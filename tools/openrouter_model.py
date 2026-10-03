"""Explicit, metered OpenRouter transport for the local Gemma API prototype.

This text/tool adapter uses no environment credentials, model fallbacks or local
token estimates. OpenRouter's route context differs from the official scorer.
Opaque reasoning details travel on a tagged ADK part signature, so ADK removing
display-only thought parts cannot discard the provider's tool-turn state.
"""

from copy import deepcopy
import json
import math
from pathlib import Path
import time

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from openai import AsyncOpenAI
from pydantic import PrivateAttr


MODEL_ID = 'google/gemma-4-31b-it'
BASE_URL = 'https://openrouter.ai/api/v1'
PROVIDER_CONFIG = {
    'only': ['deepinfra/fp8'], 'allow_fallbacks': False, 'require_parameters': True,
}
REASONING_CONFIG = {'enabled': True, 'exclude': False}
LOCAL_CONTEXT_CAP = None
_SIGNATURE_PREFIX = b'openrouter-reasoning-v1:'


class OpenRouterAdapterError(RuntimeError):
    """Sanitized, terminal error; intentionally not a retryable provider error."""


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def _schema(value):
    """Convert the Gemini declaration schema to ordinary JSON Schema."""
    if hasattr(value, 'model_dump'):
        value = value.model_dump(mode='json', by_alias=True, exclude_none=True)
    if isinstance(value, list):
        return [_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: _schema(item) for key, item in value.items()
              if key not in {'propertyOrdering', 'nullable'}}
    if isinstance(result.get('type'), str):
        result['type'] = result['type'].lower()
    if value.get('nullable'):
        return {'anyOf': [result, {'type': 'null'}]}
    return result


def _reasoning_from_parts(parts):
    payloads = []
    for part in parts:
        signature = part.thought_signature
        if signature and signature.startswith(_SIGNATURE_PREFIX):
            payloads.append(json.loads(signature[len(_SIGNATURE_PREFIX):]))
    if not payloads:
        return {}
    if any(item != payloads[0] for item in payloads[1:]):
        raise ValueError('Conflicting reasoning state in one assistant message')
    return payloads[0]


def messages_from_request(request):
    """Preserve tool-call IDs and reject unsupported modality/history silently lost elsewhere."""
    messages = []
    instruction = request.config.system_instruction
    if instruction:
        if not isinstance(instruction, str):
            if not isinstance(instruction, types.Content) or any(
                    part.text is None for part in instruction.parts or []):
                raise ValueError('Only text system instructions are supported')
            instruction = '\n'.join(part.text for part in instruction.parts or [])
        messages.append({'role': 'system', 'content': instruction})
    pending = {}
    seen_ids = set()
    for content in request.contents:
        parts = content.parts or []
        replies = [part.function_response for part in parts if part.function_response]
        for reply in replies:
            if not reply.id or reply.id not in pending:
                raise ValueError('Tool response has no matching call ID')
            if reply.name and pending[reply.id] != reply.name:
                raise ValueError('Tool response name does not match its call')
            messages.append({'role': 'tool', 'tool_call_id': reply.id,
                             'content': _json(reply.response)})
            del pending[reply.id]
        visible = [part for part in parts if not part.function_response and not part.thought]
        if not visible:
            continue
        if pending:
            raise ValueError('Missing tool result before the next conversation message')
        role = 'assistant' if content.role == 'model' else content.role
        if role not in {'user', 'assistant'}:
            raise ValueError('Unsupported content role')
        text, calls = [], []
        for part in visible:
            if part.function_call:
                call = part.function_call
                if role != 'assistant' or not call.id or not call.name or call.id in seen_ids:
                    raise ValueError('Tool call needs a distinct assistant call ID and name')
                seen_ids.add(call.id)
                pending[call.id] = call.name
                calls.append({'id': call.id, 'type': 'function', 'function': {
                    'name': call.name, 'arguments': _json(call.args or {}),
                }})
            elif part.text is not None:
                text.append(part.text)
            else:
                raise ValueError('Only text and function-call content is supported')
        message = {'role': role, 'content': ''.join(text) or None}
        if calls:
            message['tool_calls'] = calls
        if role == 'assistant':
            message.update(_reasoning_from_parts(parts))
        messages.append(message)
    if pending:
        raise ValueError('Incomplete tool results at the end of the request')
    if not any(message['role'] != 'system' for message in messages):
        raise ValueError('A user or tool conversation is required')
    return messages


def request_payload(request):
    """Build the exact routed request; never silently substitute sampling settings."""
    config = request.config
    payload = {
        'model': MODEL_ID, 'messages': messages_from_request(request), 'stream': False,
        'temperature': config.temperature if config.temperature is not None else 0.2,
        'top_p': config.top_p if config.top_p is not None else 0.95,
        'max_tokens': config.max_output_tokens if config.max_output_tokens is not None else 16384,
        'extra_body': {'provider': deepcopy(PROVIDER_CONFIG),
                       'reasoning': deepcopy(REASONING_CONFIG)},
    }
    if not 1 <= payload['max_tokens'] <= 16384:
        raise ValueError('The pinned OpenRouter route allows at most 16384 output tokens')
    for source, target in [('stop_sequences', 'stop'), ('seed', 'seed'),
                           ('frequency_penalty', 'frequency_penalty'),
                           ('presence_penalty', 'presence_penalty')]:
        value = getattr(config, source, None)
        if value is not None:
            payload[target] = value
    if config.top_k is not None:
        payload['extra_body']['top_k'] = config.top_k
    if config.response_schema or config.response_json_schema or config.response_mime_type:
        raise ValueError('Structured response output is not supported by this prototype adapter')
    tools = []
    for tool in config.tools or []:
        if not isinstance(tool, types.Tool) or not tool.function_declarations:
            raise ValueError('Only declared function tools are supported')
        for declaration in tool.function_declarations:
            parameters = (declaration.parameters_json_schema
                          if declaration.parameters_json_schema is not None
                          else declaration.parameters)
            function = {'name': declaration.name,
                        'parameters': _schema(parameters) if parameters is not None
                        else {'type': 'object', 'properties': {}}}
            if declaration.description:
                function['description'] = declaration.description
            tools.append({'type': 'function', 'function': function})
    if tools:
        payload['tools'] = tools
        payload['tool_choice'] = 'auto'
        calling = config.tool_config.function_calling_config if config.tool_config else None
        if calling:
            mode = getattr(calling.mode, 'value', calling.mode)
            if mode == 'NONE':
                # This pinned route rejects tools + tool_choice='none'. Omitting
                # available tools disables new calls without deleting history.
                del payload['tools']
                del payload['tool_choice']
                return payload
            if mode in {'ANY', 'AUTO'}:
                payload['tool_choice'] = {'ANY': 'required', 'AUTO': 'auto'}[mode]
            elif mode not in {None, 'MODE_UNSPECIFIED'}:
                raise ValueError('Unsupported function-calling mode')
            if calling.allowed_function_names:
                allowed = set(calling.allowed_function_names)
                payload['tools'] = [tool for tool in tools if tool['function']['name'] in allowed]
                if {tool['function']['name'] for tool in payload['tools']} != allowed:
                    raise ValueError('Allowed tool name is not declared')
    return payload


def _count(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def safe_error_classification(exc):
    """Map recognized provider errors to constants without exposing server text."""
    body = getattr(exc, 'body', None)
    body = body if isinstance(body, dict) else {}
    detail = body.get('error', body)
    detail = detail if isinstance(detail, dict) else {}
    message = detail.get('message')
    message = message.lower() if isinstance(message, str) else ''
    if 'no endpoints found' in message or 'no available providers' in message:
        if 'data policy' in message or 'privacy' in message:
            return 'routing_privacy_policy'
        if 'tool' in message:
            return 'routing_tool_support'
        if 'parameter' in message:
            return 'routing_parameter_support'
        return 'routing_no_matching_endpoint'
    if 'context length' in message or 'context window' in message:
        return 'context_length_exceeded'
    if 'tool_choice' in message and ('unsupported' in message or 'not support' in message):
        return 'unsupported_tool_choice'
    return {401: 'authentication_failed', 402: 'insufficient_credits',
            404: 'not_found', 408: 'request_timeout', 429: 'rate_limited',
            502: 'provider_failure', 503: 'provider_unavailable'}.get(
                getattr(exc, 'status_code', None), 'unclassified')


def normalized_usage(raw):
    """OpenRouter completion includes reasoning; cached input is part of prompt."""
    raw = raw if isinstance(raw, dict) else {}
    prompt, completion = _count(raw.get('prompt_tokens')), _count(raw.get('completion_tokens'))
    thoughts = _count((raw.get('completion_tokens_details') or {}).get('reasoning_tokens'))
    cached = _count((raw.get('prompt_tokens_details') or {}).get('cached_tokens'))
    candidates = completion - thoughts if completion is not None and thoughts is not None and thoughts <= completion else None
    return {'prompt_token_count': prompt, 'candidates_token_count': candidates,
            'thoughts_token_count': thoughts, 'cached_content_token_count': cached,
            'total_token_count': _count(raw.get('total_tokens')),
            'completion_token_count': completion}


def response_to_adk(raw):
    choices = raw.get('choices') or []
    if not choices or not isinstance(choices[0].get('message'), dict):
        raise ValueError('Provider returned no assistant message')
    choice, parts = choices[0], []
    message = choice['message']
    reasoning = {}
    if message.get('reasoning_details') is not None:
        reasoning['reasoning_details'] = deepcopy(message['reasoning_details'])
    elif message.get('reasoning') is not None:
        reasoning['reasoning'] = message['reasoning']
    if message.get('reasoning'):
        parts.append(types.Part(text=message['reasoning'], thought=True))
    content = message.get('content')
    if content is not None and not isinstance(content, str):
        raise ValueError('Provider returned unsupported assistant content')
    if content:
        parts.append(types.Part(text=content))
    call_ids = set()
    for call in message.get('tool_calls') or []:
        if call.get('type') != 'function' or not call.get('id') or call['id'] in call_ids:
            raise ValueError('Provider returned an invalid tool call')
        function = call.get('function') or {}
        arguments = json.loads(function['arguments'])
        if not isinstance(arguments, dict) or not function.get('name'):
            raise ValueError('Provider returned invalid tool arguments')
        call_ids.add(call['id'])
        parts.append(types.Part(function_call=types.FunctionCall(
            id=call['id'], name=function['name'], args=arguments)))
    visible = [part for part in parts if not part.thought]
    if not visible:
        raise ValueError('Provider returned no answer or tool call')
    if reasoning:
        visible[0].thought_signature = _SIGNATURE_PREFIX + _json(reasoning).encode('utf-8')
    usage = normalized_usage(raw.get('usage'))
    reason = choice.get('finish_reason')
    finish = {'stop': types.FinishReason.STOP, 'tool_calls': types.FinishReason.STOP,
              'length': types.FinishReason.MAX_TOKENS,
              'content_filter': types.FinishReason.SAFETY}.get(reason)
    return LlmResponse(content=types.Content(role='model', parts=parts),
                       partial=False, finish_reason=finish,
                       model_version=raw.get('model'),
                       usage_metadata=types.GenerateContentResponseUsageMetadata(**{
                           key: value for key, value in usage.items()
                           if key != 'completion_token_count' and value is not None}),
                       custom_metadata={'provider': raw.get('provider'),
                                        'generation_id': raw.get('id')})


class OpenRouterGemma(BaseLlm):
    _client: object = PrivateAttr()
    _records: list = PrivateAttr(default_factory=list)
    _task: str = PrivateAttr(default='preflight')
    _path: Path = PrivateAttr()
    _stop_reasons: dict = PrivateAttr(default_factory=dict)

    def model_copy(self, *, update=None, deep=False):
        """Clone configuration while sharing the owned transport and usage ledger.

        The official compiler asks for a deep copy. SDK clients own connection
        pools and locks that cannot be deep-copied. All public fields here are
        immutable configuration; private transport/metering state intentionally
        stays shared. The task label is copied at compilation time.
        """
        return super().model_copy(update=update, deep=False)

    def _write(self, record):
        with self._path.open('a', encoding='utf-8') as handle:
            handle.write(_json(record) + '\n')

    def _error(self, exc, stage):
        code = getattr(exc, 'status_code', None)
        self._write({'task': self._task, 'error_type': type(exc).__name__,
                     'stage': stage, 'code': code if isinstance(code, int) else None,
                     'classification': safe_error_classification(exc)})

    async def generate_content_async(self, llm_request, stream=False):
        stage = 'request_conversion'
        try:
            if self.model != MODEL_ID or llm_request.model not in {None, MODEL_ID}:
                raise ValueError('Unexpected OpenRouter model ID')
            payload = request_payload(llm_request)
            stage = 'generate_content'
            started = time.monotonic()
            response = await self._client.chat.completions.create(**payload)
            raw = response.model_dump(mode='json') if hasattr(response, 'model_dump') else response
            if raw.get('error'):
                raise ValueError('Provider returned an error response')
            usage = raw.get('usage') or {}
            cost = usage.get('cost')
            if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
                cost = None
            record = {'task': self._task, 'seconds': time.monotonic() - started,
                      'model_version': raw.get('model'), 'requested_model': MODEL_ID,
                      'provider': raw.get('provider'), 'generation_id': raw.get('id'),
                      'cost_usd': cost, 'usage': normalized_usage(usage)}
            # Record returned usage even if assistant message decoding fails.
            self._records.append(record)
            self._write(record)
            stage = 'response_conversion'
            converted = response_to_adk(raw)
        except Exception as exc:
            self._error(exc, stage)
            # Do not include status codes or provider messages in the exception:
            # the official retry plugin matches those strings and would retry.
            raise OpenRouterAdapterError('OpenRouter adapter stopped; inspect sanitized usage metadata.') from None
        yield converted

    async def aclose(self):
        await self._client.close()


def create_openrouter_model(*, api_key, base_url, usage_path, client=None):
    """Create a pinned local-prototype model; client injection is for offline tests."""
    if base_url.rstrip('/') != BASE_URL:
        raise ValueError('Unexpected OpenRouter endpoint')
    if not isinstance(api_key, str) or not api_key:
        raise ValueError('An explicit in-memory OpenRouter API key is required')
    model = OpenRouterGemma(model=MODEL_ID)
    model._path = Path(usage_path)
    model._client = client if client is not None else AsyncOpenAI(
        api_key=api_key, base_url=base_url, max_retries=0, timeout=90.0)
    return model
