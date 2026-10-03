"""Run a frozen public-task diagnostic with Gemma API and official grading.

Linux/WSL only. Credentials stay in the central registry and provider client.
This is an API prototype, not the quantized Kaggle competition submission.
"""

import argparse
import asyncio
import contextlib
from datetime import datetime
import hashlib
from importlib.metadata import distributions, version
import json
import logging
from pathlib import Path
import shutil
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

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
    _stop_reasons: dict = PrivateAttr(default_factory=dict)

    @property
    def api_client(self):
        return self._client

    async def generate_content_async(self, llm_request, stream=False):
        stopped = LlmResponse(content=types.Content(role='model', parts=[types.Part(
            text='Local API adapter stopped: input exceeds the account input-token quota. Retain the current patch for evaluation.')]))
        if self._task in self._stop_reasons:
            yield stopped
            return
        # Gemini API exposes Gemma thinking as on/off, not a numeric budget.
        llm_request.config.thinking_config = types.ThinkingConfig(
            thinking_level='high', include_thoughts=True)
        # Developer API countTokens accepts contents, not the SDK's Vertex-only
        # system_instruction/tools config. Count a conservative text serialization
        # of the complete request, including declarations, for local pacing.
        token_input = llm_request.model_dump_json(exclude_none=True)
        count_started = time.monotonic()
        try:
            counted = await self._client.aio.models.count_tokens(model=self.model, contents=token_input)
        except Exception as exc:
            self.record_error(exc, 'count_tokens')
            raise RuntimeError(f'Gemma token-count error: {type(exc).__name__}') from None
        count_seconds = time.monotonic() - count_started
        tokens = counted.total_tokens + 256
        if tokens > 15500:
            self._stop_reasons[self._task] = 'InputExceedsMinuteQuota'
            with self._path.open('a') as f:
                f.write(json.dumps({'task':self._task, 'error_type':'InputExceedsMinuteQuota',
                                    'input_tokens':tokens}) + '\n')
            yield stopped
            return
        wait_started = time.monotonic()
        while True:
            now = time.monotonic()
            self._window = [(t,n) for t,n in self._window if now-t < 65]
            if sum(n for _,n in self._window) + tokens <= 15500:
                break
            await asyncio.sleep(max(0.1,65-(now-self._window[0][0])))
        self._window.append((time.monotonic(),tokens))
        wait_seconds = time.monotonic() - wait_started
        self._last_request = time.monotonic()
        started = time.monotonic()
        try:
            async for response in super().generate_content_async(llm_request, stream=False):
                record = {'task': self._task, 'seconds': time.monotonic() - started,
                          'count_tokens_seconds': count_seconds,
                          'pacing_wait_seconds': wait_seconds,
                          'estimated_input_tokens': tokens,
                          'model_version': response.model_version,
                          'usage': response.usage_metadata.model_dump(mode='json')
                          if response.usage_metadata else None}
                self._records.append(record)
                with self._path.open('a') as f:
                    f.write(json.dumps(record) + '\n')
                yield response
        except Exception as exc:
            self.record_error(exc, 'generate_content')
            raise RuntimeError(f'Gemma API error: {type(exc).__name__}; code={getattr(exc, "code", None)}') from None

    def record_error(self, exc, stage):
        # Keep provider errors structural: raw messages can contain request data.
        with self._path.open('a') as f:
            f.write(json.dumps({'task': self._task, 'error_type': type(exc).__name__,
                                'stage': stage, 'code': getattr(exc, 'code', None)}) + '\n')


async def main(args):
    async with contextlib.AsyncExitStack() as cleanup:
        await run(args, cleanup)


async def run(args, cleanup):
    from adk_submission import ModelRegistry
    from swegemma.budget import EvaluationBudget
    from swegemma.config import EvalConfig
    from swegemma.evaluate import Evaluator
    from swegemma.models import load_tasks

    root = Path(__file__).resolve().parents[1]
    if not args.run_id or Path(args.run_id).name != args.run_id or args.run_id in {'.', '..'}:
        raise ValueError('run-id must be a single directory name')
    selection_data = json.loads((root / args.selection).read_text())
    selected = selection_data['tasks'] if isinstance(selection_data, dict) else selection_data
    split_version = selection_data.get('split_version', Path(args.selection).stem) if isinstance(selection_data, dict) else Path(args.selection).stem
    if args.task_id:
        selected = [item for item in selected if item['id'] == args.task_id]
        split_version += ':task=' + args.task_id
    if not selected or len({item['id'] for item in selected}) != len(selected):
        raise ValueError('Selection must contain distinct known task IDs')
    submission_source = (root / args.submission_dir).resolve()
    if not (submission_source / 'agent.yaml').is_file():
        raise ValueError('Submission directory must contain agent.yaml')
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
    shutil.copytree(submission_source, submission)
    yaml = submission / 'agent.yaml'
    yaml.write_text(yaml.read_text().replace('gemma-4-31b-it-qat-w4a16-ct', 'gemma-4-31b-it'))
    (output / 'selection.json').write_text(json.dumps(selected, indent=2))
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, check=True,
                            capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(['git', 'status', '--porcelain'], cwd=root, check=True,
                                capture_output=True, text=True).stdout.strip())
    source_dir = output / 'source'
    source_dir.mkdir()
    source_hashes = {}
    for name in ['run_api_baseline.py', 'api_sandbox.py']:
        payload = (root / 'tools' / name).read_bytes()
        (source_dir / name).write_bytes(payload)
        source_hashes['tools/' + name] = hashlib.sha256(payload).hexdigest()
    artifacts = {}
    for path in [root / 'data/official/tasks.jsonl', *[
            root / 'data/official/snapshots' / (item['id'] + '.tgz') for item in selected]]:
        with path.open('rb') as handle:
            artifacts[path.relative_to(root).as_posix()] = hashlib.file_digest(handle, 'sha256').hexdigest()
    (output / 'artifact-checksums.json').write_text(json.dumps(artifacts, indent=2))
    dependencies = sorted({f"{d.metadata['Name']}=={d.version}" for d in distributions()})
    dependencies += ['# Task dependency overlay'] + sorted({
        f"{d.metadata['Name']}=={d.version}" for d in distributions(
            path=[str(Path.home() / '.local/opt/gemma-task-deps')])})
    dependency_bytes = ('\n'.join(dependencies) + '\n').encode()
    (output / 'requirements-freeze.txt').write_bytes(dependency_bytes)
    manifest = {
        'run_id': args.run_id,
        'started_at': datetime.now(ZoneInfo('Australia/Sydney')).isoformat(),
        'git_commit': ('working-tree:' if dirty else '') + commit,
        'backend': 'ai_studio', 'model_id': 'gemma-4-31b-it',
        'split_version': split_version, 'task_ids': [item['id'] for item in selected],
        'source_sha256': source_hashes,
        'artifact_sha256': artifacts,
        'dependency_sha256': hashlib.sha256(dependency_bytes).hexdigest(),
        'submission_sha256': {str(p.relative_to(submission)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(submission.rglob('*')) if p.is_file()},
        'runtime': {'python': sys.version.split()[0], **{name: version(name) for name in
                    ['swegemma', 'adk-submission', 'adk-eval-core', 'google-adk', 'google-genai']}},
        'sandbox': 'subprocess+bubblewrap',
        'pacing': {'estimated_input_tokens': 15500, 'window_seconds': 65},
        'hypothesis': args.hypothesis, 'parent_run': args.parent_run,
    }
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    model = MeteredGemma(model='gemma-4-31b-it')
    model._key = credential.api_key
    model._client = genai.Client(api_key=credential.api_key, vertexai=False,
        http_options=types.HttpOptions(base_url=credential.base_url, timeout=90000,
            retry_options=types.HttpRetryOptions(attempts=1)))
    cleanup.push_async_callback(model._client.aio.aclose)
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
            # An explicit budget is required: max_time_minutes=None alone
            # falls back to the harness's default 60-minute session budget.
            budget=EvaluationBudget(time_minutes=None),
            max_tool_calls=50, max_turns=80,
            timeout_seconds=120, concurrency=1, display_mode='quiet')
        if index == 1:
            (output / 'evaluation-config.json').write_text(json.dumps({
                'max_time_minutes': config.budget.time_minutes,
                'max_tool_calls': config.budget.tool_calls,
                'max_turns': config.budget.turns,
                'timeout_seconds': config.harness.command_timeout_seconds,
            }, indent=2))
        evaluator = Evaluator(config)
        print(json.dumps({'event':'starting', 'task':task_id, 'index':index}), flush=True)
        with (destination / 'harness.log').open('w') as log:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                try:
                    result = await evaluator.evaluate_task(tasks[task_id], index, len(selected))
                finally:
                    evaluator.sandbox.cleanup_all()
        result_data = result.model_dump(mode='json', exclude={'trace'})
        result_data['adapter_stop_reason'] = model._stop_reasons.get(task_id)
        (destination / 'result.json').write_text(json.dumps(result_data, indent=2))
        summary = result.model_dump(mode='json', exclude={'trace', 'agent_patch', 'test_output'})
        summary['adapter_stop_reason'] = model._stop_reasons.get(task_id)
        summary['usage'] = [r for r in model._records if r['task'] == task_id]
        summaries.append(summary)
        (output / 'summary.json').write_text(json.dumps(summaries, indent=2))
        print(json.dumps({'event':'completed', 'task':task_id, 'resolved':result.resolved,
                          'seconds':result.duration_seconds, 'tool_calls':result.tool_calls,
                          'api_responses':len(summary['usage']), 'error':result.error}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', default='experiments/api-diagnostic-10-v1.json')
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--task-id', help='Run only this ID from the frozen selection')
    parser.add_argument('--submission-dir', default='submission', help='Agent configuration to snapshot for this run')
    parser.add_argument('--hypothesis', default='', help='One predeclared change or baseline question')
    parser.add_argument('--parent-run', help='Run ID used as the baseline for this iteration')
    parser.add_argument('--bwrap', default='~/.local/opt/gemma-bwrap/usr/bin/bwrap')
    logging.disable(logging.CRITICAL)
    asyncio.run(main(parser.parse_args()))
