from __future__ import annotations

import json

from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .llms import is_test_llm_configured
from .services import (
	PromptNotFoundError,
	PromptServiceError,
	PromptValidationError,
	get_department_repository,
	get_repository,
)


def _ui_config() -> dict[str, str]:
	return {
		'treeUrl': reverse('prompts:tree'),
		'detailUrl': reverse('prompts:prompt-detail'),
		'saveUrl': reverse('prompts:save-version'),
		'assignChannelUrl': reverse('prompts:assign-channel'),
		'deleteChannelUrl': reverse('prompts:delete-channel'),
		'deleteVersionUrl': reverse('prompts:delete-version'),
		'deletePromptUrl': reverse('prompts:delete-prompt'),
		'testUrl': reverse('prompts:test-prompt'),
		'testInlineUrl': reverse('prompts:test-prompt-inline'),
		'subDepartmentsUrl': reverse('prompts:sub-departments'),
	}


def _json_error(message: str, status: int) -> JsonResponse:
	return JsonResponse({'error': message}, status=status)


def _read_json_body(request: HttpRequest) -> dict:
	try:
		return json.loads(request.body.decode('utf-8') or '{}')
	except json.JSONDecodeError as exc:
		raise PromptValidationError('請求內容必須是有效的 JSON。') from exc


def index(request: HttpRequest):
	context = {
		'ui_config': _ui_config(),
		'channel_suggestions': ['production', 'alpha', 'beta'],
		'live_testing_enabled': is_test_llm_configured(),
	}
	return render(request, 'prompts/index.html', context)


@require_GET
def prompt_tree(request: HttpRequest) -> JsonResponse:
	repository = get_repository()
	return JsonResponse(repository.list_tree())


@require_GET
def prompt_detail(request: HttpRequest) -> JsonResponse:
	repository = get_repository()
	try:
		payload = repository.get_prompt(
			request.GET.get('type', ''),
			request.GET.get('category', ''),
			request.GET.get('name', ''),
		)
	except PromptValidationError as exc:
		return _json_error(str(exc), 400)
	except PromptNotFoundError as exc:
		return _json_error(str(exc), 404)
	return JsonResponse(payload)


@require_POST
def save_prompt_version(request: HttpRequest) -> JsonResponse:
	repository = get_repository()
	try:
		body = _read_json_body(request)
		payload = repository.save_prompt_version(
			type_name=body.get('type', ''),
			category_name=body.get('category', ''),
			prompt_name=body.get('name', ''),
			description=body.get('description', ''),
			role_character=body.get('role_character', ''),
			content=body.get('content', ''),
			notes=body.get('notes', ''),
			author=body.get('author', ''),
		)
	except PromptValidationError as exc:
		return _json_error(str(exc), 400)
	except PromptServiceError as exc:
		return _json_error(str(exc), 500)
	return JsonResponse({'message': '提示詞版本已儲存。', 'prompt': payload}, status=201)


@require_POST
def assign_prompt_channel(request: HttpRequest) -> JsonResponse:
	repository = get_repository()
	try:
		body = _read_json_body(request)
		payload = repository.assign_channel(
			type_name=body.get('type', ''),
			category_name=body.get('category', ''),
			prompt_name=body.get('name', ''),
			channel_name=body.get('channel', ''),
			version=body.get('version'),
		)
	except PromptValidationError as exc:
		return _json_error(str(exc), 400)
	except PromptNotFoundError as exc:
		return _json_error(str(exc), 404)
	except PromptServiceError as exc:
		return _json_error(str(exc), 500)
	return JsonResponse({'message': '發布環境已更新。', 'prompt': payload})


@require_POST
def delete_prompt_channel(request: HttpRequest) -> JsonResponse:
	repository = get_repository()
	try:
		body = _read_json_body(request)
		payload = repository.delete_channel_mapping(
			type_name=body.get('type', ''),
			category_name=body.get('category', ''),
			prompt_name=body.get('name', ''),
			channel_name=body.get('channel', ''),
		)
	except PromptValidationError as exc:
		return _json_error(str(exc), 400)
	except PromptNotFoundError as exc:
		return _json_error(str(exc), 404)
	except PromptServiceError as exc:
		return _json_error(str(exc), 500)
	return JsonResponse({'message': '發布環境映射已移除。', 'prompt': payload})


@require_POST
def delete_prompt_version(request: HttpRequest) -> JsonResponse:
	repository = get_repository()
	try:
		body = _read_json_body(request)
		payload = repository.delete_prompt_version(
			type_name=body.get('type', ''),
			category_name=body.get('category', ''),
			prompt_name=body.get('name', ''),
			version=body.get('version'),
		)
	except PromptValidationError as exc:
		return _json_error(str(exc), 400)
	except PromptNotFoundError as exc:
		return _json_error(str(exc), 404)
	except PromptServiceError as exc:
		return _json_error(str(exc), 500)
	return JsonResponse({'message': '提示詞版本已刪除。', 'prompt': payload})


@require_POST
def delete_prompt(request: HttpRequest) -> JsonResponse:
	repository = get_repository()
	try:
		body = _read_json_body(request)
		payload = repository.delete_prompt(
			type_name=body.get('type', ''),
			category_name=body.get('category', ''),
			prompt_name=body.get('name', ''),
		)
	except PromptValidationError as exc:
		return _json_error(str(exc), 400)
	except PromptNotFoundError as exc:
		return _json_error(str(exc), 404)
	except PromptServiceError as exc:
		return _json_error(str(exc), 500)
	return JsonResponse({'message': '提示詞已刪除。', 'prompt': payload})


@require_POST
def test_prompt_inline(request: HttpRequest) -> JsonResponse:
	repository = get_repository()
	try:
		body = _read_json_body(request)
		payload = repository.test_prompt_inline(
			role_character=body.get('role_character', ''),
			content=body.get('content', ''),
			user_input=body.get('user_input', ''),
			variables=body.get('variables', {}),
		)
	except PromptValidationError as exc:
		return _json_error(str(exc), 400)
	except PromptServiceError as exc:
		return _json_error(str(exc), 502)
	return JsonResponse(payload)


@require_GET
def sub_department_list(request: HttpRequest) -> JsonResponse:
	dept_repo = get_department_repository()
	department = request.GET.get('department', '').strip()
	if not department:
		return _json_error('部門為必填欄位。', 400)
	sub_departments = dept_repo.list_sub_departments(department)
	return JsonResponse({'sub_departments': sub_departments})


@require_POST
def test_prompt(request: HttpRequest) -> JsonResponse:
	repository = get_repository()
	try:
		body = _read_json_body(request)
		payload = repository.test_prompt(
			type_name=body.get('type', ''),
			category_name=body.get('category', ''),
			prompt_name=body.get('name', ''),
			version=body.get('version'),
			channel_name=body.get('channel', ''),
			user_input=body.get('user_input', ''),
			variables=body.get('variables', {}),
		)
	except PromptValidationError as exc:
		return _json_error(str(exc), 400)
	except PromptNotFoundError as exc:
		return _json_error(str(exc), 404)
	except PromptServiceError as exc:
		return _json_error(str(exc), 502)
	return JsonResponse(payload)
