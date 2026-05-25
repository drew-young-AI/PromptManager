from __future__ import annotations

import json
from copy import deepcopy
from unittest.mock import patch

from django.test import Client, SimpleTestCase, override_settings
from django.urls import reverse

from prompts.services import PromptRepository


class FakeCollection:
	def __init__(self):
		self.documents: dict[str, dict] = {}

	def create_index(self, *args, **kwargs):
		return None

	def find(self, query=None, projection=None):
		documents = [deepcopy(document) for document in self.documents.values()]
		if projection and projection.get('_id') is False:
			for document in documents:
				document.pop('_id', None)
		return documents

	def find_one(self, query, projection=None):
		document = self.documents.get(query.get('type'))
		if document is None:
			return None
		result = deepcopy(document)
		if projection and projection.get('_id') is False:
			result.pop('_id', None)
		return result

	def replace_one(self, query, document, upsert=False):
		self.documents[query['type']] = deepcopy(document)
		return None

	def delete_one(self, query):
		self.documents.pop(query['type'], None)
		return None


class FakeProviderResponse:
	def __init__(self, payload: dict):
		self.payload = payload

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc, traceback):
		return False

	def read(self):
		return json.dumps(self.payload).encode('utf-8')


class PromptRepositoryTests(SimpleTestCase):
	def setUp(self):
		self.repository = PromptRepository(FakeCollection())

	def test_save_prompt_version_builds_four_layer_tree(self):
		first = self.repository.save_prompt_version(
			type_name='clinical',
			category_name='triage',
			prompt_name='adult-intake',
			role_character='You are a calm intake nurse.',
			content='Assess patient {patient_name}.',
			notes='Initial release',
			metadata={'department': 'ER'},
			author='qa.user',
		)
		second = self.repository.save_prompt_version(
			type_name='clinical',
			category_name='triage',
			prompt_name='adult-intake',
			role_character='You are a calm intake nurse focused on safety.',
			content='Assess patient {patient_name} and capture allergy risk.',
			notes='Expanded safety language',
			metadata={'department': 'ER', 'priority': 'high'},
			author='qa.user',
		)

		tree = self.repository.list_tree()

		self.assertEqual(first['latest_version'], 1)
		self.assertEqual(second['latest_version'], 2)
		self.assertEqual(tree['types'][0]['name'], 'clinical')
		self.assertEqual(tree['types'][0]['categories'][0]['name'], 'triage')
		self.assertEqual(tree['types'][0]['categories'][0]['prompts'][0]['name'], 'adult-intake')
		self.assertEqual(
			tree['types'][0]['categories'][0]['prompts'][0]['version_numbers'],
			[2, 1],
		)
		self.assertEqual(second['versions'][0]['role_character'], 'You are a calm intake nurse focused on safety.')
		self.assertEqual(second['versions'][1]['role_character'], 'You are a calm intake nurse.')

	def test_assign_channel_updates_prompt_mapping(self):
		self.repository.save_prompt_version(
			type_name='operations',
			category_name='handoff',
			prompt_name='nurse-shift-summary',
			content='Summarize the nurse handoff.',
			notes='',
			metadata={},
			author='ops.user',
		)

		payload = self.repository.assign_channel(
			type_name='operations',
			category_name='handoff',
			prompt_name='nurse-shift-summary',
			channel_name='production',
			version=1,
		)

		self.assertEqual(payload['channels']['production'], 1)

	def test_delete_prompt_version_removes_version_and_channel_mapping(self):
		self.repository.save_prompt_version(
			type_name='clinical',
			category_name='triage',
			prompt_name='adult-intake',
			content='v1',
			notes='',
			metadata={},
			author='qa.user',
		)
		self.repository.save_prompt_version(
			type_name='clinical',
			category_name='triage',
			prompt_name='adult-intake',
			content='v2',
			notes='',
			metadata={},
			author='qa.user',
		)
		self.repository.assign_channel(
			type_name='clinical',
			category_name='triage',
			prompt_name='adult-intake',
			channel_name='production',
			version=2,
		)

		payload = self.repository.delete_prompt_version(
			type_name='clinical',
			category_name='triage',
			prompt_name='adult-intake',
			version=2,
		)

		self.assertEqual(payload['latest_version'], 1)
		self.assertEqual(payload['versions'][0]['version'], 1)
		self.assertEqual(payload['channels'], {})

	def test_delete_channel_mapping_removes_existing_channel(self):
		self.repository.save_prompt_version(
			type_name='clinical',
			category_name='triage',
			prompt_name='adult-intake',
			content='v1',
			notes='',
			metadata={},
			author='qa.user',
		)
		self.repository.assign_channel(
			type_name='clinical',
			category_name='triage',
			prompt_name='adult-intake',
			channel_name='production',
			version=1,
		)

		payload = self.repository.delete_channel_mapping(
			type_name='clinical',
			category_name='triage',
			prompt_name='adult-intake',
			channel_name='production',
		)

		self.assertEqual(payload['channels'], {})

	def test_delete_prompt_removes_prompt_from_tree(self):
		self.repository.save_prompt_version(
			type_name='clinical',
			category_name='triage',
			prompt_name='adult-intake',
			content='v1',
			notes='',
			metadata={},
			author='qa.user',
		)

		payload = self.repository.delete_prompt(
			type_name='clinical',
			category_name='triage',
			prompt_name='adult-intake',
		)
		tree = self.repository.list_tree()

		self.assertTrue(payload['deleted'])
		self.assertEqual(tree['types'], [])

	@override_settings(
		PROMPT_MANAGER_AZURE_OPENAI_ENDPOINT='',
		PROMPT_MANAGER_AZURE_OPENAI_API_KEY='',
		PROMPT_MANAGER_AZURE_OPENAI_DEPLOYMENT='',
	)
	def test_test_prompt_returns_preview_when_live_provider_not_configured(self):
		self.repository.save_prompt_version(
			type_name='clinical',
			category_name='discharge',
			prompt_name='care-plan',
			role_character='You are coordinating discharge for {patient_name}.',
			content='Prepare discharge plan for {patient_name}.',
			notes='',
			metadata={},
			author='clinician',
		)

		payload = self.repository.test_prompt(
			type_name='clinical',
			category_name='discharge',
			prompt_name='care-plan',
			version=1,
			channel_name='',
			user_input='Patient needs home care follow-up.',
			variables={'patient_name': 'Taylor'},
		)

		self.assertEqual(payload['mode'], 'preview')
		self.assertEqual(
			payload['rendered_prompt'],
			'You are coordinating discharge for Taylor.\n\nPrepare discharge plan for Taylor.',
		)
		self.assertEqual(payload['request_preview'][1]['content'], 'Patient needs home care follow-up.')

	@override_settings(
		PROMPT_MANAGER_AZURE_OPENAI_ENDPOINT='https://example.openai.azure.com',
		PROMPT_MANAGER_AZURE_OPENAI_API_KEY='azure-test-key',
		PROMPT_MANAGER_AZURE_OPENAI_DEPLOYMENT='gpt-4.1',
		PROMPT_MANAGER_AZURE_OPENAI_API_VERSION='2024-10-21',
	)
	def test_test_prompt_calls_azure_openai_when_configured(self):
		self.repository.save_prompt_version(
			type_name='clinical',
			category_name='discharge',
			prompt_name='care-plan',
			role_character='You are coordinating discharge for {patient_name}.',
			content='Prepare discharge plan for {patient_name}.',
			notes='',
			metadata={},
			author='clinician',
		)

		with patch(
			'prompts.llms.azure_openai.request.urlopen',
			return_value=FakeProviderResponse(
				{'choices': [{'message': {'content': 'Live Azure response'}}]}
			),
		) as mock_urlopen:
			payload = self.repository.test_prompt(
				type_name='clinical',
				category_name='discharge',
				prompt_name='care-plan',
				version=1,
				channel_name='',
				user_input='Patient needs home care follow-up.',
				variables={'patient_name': 'Taylor'},
			)

		provider_request = mock_urlopen.call_args.args[0]
		headers = {key.lower(): value for key, value in provider_request.header_items()}

		self.assertEqual(payload['mode'], 'live')
		self.assertEqual(payload['output'], 'Live Azure response')
		self.assertEqual(
			provider_request.full_url,
			'https://example.openai.azure.com/openai/deployments/gpt-4.1/chat/completions?api-version=2024-10-21',
		)
		self.assertEqual(headers['api-key'], 'azure-test-key')
		self.assertEqual(
			json.loads(provider_request.data.decode('utf-8')),
			{
				'messages': [
					{
						'role': 'system',
						'content': 'You are coordinating discharge for Taylor.\n\nPrepare discharge plan for Taylor.',
					},
					{'role': 'user', 'content': 'Patient needs home care follow-up.'},
				],
			},
		)


class PromptViewsTests(SimpleTestCase):
	def setUp(self):
		self.client = Client()

	def test_index_renders_single_page_ui(self):
		response = self.client.get(reverse('prompts:index'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, '醫療提示詞管理系統')

	def test_save_endpoint_returns_created_prompt(self):
		fake_prompt = {
			'type': 'clinical',
			'category': 'triage',
			'name': 'adult-intake',
			'channels': {},
			'versions': [],
			'latest_version': 1,
			'updated_at': '2026-03-10T12:00:00+00:00',
		}

		with patch('prompts.views.get_repository') as mock_get_repository:
			mock_get_repository.return_value.save_prompt_version.return_value = fake_prompt
			response = self.client.post(
				reverse('prompts:save-version'),
				data={
					'type': 'clinical',
					'category': 'triage',
					'name': 'adult-intake',
					'role_character': 'You are a calm intake nurse.',
					'content': 'Assess the patient.',
					'notes': '',
					'metadata': {},
					'author': 'qa.user',
				},
				content_type='application/json',
			)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(response.json()['prompt']['latest_version'], 1)
		mock_get_repository.return_value.save_prompt_version.assert_called_once_with(
			type_name='clinical',
			category_name='triage',
			prompt_name='adult-intake',
			role_character='You are a calm intake nurse.',
			content='Assess the patient.',
			notes='',
			metadata={},
			author='qa.user',
		)

	def test_prompt_tree_endpoint_returns_repository_payload(self):
		tree = {'types': [{'name': 'clinical', 'categories': []}]}

		with patch('prompts.views.get_repository') as mock_get_repository:
			mock_get_repository.return_value.list_tree.return_value = tree
			response = self.client.get(reverse('prompts:tree'))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), tree)

	def test_delete_prompt_endpoint_returns_deleted_payload(self):
		deleted_payload = {
			'type': 'clinical',
			'category': 'triage',
			'name': 'adult-intake',
			'deleted': True,
		}

		with patch('prompts.views.get_repository') as mock_get_repository:
			mock_get_repository.return_value.delete_prompt.return_value = deleted_payload
			response = self.client.post(
				reverse('prompts:delete-prompt'),
				data={
					'type': 'clinical',
					'category': 'triage',
					'name': 'adult-intake',
				},
				content_type='application/json',
			)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.json()['prompt']['deleted'])

	def test_delete_channel_endpoint_returns_prompt_payload(self):
		prompt_payload = {
			'type': 'clinical',
			'category': 'triage',
			'name': 'adult-intake',
			'channels': {},
			'versions': [],
			'latest_version': 1,
		}

		with patch('prompts.views.get_repository') as mock_get_repository:
			mock_get_repository.return_value.delete_channel_mapping.return_value = prompt_payload
			response = self.client.post(
				reverse('prompts:delete-channel'),
				data={
					'type': 'clinical',
					'category': 'triage',
					'name': 'adult-intake',
					'channel': 'production',
				},
				content_type='application/json',
			)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['prompt']['channels'], {})
