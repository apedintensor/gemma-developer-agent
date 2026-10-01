"""Run a frozen public-task diagnostic with Gemma API and official grading.

Linux/WSL only. Credentials stay in the central registry and provider client.
This is an API prototype, not the quantized Kaggle competition submission.
"""

import argparse
import asyncio
import contextlib
import json
import logging
from pathlib import Path
import shutil
import sys
import time

from pydantic import PrivateAttr
from google import genai
from google.genai import types
from google.adk.models.google_llm import Gemini
from google.adk.models.llm_response import LlmResponse

from api_sandbox import install_isolation, check_isolation


class MeteredGemma(Gemini):
    _client: object = PrivateAttr()
    _records: list = PrivateAttr(default_factory=list)
    _task: str = PrivateAttr(default='preflight')
    _path: Path = PrivateAttr()
    _last_request: float = PrivateAttr(default=0)
    _key: str = PrivateAttr(default='')
    _window: list = PrivateAttr(default_factory=list)

    @property
    def api_client(self):
        return self._client

    async def generate_content_async(self, llm_request, stream=False):
        # Gemini API exposes Gemma thinking as on/off, not a numeric budget.
        llm_request.config.thinking_config = types.ThinkingConfig(
            thinking_level='high', include_thoughts=True)
        # Developer API countTokens accepts contents, not the SDK's Vertex-only
        # system_instruction/tools config. Count a conservative text serialization
        # of the complete request, including declarations, for local pacing.
        token_input = llm_request.model_dump_json(exclude_none=True)
        counted = await self._client.aio.models.count_tokens(model=self.model, contents=token_input)
        tokens = counted.total_tokens + 256
        if tokens > 15500:
            with self._path.open('a') as f:
                f.write(json.dumps({'task':self._task, 'error_type':'InputExceedsMinuteQuota',
                                    'input_tokens':tokens}) + '\n')
            yield LlmResponse(content=types.Content(role='model', parts=[types.Part(
                text='Local API adapter stopped: input exceeds the account input-token quota. Retain the current patch for evaluation.')] ))
            return
        while True:
            now = time.monotonic()
            self._window = [(t,n) for t,n in self._window if now-t < 65]
            if sum(n for _,n in self._window) + tokens <= 15500:
                break
            await asyncio.sleep(max(0.1,65-(now-self._window[0][0])))
        self._window.append((time.monotonic(),tokens))
        self._last_request = time.monotonic()
        started = time.monotonic()
        try:
            async for response in super().generate_content_async(llm_request, stream=False):
                record = {'task': self._task, 'seconds': time.monotonic() - started,
                          'model_version': response.model_version,
                          'usage': response.usage_metadata.model_dump(mode='json')
                          if response.usage_metadata else None}
                self._records.append(record)
                with self._path.open('a') as f:
                    f.write(json.dumps(record) + '\n')
                yield response
        except Exception as exc:
            # Do not log raw SDK exceptions, which can include request details.
            with self._path.open('a') as f:
                f.write(json.dumps({'task': self._task, 'error_type': type(exc).__name__,
                                    'code': getattr(exc, 'code', None),
                                    'message': str(exc).replace(self._key, '[REDACTED]')[:4000]}) + '\n')
            raise RuntimeError(f'Gemma API error: {type(exc).__name__}; code={getattr(exc, "code", None)}') from None


async def main(args):
    from adk_submission import ModelRegistry
    from swegemma.config import EvalConfig
    from swegemma.evaluate import Evaluator
    from swegemma.models import load_tasks

    root = Path(__file__).resolve().parents[1]
    local = json.loads((root / 'configs/local.json').read_text())
    sys.path.insert(0, local['registry_wsl'])
    from api_registry import load_api
    credential = load_api('gemini', profile=local['profile'])
    if credential.base_url.rstrip('/') != 'https://generativelanguage.googleapis.com':
        raise ValueError('Unexpected central Gemini endpoint')
    install_isolation(Path(args.bwrap).expanduser())
    check_isolation()
    output = root / 'runs' / args.run_id
    output.mkdir(exist_ok=False, parents=True)
    submission = output / 'submission'
    shutil.copytree(root / 'submission', submission)
    yaml = submission / 'agent.yaml'
    yaml.write_text(yaml.read_text().replace('gemma-4-31b-it-qat-w4a16-ct', 'gemma-4-31b-it'))
    selected = json.loads((root / args.selection).read_text())
    if isinstance(selected, dict):
        selected = selected['tasks']
    (output / 'selection.json').write_text(json.dumps(selected, indent=2))
    model = MeteredGemma(model='gemma-4-31b-it')
    model._key = credential.api_key
    model._client = genai.Client(api_key=credential.api_key, vertexai=False,
        http_options=types.HttpOptions(base_url=credential.base_url, timeout=90000,
            retry_options=types.HttpRetryOptions(attempts=1)))
    model._path = output / 'usage.jsonl'
    registry = ModelRegistry()
    registry.register('gemma-4-31b-it', model)
    tasks = {t.instance_id: t for t in load_tasks(root / 'data/official/tasks.jsonl')}
    summaries = []
    for index, item in enumerate(selected, 1):
        task_id = item['id']
        model._task = task_id
        destination = output / task_id
        destination.mkdir()
        config = EvalConfig(tasks_path=root / 'data/official/tasks.jsonl',
            snapshots_dir=root / 'data/official/snapshots', results_dir=destination,
            submission_dir=submission, models=registry, sandbox='subprocess',
            max_time_minutes=4, max_tool_calls=50, max_turns=80,
            timeout_seconds=120, concurrency=1, display_mode='quiet')
        evaluator = Evaluator(config)
        print(json.dumps({'event':'starting', 'task':task_id, 'index':index}), flush=True)
        with (destination / 'harness.log').open('w') as log:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                try:
                    result = await evaluator.evaluate_task(tasks[task_id], index, len(selected))
                finally:
                    evaluator.sandbox.cleanup_all()
        (destination / 'result.json').write_text(result.model_dump_json(exclude={'trace'}, indent=2))
        summary = result.model_dump(mode='json', exclude={'trace', 'agent_patch', 'test_output'})
        summary['usage'] = [r for r in model._records if r['task'] == task_id]
        summaries.append(summary)
        (output / 'summary.json').write_text(json.dumps(summaries, indent=2))
        print(json.dumps({'event':'completed', 'task':task_id, 'resolved':result.resolved,
                          'seconds':result.duration_seconds, 'tool_calls':result.tool_calls,
                          'api_responses':len(summary['usage']), 'error':result.error}), flush=True)
    await model._client.aio.aclose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', default='experiments/api-diagnostic-10-v1.json')
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--bwrap', default='~/.local/opt/gemma-bwrap/usr/bin/bwrap')
    logging.disable(logging.CRITICAL)
    asyncio.run(main(parser.parse_args()))
