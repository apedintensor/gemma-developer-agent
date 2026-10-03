"""Summarize an iteration and compare fixed-task runs without reading task traces.

This command is offline. It reports paired observations, never promotes a candidate.
"""

import argparse
import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['run_id', 'git_commit', 'backend', 'model_id', 'split_version',
          'attempted', 'solved', 'success_rate', 'wall_seconds', 'cost_usd',
          'config_path', 'log_path', 'notes']
TOKEN_FIELDS = ['prompt_token_count', 'candidates_token_count', 'thoughts_token_count',
                'cached_content_token_count', 'total_token_count']
CAPS = {'max_time_minutes', 'max_tool_calls', 'max_turns', 'timeout_seconds'}
LOCAL_QUOTA = 'InputExceedsMinuteQuota'


def read_json(path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def task_ids(value):
    if isinstance(value, dict):
        value = value.get('tasks', value.get('task_ids'))
    if not isinstance(value, list) or not value:
        raise ValueError('A nonempty predeclared task selection is required.')
    ids = [item.get('id') if isinstance(item, dict) else item for item in value]
    if any(not isinstance(item, str) or not item for item in ids) or len(set(ids)) != len(ids):
        raise ValueError('Task selection contains missing or duplicate IDs.')
    return ids


def number(value):
    if value is None:
        return 0
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError('Run metrics must be finite, nonnegative numbers.')
    return value


def file_hash(manifest, group, name):
    values = manifest.get(group) or {}
    if not isinstance(values, dict):
        return None
    return next((value for key, value in values.items() if key.replace('\\', '/') == name), None)


def build_report(directory):
    directory = Path(directory)
    manifest = read_json(directory / 'manifest.json', {})
    selected = read_json(directory / 'selection.json')
    ids = task_ids(selected if selected is not None else manifest)
    manifest_ids = manifest.get('task_ids', manifest.get('tasks'))
    if manifest_ids is not None and task_ids(manifest_ids) != ids:
        raise ValueError('Manifest and frozen task selection disagree.')
    summaries = read_json(directory / 'summary.json', [])
    if not isinstance(summaries, list):
        raise ValueError('summary.json must contain a task-result list.')
    by_id = {}
    for row in summaries:
        task = row.get('task_id')
        if task not in ids or task in by_id:
            raise ValueError('Task results contain an unselected or duplicate ID.')
        if not isinstance(row.get('resolved'), bool):
            raise ValueError('Task results need an explicit boolean resolved value.')
        by_id[task] = row

    warnings = []
    usage_file = directory / 'usage.jsonl'
    if usage_file.exists():
        usage = [json.loads(line) for line in usage_file.read_text(encoding='utf-8').splitlines() if line.strip()]
    else:
        usage = [item for row in summaries for item in row.get('usage', [])]
        warnings.append('usage.jsonl is missing; summary usage may omit errors or interrupted calls.')
    config = read_json(directory / 'evaluation-config.json')
    config_known = isinstance(config, dict) and CAPS <= config.keys()
    if not config_known:
        warnings.append('Effective evaluation caps are unknown or incomplete.')
    model = manifest.get('model_id', manifest.get('model'))
    backend = manifest.get('backend')
    if not model or not backend:
        warnings.append('Model or backend metadata is missing.')
    for key in ['sandbox', 'pacing', 'runtime']:
        if not manifest.get(key):
            warnings.append(f'{key} metadata is missing.')
    if not isinstance(manifest.get('pacing'), dict):
        warnings.append('Structured pacing settings are unavailable.')
    elif not {'estimated_input_tokens', 'window_seconds'} <= manifest['pacing'].keys():
        warnings.append('Structured pacing settings are incomplete.')
    fingerprints = {
        'sandbox_source': file_hash(manifest, 'source_sha256', 'tools/api_sandbox.py'),
        'runner_source': file_hash(manifest, 'source_sha256', 'tools/run_api_baseline.py'),
        'agent_config': file_hash(manifest, 'submission_sha256', 'agent.yaml'),
        'artifacts': manifest.get('artifact_sha256'),
        'dependencies': manifest.get('dependency_sha256'),
    }
    for key, value in fingerprints.items():
        if not value:
            warnings.append(f'{key} fingerprint is unknown; protocol equivalence cannot be established.')
    blockers = list(warnings)

    tokens = {key: sum(number((row.get('usage') or {}).get(key)) for row in usage) for key in TOKEN_FIELDS}
    successful = [row for row in usage if not row.get('error_type') and 'usage' in row]
    timing_sources = {'pacing_wait_seconds': 'pacing_wait_seconds',
                      'count_tokens_seconds': 'count_tokens_seconds',
                      'generation_response_seconds': 'seconds'}
    timings = {key: sum(number(row.get(source)) for row in successful)
               for key, source in timing_sources.items()}
    timing_counts = {key: sum(row.get(source) is not None for row in successful)
                     for key, source in timing_sources.items()}
    api_errors = [row for row in usage if row.get('error_type') and row['error_type'] != LOCAL_QUOTA]
    quota_stops = [row for row in usage if row.get('error_type') == LOCAL_QUOTA]
    outcomes = []
    for task in ids:
        row = by_id.get(task)
        if row is None:
            outcomes.append({'task_id': task, 'completed': False, 'resolved': False,
                             'outcome': 'missing_result', 'duration_seconds': None,
                             'tool_calls': None, 'total_llm_calls': None})
            continue
        task_quota = any(item.get('task') == task for item in quota_stops)
        task_api = any(item.get('task') == task for item in api_errors)
        # Never reproduce SDK errors, model output, patches, or raw harness errors.
        error = str(row.get('error_message') or '').lower()
        if row.get('adapter_stop_reason') or task_quota:
            outcome = 'local_quota_stop' if task_quota or row.get('adapter_stop_reason') == LOCAL_QUOTA else 'local_adapter_stop'
        elif task_api:
            outcome = 'api_error'
        elif 'timeout' in error or 'timed out' in error:
            outcome = 'timeout'
        elif row.get('error_message') or row.get('error'):
            outcome = 'execution_error'
        else:
            outcome = 'resolved' if row['resolved'] else 'unresolved'
        outcomes.append({'task_id': task, 'completed': True, 'resolved': row['resolved'],
                         'outcome': outcome, 'duration_seconds': number(row.get('duration_seconds')),
                         'tool_calls': number(row.get('tool_calls')),
                         'total_llm_calls': number(row.get('total_llm_calls'))})
    missing = [row['task_id'] for row in outcomes if not row['completed']]
    if missing:
        message = 'Missing task results remain in the predeclared denominator; run is incomplete.'
        warnings.append(message)
        blockers.append(message)
    if api_errors:
        message = 'Provider errors occurred; operational failures prevent a controlled comparison.'
        warnings.append(message)
        blockers.append(message)
    execution_errors = any(
        (row.get('error_message') or row.get('error'))
        and 'timeout' not in str(row.get('error_message') or '').lower()
        and 'timed out' not in str(row.get('error_message') or '').lower()
        and not (
            row.get('error_message') == 'Agent completed execution without calling submit_patch.'
            and (row.get('adapter_stop_reason') == LOCAL_QUOTA
                 or any(item.get('task') == row['task_id'] for item in quota_stops))
        )
        for row in summaries
    )
    if execution_errors or any(row['outcome'] == 'local_adapter_stop' for row in outcomes):
        message = 'Unclassified execution or adapter errors prevent a controlled comparison.'
        warnings.append(message)
        blockers.append(message)
    if any(row['outcome'] == 'local_quota_stop' for row in outcomes):
        warnings.append('Local input quota stops occurred. Under identical settings these are comparable workflow outcomes, not a pure model-capability score.')
    resolved = sum(row['resolved'] for row in outcomes)
    return {
        'schema_version': 1, 'run_id': manifest.get('run_id', directory.name),
        'git_commit': manifest.get('git_commit', manifest.get('runner_commit', manifest.get('runner_base_commit'))),
        'backend': backend, 'model_id': model, 'split_version': manifest.get('split_version'),
        'task_ids': ids, 'attempted': len(ids), 'completed': len(by_id), 'resolved': resolved,
        'success_rate': resolved / len(ids), 'missing_task_ids': missing,
        'complete': not missing, 'valid_comparison_gate': not blockers,
        'evaluation_config': config, 'sandbox': manifest.get('sandbox'),
        'pacing': manifest.get('pacing'), 'runtime': manifest.get('runtime'),
        'protocol_fingerprints': fingerprints,
        'successful_api_responses': len(successful),
        'api_errors': len(api_errors), 'local_quota_stops': len(quota_stops),
        'tokens': tokens, 'task_wall_seconds': sum(row['duration_seconds'] or 0 for row in outcomes),
        **timings, 'timing_record_counts': timing_counts,
        'timing_scope': 'Sums from recorded successful generation responses only. Failed/interrupted requests and missing timing fields are excluded; zero records means unknown, not zero elapsed time.',
        'task_outcomes': outcomes, 'cost_usd': None, 'warnings': warnings,
        'comparison_blockers': blockers,
        'usage_scope': 'Recorded response metadata only; interrupted in-flight requests may be absent. Cached input is a subset of prompt tokens, not additional tokens.',
        'promotion': 'manual_review_required',
    }


def compare_reports(candidate, baseline):
    reasons = []
    warnings = []
    for label, report in [('candidate', candidate), ('baseline', baseline)]:
        warnings.extend(f'{label}: {message}' for message in report['warnings'])
        if not report['valid_comparison_gate']:
            reasons.extend(f'{label}: {message}' for message in report['comparison_blockers'])
    for key in ['model_id', 'backend', 'task_ids', 'evaluation_config', 'sandbox', 'pacing', 'runtime']:
        if candidate[key] != baseline[key]:
            reasons.append(f'{key} differs between runs.')
    for key in candidate['protocol_fingerprints']:
        if candidate['protocol_fingerprints'][key] != baseline['protocol_fingerprints'][key]:
            reasons.append(f'{key} fingerprint differs; prompt-only attribution is not supported.')
    comparable = not reasons
    baseline_tasks = {row['task_id']: row for row in baseline['task_outcomes']}
    paired = []
    for row in candidate['task_outcomes']:
        old = baseline_tasks.get(row['task_id'])
        if old is not None:
            complete = row['completed'] and old['completed']
            paired.append({'task_id': row['task_id'], 'both_completed': complete,
                           'baseline_resolved': old['resolved'], 'candidate_resolved': row['resolved'],
                           'resolved_delta': int(row['resolved']) - int(old['resolved']) if complete else None,
                           'wall_seconds_delta': row['duration_seconds'] - old['duration_seconds'] if complete else None})
    return {'baseline_run_id': baseline['run_id'], 'comparable': comparable,
            'warnings': list(dict.fromkeys(warnings + reasons)), 'comparison_blockers': reasons,
            'paired_observations': paired,
            'success_rate_delta': candidate['success_rate'] - baseline['success_rate'] if comparable else None,
            'task_wall_seconds_delta': candidate['task_wall_seconds'] - baseline['task_wall_seconds'] if comparable else None,
            'promotion': 'manual_review_required',
            'interpretation': 'Paired development-task workflow observations under the recorded limits; no automatic promotion, pure capability score, or claim of general improvement.'}


def record_report(report, directory, root=ROOT, *, finalize_incomplete=False):
    """Append a unique ledger row and save the private report; reject collisions."""
    if not report['complete'] and not finalize_incomplete:
        raise ValueError('Incomplete run: wait for completion, or use --finalize-incomplete with --record only after the attempt has ended.')
    directory, root = Path(directory).resolve(), Path(root).resolve()
    relative = directory.relative_to(root / 'runs')
    if not relative.parts:
        raise ValueError('Use a specific directory under the project runs directory.')
    ledger = root / 'experiments/results.csv'
    config_path = (Path('runs') / relative / 'evaluation-config.json').as_posix()
    log_path = (Path('runs') / relative).as_posix() + '/'
    row = {key: '' for key in FIELDS}
    row.update({key: report.get(key) if report.get(key) is not None else ''
                for key in ['run_id', 'git_commit', 'backend', 'model_id', 'split_version', 'attempted', 'success_rate']})
    row.update(solved=report['resolved'], wall_seconds=report['task_wall_seconds'],
               config_path=config_path, log_path=log_path,
               notes=f"Completed {report['completed']}/{report['attempted']}; "
                     f"recorded tokens {report['tokens']['total_token_count']}; "
                     f"API errors {report['api_errors']}; local quota stops {report['local_quota_stops']}; "
                     + ('explicitly finalized incomplete; ' if not report['complete'] else '') +
                     'billing unverified; manual review required')
    row = {key: str(value) for key, value in row.items()}
    with ledger.open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError('Unexpected experiment ledger schema.')
        existing = [item for item in reader if item['run_id'] == row['run_id']]
    if len(existing) > 1 or existing and existing[0] != row:
        raise ValueError('Conflicting run_id already exists in the experiment ledger.')
    report_path = directory / 'report.json'
    saved = read_json(report_path)
    # Comparison is a view that may be added later; the measured run must stay fixed.
    measured = lambda value: {key: item for key, item in value.items() if key != 'comparison'}
    if saved is not None and measured(saved) != measured(report):
        raise ValueError('Conflicting report already exists; use a new run_id.')
    if not existing:
        with ledger.open('a', newline='', encoding='utf-8') as handle:
            csv.DictWriter(handle, fieldnames=FIELDS).writerow(row)
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--compare', type=Path, metavar='BASELINE_RUN_DIR')
    parser.add_argument('--record', action='store_true')
    parser.add_argument('--finalize-incomplete', action='store_true',
                        help='With --record, finalize an ended/interrupted attempt while retaining every selected task in the denominator.')
    args = parser.parse_args()
    if args.finalize_incomplete and not args.record:
        parser.error('--finalize-incomplete requires --record.')
    try:
        report = build_report(args.run_dir)
        if args.compare:
            report['comparison'] = compare_reports(report, build_report(args.compare))
        if args.record:
            record_report(report, args.run_dir, finalize_incomplete=args.finalize_incomplete)
    except (ValueError, OSError, TypeError, KeyError) as exc:
        parser.exit(2, f'Cannot report iteration: {type(exc).__name__}: {exc}\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
