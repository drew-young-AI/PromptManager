from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from bson import ObjectId
from django.conf import settings
from pymongo import ASCENDING, MongoClient, ReturnDocument

from .llms import get_test_llm_provider
from .llms.base import LLMProviderError


class PromptServiceError(Exception):
    """Base class for prompt repository and test service errors."""


class PromptValidationError(PromptServiceError):
    """Raised when incoming request data is invalid."""


class PromptNotFoundError(PromptServiceError):
    """Raised when the requested prompt hierarchy does not exist."""


class SafeTemplateMap(dict):
    def __missing__(self, key: str) -> str:
        return '{' + key + '}'


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec='seconds')


def _clean_name(value: Any, field_name: str) -> str:
    cleaned = str(value or '').strip()
    if not cleaned:
        raise PromptValidationError(f'{field_name}為必填欄位。')
    return cleaned


def _clean_channel(value: Any) -> str:
    return _clean_name(value, '發布環境').lower().replace(' ', '-')


def _clean_metadata(value: Any) -> dict[str, Any]:
    if value in (None, ''):
        return {}
    if not isinstance(value, dict):
        raise PromptValidationError('中繼資料必須是 JSON 物件。')
    return value


def _clean_version(value: Any) -> int:
    try:
        version = int(value)
    except (TypeError, ValueError) as exc:
        raise PromptValidationError('版本號必須是大於 0 的整數。') from exc
    if version < 1:
        raise PromptValidationError('版本號必須是大於 0 的整數。')
    return version


class DepartmentRepository:
    """Manages the departments collection: {_id, department, sub_department}."""

    def __init__(self, collection):
        self.collection = collection


    def list_sub_departments(self, department_name: str) -> list[dict[str, str]]:
        docs = list(
            self.collection.find(
                {'department': department_name},
                {'_id': True, 'sub_department': True},
            ).sort('sub_department', ASCENDING)
        )
        return [{'id': str(d['_id']), 'name': d['sub_department']} for d in docs]

    def get_or_create(self, department_name: str, sub_department_name: str) -> ObjectId:
        doc = self.collection.find_one_and_update(
            {'department': department_name, 'sub_department': sub_department_name},
            {'$setOnInsert': {'department': department_name, 'sub_department': sub_department_name}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return doc['_id']

    def find_id(self, department_name: str, sub_department_name: str) -> ObjectId | None:
        doc = self.collection.find_one(
            {'department': department_name, 'sub_department': sub_department_name},
            {'_id': True},
        )
        return doc['_id'] if doc else None

    def get_by_ids(self, ids: list) -> dict[str, Any]:
        """Returns {str(id): doc} for the given ObjectId list."""
        if not ids:
            return {}
        docs = list(self.collection.find({'_id': {'$in': ids}}))
        return {str(d['_id']): d for d in docs}


class PromptRepository:
    """
    Manages the prompts collection.

    Each document represents one named prompt:

        {
            _id: ObjectId,
            promptname: str,
            subdepartment: ObjectId,   # ref -> departments._id
            prompts: [
                {
                    _id: str,          # hex ObjectId string
                    data: {role_character, content, note},
                    version: int,
                    create_at: str,
                    create_by: str,
                },
                ...
            ],
            channels: {channel_name: version_id_str, ...},
            create_at: str,
            update_at: str,
        }
    """

    def __init__(self, collection, dept_repo: DepartmentRepository):
        self.collection = collection
        self.dept_repo = dept_repo

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def list_tree(self) -> dict[str, list[dict[str, Any]]]:
        prompt_docs = list(
            self.collection.find(
                {},
                {
                    'promptname': True,
                    'subdepartment': True,
                    'prompts': True,
                    'channels': True,
                    'update_at': True,
                },
            )
        )

        subdept_ids = list({doc['subdepartment'] for doc in prompt_docs if 'subdepartment' in doc})
        dept_map = self.dept_repo.get_by_ids(subdept_ids)

        tree: dict[str, dict[str, list]] = {}
        for doc in prompt_docs:
            dept_info = dept_map.get(str(doc.get('subdepartment', '')))
            if dept_info is None:
                continue
            dept_name = dept_info['department']
            subdept_name = dept_info['sub_department']

            version_numbers = sorted(
                [v.get('version', 0) for v in doc.get('prompts', [])],
                reverse=True,
            )
            prompt_summary = {
                'name': doc['promptname'],
                'description': doc.get('description', ''),
                'version_numbers': version_numbers,
                'latest_version': version_numbers[0] if version_numbers else None,
                'channels': dict(sorted(doc.get('channels', {}).items())),
                'updated_at': doc.get('update_at', ''),
            }
            tree.setdefault(dept_name, {}).setdefault(subdept_name, []).append(prompt_summary)

        types = []
        for dept_name in sorted(tree.keys()):
            categories = []
            dept_count = 0
            for subdept_name in sorted(tree[dept_name].keys()):
                prompts = sorted(tree[dept_name][subdept_name], key=lambda p: p['name'].lower())
                dept_count += len(prompts)
                categories.append(
                    {'name': subdept_name, 'prompt_count': len(prompts), 'prompts': prompts}
                )
            types.append({'name': dept_name, 'prompt_count': dept_count, 'categories': categories})

        return {'types': types}

    def get_prompt(self, type_name: Any, category_name: Any, prompt_name: Any) -> dict[str, Any]:
        dept_name = _clean_name(type_name, '部門')
        subdept_name = _clean_name(category_name, '科室')
        prompt_key = _clean_name(prompt_name, '提示詞名稱')

        subdept_id = self.dept_repo.find_id(dept_name, subdept_name)
        if subdept_id is None:
            raise PromptNotFoundError(f'找不到科室「{subdept_name}」。')

        doc = self.collection.find_one({'subdepartment': subdept_id, 'promptname': prompt_key})
        if doc is None:
            raise PromptNotFoundError(f'找不到提示詞「{prompt_key}」。')

        return self._serialize_prompt(dept_name, subdept_name, doc)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def save_prompt_version(
        self,
        *,
        type_name: Any,
        category_name: Any,
        prompt_name: Any,
        description: Any = '',
        role_character: Any = '',
        content: Any,
        notes: Any,
        author: Any,
    ) -> dict[str, Any]:
        dept_name = _clean_name(type_name, '部門')
        subdept_name = _clean_name(category_name, '科室')
        prompt_key = _clean_name(prompt_name, '提示詞名稱')
        prompt_content = str(content or '').strip()
        if not prompt_content:
            raise PromptValidationError('系統提示詞內容不可空白。')

        description_text = str(description or '').strip()
        note_text = str(notes or '').strip()
        author_name = str(author or '').strip()
        role_character_text = str(role_character or '').strip()
        timestamp = _utc_now()

        subdept_id = self.dept_repo.get_or_create(dept_name, subdept_name)

        existing = self.collection.find_one(
            {'subdepartment': subdept_id, 'promptname': prompt_key},
            {'prompts': True},
        )

        if existing is None:
            version_number = 1
            self.collection.insert_one(
                {
                    'promptname': prompt_key,
                    'description': description_text,
                    'subdepartment': subdept_id,
                    'prompts': [],
                    'channels': {},
                    'create_at': timestamp,
                    'update_at': timestamp,
                }
            )
        else:
            version_number = (
                max((v.get('version', 0) for v in existing.get('prompts', [])), default=0) + 1
            )
            # Update description if provided
            if description_text:
                self.collection.update_one(
                    {'subdepartment': subdept_id, 'promptname': prompt_key},
                    {'$set': {'description': description_text}},
                )

        new_version = {
            '_id': str(ObjectId()),
            'data': {
                'role_character': role_character_text,
                'content': prompt_content,
                'note': note_text,
            },
            'version': version_number,
            'create_at': timestamp,
            'create_by': author_name,
        }

        self.collection.update_one(
            {'subdepartment': subdept_id, 'promptname': prompt_key},
            {'$push': {'prompts': new_version}, '$set': {'update_at': timestamp}},
        )

        return self.get_prompt(dept_name, subdept_name, prompt_key)

    def assign_channel(
        self,
        *,
        type_name: Any,
        category_name: Any,
        prompt_name: Any,
        channel_name: Any,
        version: Any,
    ) -> dict[str, Any]:
        dept_name = _clean_name(type_name, '部門')
        subdept_name = _clean_name(category_name, '科室')
        prompt_key = _clean_name(prompt_name, '提示詞名稱')
        release_channel = _clean_channel(channel_name)
        version_number = _clean_version(version)
        timestamp = _utc_now()

        subdept_id = self.dept_repo.find_id(dept_name, subdept_name)
        if subdept_id is None:
            raise PromptNotFoundError(f'找不到科室「{subdept_name}」。')

        doc = self.collection.find_one(
            {'subdepartment': subdept_id, 'promptname': prompt_key},
            {'prompts': True},
        )
        if doc is None:
            raise PromptNotFoundError(f'找不到提示詞「{prompt_key}」。')

        selected_version = self._find_raw_version(doc.get('prompts', []), version_number)
        version_id = str(selected_version.get('_id', '')).strip()
        if not version_id:
            raise PromptValidationError('版本資料缺少 _id，無法設定發布環境。')

        self.collection.update_one(
            {'subdepartment': subdept_id, 'promptname': prompt_key},
            {'$set': {f'channels.{release_channel}': version_id, 'update_at': timestamp}},
        )

        return self.get_prompt(dept_name, subdept_name, prompt_key)

    def delete_channel_mapping(
        self,
        *,
        type_name: Any,
        category_name: Any,
        prompt_name: Any,
        channel_name: Any,
    ) -> dict[str, Any]:
        dept_name = _clean_name(type_name, '部門')
        subdept_name = _clean_name(category_name, '科室')
        prompt_key = _clean_name(prompt_name, '提示詞名稱')
        release_channel = _clean_channel(channel_name)
        timestamp = _utc_now()

        subdept_id = self.dept_repo.find_id(dept_name, subdept_name)
        if subdept_id is None:
            raise PromptNotFoundError(f'找不到科室「{subdept_name}」。')

        doc = self.collection.find_one(
            {'subdepartment': subdept_id, 'promptname': prompt_key},
            {'channels': True},
        )
        if doc is None:
            raise PromptNotFoundError(f'找不到提示詞「{prompt_key}」。')

        if release_channel not in doc.get('channels', {}):
            raise PromptNotFoundError(f'找不到發布環境「{release_channel}」的版本映射。')

        self.collection.update_one(
            {'subdepartment': subdept_id, 'promptname': prompt_key},
            {'$unset': {f'channels.{release_channel}': ''}, '$set': {'update_at': timestamp}},
        )

        return self.get_prompt(dept_name, subdept_name, prompt_key)

    def delete_prompt_version(
        self,
        *,
        type_name: Any,
        category_name: Any,
        prompt_name: Any,
        version: Any,
    ) -> dict[str, Any]:
        dept_name = _clean_name(type_name, '部門')
        subdept_name = _clean_name(category_name, '科室')
        prompt_key = _clean_name(prompt_name, '提示詞名稱')
        version_number = _clean_version(version)
        timestamp = _utc_now()

        subdept_id = self.dept_repo.find_id(dept_name, subdept_name)
        if subdept_id is None:
            raise PromptNotFoundError(f'找不到科室「{subdept_name}」。')

        doc = self.collection.find_one(
            {'subdepartment': subdept_id, 'promptname': prompt_key},
            {'prompts': True, 'channels': True},
        )
        if doc is None:
            raise PromptNotFoundError(f'找不到提示詞「{prompt_key}」。')

        prompts = doc.get('prompts', [])
        self._find_raw_version(prompts, version_number)

        remaining = [v for v in prompts if v.get('version') != version_number]
        if not remaining:
            raise PromptValidationError('不能刪除最後一個版本；若要移除請直接刪除整筆提示詞。')

        deleted_version = self._find_raw_version(prompts, version_number)
        deleted_version_id = str(deleted_version.get('_id', '')).strip()
        channels_pruned = {
            ch: ver
            for ch, ver in doc.get('channels', {}).items()
            if str(ver) != deleted_version_id and ver != version_number
        }

        self.collection.update_one(
            {'subdepartment': subdept_id, 'promptname': prompt_key},
            {
                '$pull': {'prompts': {'version': version_number}},
                '$set': {'channels': channels_pruned, 'update_at': timestamp},
            },
        )

        return self.get_prompt(dept_name, subdept_name, prompt_key)

    def delete_prompt(
        self,
        *,
        type_name: Any,
        category_name: Any,
        prompt_name: Any,
    ) -> dict[str, Any]:
        dept_name = _clean_name(type_name, '部門')
        subdept_name = _clean_name(category_name, '科室')
        prompt_key = _clean_name(prompt_name, '提示詞名稱')

        subdept_id = self.dept_repo.find_id(dept_name, subdept_name)
        if subdept_id is None:
            raise PromptNotFoundError(f'找不到科室「{subdept_name}」。')

        result = self.collection.delete_one(
            {'subdepartment': subdept_id, 'promptname': prompt_key}
        )
        if result.deleted_count == 0:
            raise PromptNotFoundError(f'找不到提示詞「{prompt_key}」。')

        return {
            'type': dept_name,
            'category': subdept_name,
            'name': prompt_key,
            'deleted': True,
        }

    def test_prompt(
        self,
        *,
        type_name: Any,
        category_name: Any,
        prompt_name: Any,
        version: Any,
        channel_name: Any,
        user_input: Any,
        variables: Any,
    ) -> dict[str, Any]:
        prompt = self.get_prompt(type_name, category_name, prompt_name)
        test_variables = _clean_metadata(variables)
        selected_channel = str(channel_name or '').strip().lower()

        if version not in (None, ''):
            version_number = _clean_version(version)
        elif selected_channel:
            assigned_version = prompt['channels'].get(selected_channel)
            if assigned_version is None:
                raise PromptValidationError(
                    f'發布環境「{selected_channel}」尚未指派到這筆提示詞。'
                )
            version_payload = next(
                (v for v in prompt['versions'] if str(v.get('id', '')) == str(assigned_version)),
                None,
            )
            if version_payload is not None:
                version_number = version_payload['version']
            else:
                # Legacy compatibility: older mappings may still store version numbers.
                version_number = _clean_version(assigned_version)
        else:
            version_number = prompt['latest_version']

        version_payload = next(
            (v for v in prompt['versions'] if v.get('version') == version_number), None
        )
        if version_payload is None:
            raise PromptNotFoundError(f'找不到版本 {version_number}。')

        rendered_role_character = version_payload['role_character'].format_map(
            SafeTemplateMap(test_variables)
        )
        rendered_content = version_payload['content'].format_map(SafeTemplateMap(test_variables))
        user_message = str(user_input or '').strip()
        rendered_prompt = '\n\n'.join(
            item for item in [rendered_role_character, rendered_content] if item
        )
        request_preview = [
            {'role': 'system', 'content': rendered_prompt},
            {'role': 'user', 'content': user_message},
        ]

        provider_result = self._invoke_test_provider(request_preview)

        return {
            'mode': provider_result['mode'],
            'selected_version': version_number,
            'selected_channel': selected_channel or None,
            'rendered_prompt': rendered_prompt,
            'request_preview': request_preview,
            'output': provider_result['output'],
            'provider_response': provider_result.get('provider_response'),
        }

    def test_prompt_inline(
        self,
        *,
        role_character: Any,
        content: Any,
        user_input: Any,
        variables: Any,
    ) -> dict[str, Any]:
        role_character_text = str(role_character or '').strip()
        content_text = str(content or '').strip()
        if not content_text:
            raise PromptValidationError('系統提示詞內容不可空白。')
        test_variables = _clean_metadata(variables)
        rendered_role = role_character_text.format_map(SafeTemplateMap(test_variables))
        rendered_content = content_text.format_map(SafeTemplateMap(test_variables))
        user_message = str(user_input or '').strip()
        rendered_prompt = '\n\n'.join(item for item in [rendered_role, rendered_content] if item)
        request_preview = [
            {'role': 'system', 'content': rendered_prompt},
            {'role': 'user', 'content': user_message},
        ]
        provider_result = self._invoke_test_provider(request_preview)
        return {
            'mode': provider_result['mode'],
            'selected_version': None,
            'selected_channel': None,
            'rendered_prompt': rendered_prompt,
            'request_preview': request_preview,
            'output': provider_result['output'],
            'provider_response': provider_result.get('provider_response'),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_raw_version(
        self, prompts: list[dict[str, Any]], version_number: int
    ) -> dict[str, Any]:
        """Find a raw (DB-format) version entry; raises PromptNotFoundError if missing."""
        for v in prompts:
            if v.get('version') == version_number:
                return v
        raise PromptNotFoundError(f'找不到版本 {version_number}。')

    def _serialize_version(self, v: dict[str, Any]) -> dict[str, Any]:
        data = v.get('data', {})
        return {
            'id': v.get('_id', ''),
            'version': v.get('version'),
            'role_character': data.get('role_character', ''),
            'content': data.get('content', ''),
            'notes': data.get('note', ''),       # DB stores 'note'; API exposes 'notes'
            'created_at': v.get('create_at', ''),  # DB stores 'create_at'; API exposes 'created_at'
            'created_by': v.get('create_by', ''),  # DB stores 'create_by'; API exposes 'created_by'
        }

    def _serialize_prompt(
        self, dept_name: str, subdept_name: str, doc: dict[str, Any]
    ) -> dict[str, Any]:
        versions = sorted(
            [self._serialize_version(v) for v in doc.get('prompts', [])],
            key=lambda v: v['version'],
            reverse=True,
        )
        latest_version = versions[0]['version'] if versions else None
        latest_version_id = versions[0]['id'] if versions else None
        return {
            'type': dept_name,
            'category': subdept_name,
            'name': doc.get('promptname', ''),
            'description': doc.get('description', ''),
            'channels': dict(sorted(doc.get('channels', {}).items())),
            'versions': versions,
            'latest_version': latest_version,
            'latest_version_id': latest_version_id,
            'updated_at': doc.get('update_at', ''),
        }

    def _invoke_test_provider(
        self, request_preview: list[dict[str, str]]
    ) -> dict[str, Any]:
        try:
            return get_test_llm_provider().invoke(request_preview)
        except LLMProviderError as exc:
            raise PromptServiceError(str(exc)) from exc


# ------------------------------------------------------------------
# Singleton factories (cached per process)
# ------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_database():
    client = MongoClient(settings.MONGODB_URI, tz_aware=True)
    return client[settings.MONGODB_DB_NAME]


@lru_cache(maxsize=1)
def get_department_repository() -> DepartmentRepository:
    database = _get_database()
    collection = database[settings.MONGODB_DEPARTMENTS_COLLECTION]
    return DepartmentRepository(collection)


@lru_cache(maxsize=1)
def get_repository() -> PromptRepository:
    database = _get_database()
    collection = database[settings.MONGODB_PROMPTS_COLLECTION]
    return PromptRepository(collection, get_department_repository())
