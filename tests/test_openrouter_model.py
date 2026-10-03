"""Offline transport contract tests; optional SDKs are needed only in the WSL harness."""

import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


AVAILABLE = all(importlib.util.find_spec(name) is not None for name in ('google', 'openai', 'pydantic'))
adapter = None
if AVAILABLE:
    try:
        from google.adk.models.llm_request import LlmRequest
        from google.genai import types
        SPEC = importlib.util.spec_from_file_location(
            'openrouter_model', Path(__file__).resolve().parents[1] / 'tools/openrouter_model.py')
        adapter = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(adapter)
    except ModuleNotFoundError:
        AVAILABLE = False


def provider_response(*, tool=True, reasoning=True, cost=0.002):
    message = {'role': 'assistant', 'content': None if tool else 'Done.'}
    if reasoning:
        message['reasoning'] = 'Inspect the result before answering.'
        message['reasoning_details'] = [
            {'type': 'reasoning.text', 'text': 'Inspect the result before answering.',
             'id': 'reason-1', 'format': 'unknown', 'index': 0},
            {'type': 'reasoning.encrypted', 'data': 'opaque-state', 'id': 'reason-2',
             'format': 'provider-format', 'index': 1},
        ]
    if tool:
        message['tool_calls'] = [
            {'id': 'call-one', 'type': 'function', 'function': {
                'name': 'report_value', 'arguments': '{"value":"ok"}'}}
        ]
    return {'id': 'generation-123', 'model': adapter.MODEL_ID, 'provider': 'DeepInfra',
            'choices': [{'message': message, 'finish_reason': 'tool_calls' if tool else 'stop'}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 30, 'total_tokens': 130,
                      'prompt_tokens_details': {'cached_tokens': 60},
                      'completion_tokens_details': {'reasoning_tokens': 20}, 'cost': cost}}


def request(contents=None):
    declaration = types.FunctionDeclaration(name='report_value', parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={'value': types.Schema(type=types.Type.STRING)}, required=['value']))
    return LlmRequest(model=adapter.MODEL_ID, contents=contents or [
        types.Content(role='user', parts=[types.Part(text='Report ok.')])],
        config=types.GenerateContentConfig(system_instruction='Use the tool.',
            temperature=0.2, top_p=0.95, max_output_tokens=16384,
            thinking_config=types.ThinkingConfig(thinking_budget=4096, include_thoughts=True),
            tools=[types.Tool(function_declarations=[declaration])]))


class FakeClient:
    def __init__(self, responses):
        self.responses, self.calls, self.closed = list(responses), [], False
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def close(self):
        self.closed = True


@unittest.skipUnless(AVAILABLE, 'Optional ADK/OpenAI packages require the local harness runtime')
class OpenRouterTransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'usage.jsonl'

    def model(self, responses):
        client = FakeClient(responses)
        model = adapter.create_openrouter_model(api_key='fake-secret-never-send',
            base_url=adapter.BASE_URL, usage_path=self.path, client=client)
        model._task = 'synthetic'
        return model, client

    async def collect(self, model, value):
        return [item async for item in model.generate_content_async(value)]

    def test_exact_routing_sampling_tools_and_forced_choice(self):
        value = request()
        value.config.tool_config = types.ToolConfig(function_calling_config=types.FunctionCallingConfig(
            mode='ANY', allowed_function_names=['report_value']))
        payload = adapter.request_payload(value)
        self.assertEqual(payload['model'], 'google/gemma-4-31b-it')
        self.assertEqual((payload['temperature'], payload['top_p'], payload['max_tokens']), (0.2, 0.95, 16384))
        self.assertEqual(payload['extra_body']['provider'], adapter.PROVIDER_CONFIG)
        self.assertEqual(payload['extra_body']['reasoning'], {'enabled': True, 'exclude': False})
        self.assertEqual(payload['tool_choice'], 'required')
        self.assertEqual(payload['tools'][0]['function']['parameters'], {
            'type': 'object', 'properties': {'value': {'type': 'string'}}, 'required': ['value']})
        self.assertIsNone(adapter.LOCAL_CONTEXT_CAP)

    async def test_two_turn_tool_and_reasoning_roundtrip_survives_adk_history(self):
        from google.adk.events.event import Event
        from google.adk.flows.llm_flows import contents
        raw = provider_response()
        model, client = self.model([raw, provider_response(tool=False)])
        first_request = request()
        first = (await self.collect(model, first_request))[0]
        # Serialize and rebuild the event, then exercise ADK's real history path.
        event = Event(author='coder', invocation_id='turn-1', content=first.content)
        event = Event.model_validate_json(event.model_dump_json())
        reply = types.Content(role='user', parts=[types.Part(function_response=types.FunctionResponse(
            name='report_value', id='call-one', response={'value': 'ok'}))])
        history = contents._get_contents(current_branch=None, agent_name='coder', events=[
            Event(author='user', invocation_id='turn-1', content=first_request.contents[0]),
            event, Event(author='coder', invocation_id='turn-1', content=reply),
        ])
        second = (await self.collect(model, request(history)))[0]
        messages = client.calls[1]['messages']
        assistant = next(message for message in messages if message['role'] == 'assistant')
        self.assertEqual(assistant['reasoning_details'], raw['choices'][0]['message']['reasoning_details'])
        self.assertEqual(assistant['tool_calls'][0]['id'], 'call-one')
        self.assertEqual(json.loads(assistant['tool_calls'][0]['function']['arguments']), {'value': 'ok'})
        self.assertEqual(messages[-1], {'role': 'tool', 'tool_call_id': 'call-one', 'content': '{"value":"ok"}'})
        self.assertEqual(second.content.parts[-1].text, 'Done.')
        await model.aclose()
        self.assertTrue(client.closed)

    def test_parallel_tool_results_keep_each_id_and_content(self):
        history = [types.Content(role='model', parts=[
            types.Part(function_call=types.FunctionCall(id='a', name='first', args={'n': 1})),
            types.Part(function_call=types.FunctionCall(id='b', name='second', args={'n': 2})),
        ]), types.Content(role='user', parts=[
            types.Part(function_response=types.FunctionResponse(id='b', name='second', response={'n': 2})),
            types.Part(function_response=types.FunctionResponse(id='a', name='first', response={'n': 1})),
        ])]
        messages = adapter.messages_from_request(request(history))
        self.assertEqual([m['tool_call_id'] for m in messages if m['role'] == 'tool'], ['b', 'a'])

    def test_none_mode_omits_available_tools_but_preserves_tool_history(self):
        first = adapter.response_to_adk(provider_response()).content
        value = request([types.Content(role='user', parts=[types.Part(text='Report ok.')]), first,
            types.Content(role='user', parts=[types.Part(function_response=types.FunctionResponse(
                id='call-one', name='report_value', response={'confirmation': 'ok'}))])])
        value.config.tool_config = types.ToolConfig(function_calling_config=types.FunctionCallingConfig(mode='NONE'))
        payload = adapter.request_payload(value)
        self.assertNotIn('tools', payload)
        self.assertNotIn('tool_choice', payload)
        self.assertEqual(payload['messages'][-1]['role'], 'tool')
        self.assertEqual(payload['messages'][-1]['tool_call_id'], 'call-one')
        self.assertEqual(payload['messages'][-2]['reasoning_details'],
                         provider_response()['choices'][0]['message']['reasoning_details'])

    def test_unmatched_results_and_missing_results_fail_before_dispatch(self):
        for history in [[types.Content(role='user', parts=[types.Part(function_response=types.FunctionResponse(
            name='report_value', id='missing', response={'value': 'ok'}))])],
            [types.Content(role='model', parts=[types.Part(function_call=types.FunctionCall(
                name='report_value', id='unfinished', args={'value': 'ok'}))])]]:
            with self.subTest(history=history), self.assertRaises(ValueError):
                adapter.messages_from_request(request(history))

    async def test_usage_cost_routing_and_secret_safe_model_serialization(self):
        model, _ = self.model([provider_response()])
        response = (await self.collect(model, request()))[0]
        row = model._records[0]
        self.assertEqual(row['usage'], {'prompt_token_count': 100, 'candidates_token_count': 10,
            'thoughts_token_count': 20, 'cached_content_token_count': 60,
            'total_token_count': 130, 'completion_token_count': 30})
        self.assertEqual(response.usage_metadata.candidates_token_count, 10)
        self.assertEqual((row['provider'], row['generation_id'], row['cost_usd']), ('DeepInfra', 'generation-123', 0.002))
        self.assertNotIn('fake-secret', model.model_dump_json() + self.path.read_text())
        self.assertNotIn('opaque-state', self.path.read_text())

    async def test_missing_cost_and_reasoning_counts_stay_unknown(self):
        raw = provider_response(cost=None)
        raw['usage'].pop('completion_tokens_details')
        model, _ = self.model([raw])
        await self.collect(model, request())
        row = model._records[0]
        self.assertIsNone(row['cost_usd'])
        self.assertIsNone(row['usage']['thoughts_token_count'])
        self.assertIsNone(row['usage']['candidates_token_count'])
        self.assertEqual(row['usage']['completion_token_count'], 30)

    async def test_provider_failure_is_sanitized_and_not_retried(self):
        class SyntheticFailure(Exception):
            status_code = 429
            body = {'error': {'message': 'private prompt fake-secret-never-send'}}
        model, client = self.model([SyntheticFailure('fake-secret-never-send private prompt')])
        with self.assertRaises(adapter.OpenRouterAdapterError) as caught:
            await self.collect(model, request())
        serialized = self.path.read_text() + str(caught.exception)
        self.assertNotIn('fake-secret', serialized)
        self.assertNotIn('private prompt', serialized)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(json.loads(self.path.read_text())['code'], 429)
        from adk_eval_core.plugins import ModelRetryPlugin
        self.assertFalse(ModelRetryPlugin()._is_retryable_error(caught.exception))

    def test_routing_error_classification_only_returns_known_constants(self):
        class SyntheticRoutingFailure(Exception):
            status_code = 404
            body = {'error': {'message': 'No endpoints found that support tool use. private fake-secret'}}
        self.assertEqual(adapter.safe_error_classification(SyntheticRoutingFailure()), 'routing_tool_support')
        error = SyntheticRoutingFailure()
        error.body = {'message': 'No endpoints found that match your data policy. private fake-secret'}
        self.assertEqual(adapter.safe_error_classification(error), 'routing_privacy_policy')

    async def test_decode_failure_preserves_billed_usage_without_raw_arguments(self):
        raw = provider_response()
        raw['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = 'private malformed output'
        model, _ = self.model([raw])
        with self.assertRaises(adapter.OpenRouterAdapterError):
            await self.collect(model, request())
        rows = [json.loads(line) for line in self.path.read_text().splitlines()]
        self.assertEqual(rows[0]['cost_usd'], 0.002)
        self.assertEqual(rows[1]['stage'], 'response_conversion')
        self.assertNotIn('private malformed output', self.path.read_text())

    async def test_unexpected_model_is_rejected_without_network(self):
        model, client = self.model([])
        value = request()
        value.model = 'other/model'
        with self.assertRaises(adapter.OpenRouterAdapterError):
            await self.collect(model, value)
        self.assertEqual(client.calls, [])

    def test_factory_uses_explicit_credentials_endpoint_and_zero_sdk_retries(self):
        with patch.object(adapter, 'AsyncOpenAI') as factory:
            adapter.create_openrouter_model(api_key='fake-secret', base_url=adapter.BASE_URL,
                                            usage_path=self.path)
        factory.assert_called_once_with(api_key='fake-secret', base_url=adapter.BASE_URL,
                                         max_retries=0, timeout=90.0)
        with self.assertRaises(ValueError):
            adapter.create_openrouter_model(api_key='fake-secret', base_url='https://other.example/v1',
                                            usage_path=self.path)


if __name__ == '__main__':
    unittest.main()
