"""Protect iteration decisions and ledger integrity using only synthetic runs."""

import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location('iteration_report', Path(__file__).resolve().parents[1] / 'tools/iteration_report.py')
reporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reporter)


class IterationReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'experiments').mkdir()
        with (self.root / 'experiments/results.csv').open('w', newline='', encoding='utf-8') as handle:
            csv.writer(handle).writerow(reporter.FIELDS)

    def write(self, path, value):
        path.write_text(json.dumps(value), encoding='utf-8')

    def fixture(self, name, results=None):
        directory = self.root / 'runs' / name
        directory.mkdir(parents=True)
        self.write(directory / 'selection.json', [{'id': 'task_a'}, {'id': 'task_b'}])
        self.write(directory / 'manifest.json', {
            'run_id': name, 'git_commit': 'abc', 'model_id': 'gemma-4-31b-it',
            'backend': 'ai_studio', 'split_version': 'synthetic-v1',
            'task_ids': ['task_a', 'task_b'], 'sandbox': 'subprocess+bubblewrap',
            'pacing': {'estimated_input_tokens': 15500, 'window_seconds': 65},
            'runtime': {'example': '1.0'},
            'submission_sha256': {'prompts/system.md': name, 'agent.yaml': 'same-agent'},
            'source_sha256': {'tools/api_sandbox.py': 'same-sandbox', 'tools/run_api_baseline.py': 'same-runner'},
            'artifact_sha256': {'tasks': 'same-tasks', 'snapshots': 'same-snapshots'},
            'dependency_sha256': {'overlay': 'same-dependencies'},
        })
        self.write(directory / 'evaluation-config.json', {
            'max_time_minutes': None, 'max_tool_calls': 50, 'max_turns': 80, 'timeout_seconds': 120,
        })
        self.write(directory / 'summary.json', results if results is not None else [
            {'task_id': 'task_a', 'resolved': True, 'duration_seconds': 10, 'tool_calls': 2},
            {'task_id': 'task_b', 'resolved': False, 'duration_seconds': 20, 'tool_calls': 3},
        ])
        usage = [{'task': 'task_a', 'usage': {'prompt_token_count': 100, 'cached_content_token_count': 60,
                                            'candidates_token_count': 10, 'thoughts_token_count': 5,
                                            'total_token_count': 115}}]
        (directory / 'usage.jsonl').write_text('\n'.join(json.dumps(row) for row in usage), encoding='utf-8')
        return directory

    def openrouter_fixture(self, name, usage):
        directory = self.fixture(name)
        manifest = reporter.read_json(directory / 'manifest.json')
        manifest.update(backend='openrouter', model_id='google/gemma-4-31b-it',
                        pacing={'mode': 'provider_managed', 'estimated_input_tokens': None,
                                'window_seconds': None, 'automatic_retries': 0},
                        provider_config={'only': ['deepinfra/fp8'], 'allow_fallbacks': False,
                                         'require_parameters': True},
                        reasoning_config={'enabled': True, 'max_tokens': 4096}, local_context_cap=None)
        manifest['source_sha256']['tools/openrouter_model.py'] = 'same-openrouter-adapter'
        self.write(directory / 'manifest.json', manifest)
        (directory / 'usage.jsonl').write_text('\n'.join(json.dumps(row) for row in usage), encoding='utf-8')
        return directory

    def routed_response(self, cost=0.125, provider='DeepInfra', model='google/gemma-4-31b-it'):
        return {'task': 'task_a', 'generation_id': 'synthetic-id', 'provider': provider,
                'model_version': model, 'cost_usd': cost, 'usage': {
                    'prompt_token_count': 100, 'cached_content_token_count': 80,
                    'candidates_token_count': 10, 'thoughts_token_count': 5,
                    'total_token_count': 115}}

    def test_missing_results_remain_in_denominator_and_block_comparison(self):
        baseline = self.fixture('baseline')
        incomplete = self.fixture('partial', [{'task_id': 'task_a', 'resolved': True, 'duration_seconds': 5}])
        report = reporter.build_report(incomplete)
        self.assertEqual((report['attempted'], report['completed'], report['success_rate']), (2, 1, 0.5))
        self.assertEqual(report['missing_task_ids'], ['task_b'])
        self.assertFalse(report['valid_comparison_gate'])
        comparison = reporter.compare_reports(report, reporter.build_report(baseline))
        self.assertFalse(comparison['comparable'])
        self.assertIsNone(comparison['success_rate_delta'])
        self.assertIsNone(comparison['paired_observations'][1]['resolved_delta'])

    def test_provider_usage_is_not_double_counted_and_sensitive_fields_are_omitted(self):
        directory = self.fixture('usage')
        summary = reporter.read_json(directory / 'summary.json')
        summary[0].update(usage=[{'usage': {'total_token_count': 999}}], agent_patch='SECRET PATCH',
                          error_message='SECRET RAW SDK ERROR', trace='SECRET TRACE')
        self.write(directory / 'summary.json', summary)
        with (directory / 'usage.jsonl').open('a', encoding='utf-8') as handle:
            handle.write('\n' + json.dumps({'task': 'task_a', 'error_type': 'InputExceedsMinuteQuota'}))
            handle.write('\n' + json.dumps({'task': 'task_b', 'error_type': 'ClientError', 'message': 'SECRET API ERROR'}))
        report = reporter.build_report(directory)
        self.assertEqual(report['tokens']['total_token_count'], 115)
        self.assertEqual(report['tokens']['prompt_token_count'], 100)
        self.assertEqual(report['tokens']['cached_content_token_count'], 60)
        self.assertEqual((report['successful_api_responses'], report['api_errors'], report['local_quota_stops']), (1, 1, 1))
        self.assertEqual(report['task_outcomes'][0]['outcome'], 'local_quota_stop')
        self.assertTrue(report['task_outcomes'][0]['resolved'])
        self.assertNotIn('SECRET', json.dumps(report))

    def test_different_conditions_warn_and_unknown_legacy_caps_are_not_assumed(self):
        baseline = reporter.build_report(self.fixture('baseline'))
        changes = {'model_id': 'other', 'backend': 'official_harness', 'task_ids': ['other'],
                   'evaluation_config': {'max_time_minutes': 4}, 'sandbox': 'other', 'pacing': {}}
        for key, value in changes.items():
            with self.subTest(key=key):
                candidate = dict(baseline, **{key: value})
                comparison = reporter.compare_reports(candidate, baseline)
                self.assertFalse(comparison['comparable'])
                self.assertTrue(any(key in warning for warning in comparison['warnings']))
        legacy = self.fixture('legacy')
        (legacy / 'evaluation-config.json').unlink()
        manifest = reporter.read_json(legacy / 'manifest.json')
        manifest['time_minutes_per_task'] = 4
        self.write(legacy / 'manifest.json', manifest)
        self.assertFalse(reporter.compare_reports(reporter.build_report(legacy), baseline)['comparable'])

    def test_changed_artifacts_dependencies_and_agent_settings_prevent_prompt_attribution(self):
        baseline = reporter.build_report(self.fixture('baseline'))
        directory = self.fixture('candidate')
        manifest = reporter.read_json(directory / 'manifest.json')
        manifest['artifact_sha256']['tasks'] = 'other-task-data'
        manifest['dependency_sha256']['overlay'] = 'other-dependencies'
        manifest['submission_sha256']['agent.yaml'] = 'other-sampling-and-tools'
        self.write(directory / 'manifest.json', manifest)
        comparison = reporter.compare_reports(reporter.build_report(directory), baseline)
        self.assertFalse(comparison['comparable'])
        for key in ['artifacts', 'dependencies', 'agent_config']:
            self.assertTrue(any(key in warning for warning in comparison['warnings']))

    def test_prompt_candidate_can_compare_without_automatic_promotion(self):
        baseline = reporter.build_report(self.fixture('baseline'))
        candidate_dir = self.fixture('candidate', [
            {'task_id': 'task_a', 'resolved': True, 'duration_seconds': 10},
            {'task_id': 'task_b', 'resolved': True, 'duration_seconds': 30},
        ])
        candidate = reporter.build_report(candidate_dir)
        comparison = reporter.compare_reports(candidate, baseline)
        self.assertTrue(comparison['comparable'])
        self.assertEqual(comparison['success_rate_delta'], 0.5)
        self.assertEqual(comparison['promotion'], 'manual_review_required')

    def test_quota_stop_is_comparable_workflow_outcome_with_warning_and_manual_review(self):
        baseline_dir = self.fixture('quota-baseline')
        summaries = reporter.read_json(baseline_dir / 'summary.json')
        summaries[1]['adapter_stop_reason'] = 'InputExceedsMinuteQuota'
        summaries[1]['error_message'] = 'Agent completed execution without calling submit_patch.'
        self.write(baseline_dir / 'summary.json', summaries)
        with (baseline_dir / 'usage.jsonl').open('a', encoding='utf-8') as handle:
            handle.write('\n' + json.dumps({'task': 'task_b', 'error_type': 'InputExceedsMinuteQuota'}))
        baseline = reporter.build_report(baseline_dir)
        candidate = reporter.build_report(self.fixture('resolved-candidate', [
            {'task_id': 'task_a', 'resolved': True, 'duration_seconds': 10},
            {'task_id': 'task_b', 'resolved': True, 'duration_seconds': 30},
        ]))
        comparison = reporter.compare_reports(candidate, baseline)
        self.assertTrue(baseline['valid_comparison_gate'])
        self.assertEqual(baseline['comparison_blockers'], [])
        self.assertTrue(comparison['comparable'])
        self.assertEqual(comparison['success_rate_delta'], 0.5)
        self.assertTrue(any('quota' in warning for warning in comparison['warnings']))
        self.assertEqual(comparison['promotion'], 'manual_review_required')
        summaries[1]['error_message'] = 'Unexpected sandbox failure'
        self.write(baseline_dir / 'summary.json', summaries)
        self.assertFalse(reporter.compare_reports(candidate, reporter.build_report(baseline_dir))['comparable'])
        summaries[1]['error_message'] = 'Agent completed execution without calling submit_patch.'
        summaries[1]['adapter_stop_reason'] = None
        self.write(baseline_dir / 'summary.json', summaries)
        (baseline_dir / 'usage.jsonl').write_text('', encoding='utf-8')
        self.assertFalse(reporter.compare_reports(candidate, reporter.build_report(baseline_dir))['comparable'])

    def test_record_is_idempotent_and_conflict_does_not_replace_evidence(self):
        directory = self.fixture('record')
        report = reporter.build_report(directory)
        reporter.record_report(report, directory, self.root)
        before = (self.root / 'experiments/results.csv').read_bytes()
        reporter.record_report(report, directory, self.root)
        self.assertEqual(before, (self.root / 'experiments/results.csv').read_bytes())
        with (self.root / 'experiments/results.csv').open(newline='', encoding='utf-8') as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['cost_usd'], '')
        original_report = (directory / 'report.json').read_bytes()
        changed = dict(report, resolved=2, success_rate=1)
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            reporter.record_report(changed, directory, self.root)
        self.assertEqual(before, (self.root / 'experiments/results.csv').read_bytes())
        self.assertEqual(original_report, (directory / 'report.json').read_bytes())

    def test_incomplete_run_requires_explicit_finalization_without_excluding_missing_tasks(self):
        directory = self.fixture('interrupted', [{'task_id': 'task_a', 'resolved': True, 'duration_seconds': 5}])
        report = reporter.build_report(directory)
        before = (self.root / 'experiments/results.csv').read_bytes()
        with self.assertRaisesRegex(ValueError, 'Incomplete run'):
            reporter.record_report(report, directory, self.root)
        self.assertEqual(before, (self.root / 'experiments/results.csv').read_bytes())
        self.assertFalse((directory / 'report.json').exists())
        result = subprocess.run([sys.executable, str(Path(reporter.__file__)), str(directory), '--finalize-incomplete'],
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn('requires --record', result.stderr)
        reporter.record_report(report, directory, self.root, finalize_incomplete=True)
        reporter.record_report(report, directory, self.root, finalize_incomplete=True)
        with (self.root / 'experiments/results.csv').open(newline='', encoding='utf-8') as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['attempted'], rows[0]['solved'], rows[0]['success_rate']), ('2', '1', '0.5'))
        self.assertIn('explicitly finalized incomplete', rows[0]['notes'])
        saved = reporter.read_json(directory / 'report.json')
        self.assertFalse(saved['complete'])
        self.assertEqual(saved['missing_task_ids'], ['task_b'])

    def test_timings_cover_only_recorded_successful_responses_and_expose_missing_measurements(self):
        directory = self.fixture('timings')
        rows = [
            {'task': 'task_a', 'usage': {}, 'seconds': 3, 'pacing_wait_seconds': 60, 'count_tokens_seconds': 1.5},
            {'task': 'task_a', 'usage': {}, 'seconds': 4},
            {'task': 'task_b', 'error_type': 'ClientError', 'seconds': 80, 'pacing_wait_seconds': 90},
        ]
        (directory / 'usage.jsonl').write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
        report = reporter.build_report(directory)
        self.assertEqual((report['pacing_wait_seconds'], report['count_tokens_seconds'], report['generation_response_seconds']),
                         (60, 1.5, 7))
        self.assertEqual(report['timing_record_counts'], {'pacing_wait_seconds': 1, 'count_tokens_seconds': 1,
                                                        'generation_response_seconds': 2})
        self.assertIn('recorded successful', report['timing_scope'])

    def test_openrouter_cost_uses_response_metadata_and_cached_input_is_not_added_again(self):
        directory = self.openrouter_fixture('paid', [self.routed_response(0.125), self.routed_response(0.375),
                                                    {'task': 'task_b', 'error_type': 'ClientError', 'cost_usd': 99}])
        report = reporter.build_report(directory)
        self.assertEqual(report['cost_usd'], 0.5)
        self.assertEqual((report['cost_reported_responses'], report['cost_missing_responses']), (2, 0))
        self.assertTrue(report['cost_complete_for_recorded_responses'])
        self.assertEqual(report['tokens']['prompt_token_count'], 200)
        self.assertEqual(report['tokens']['cached_content_token_count'], 160)
        self.assertEqual(report['tokens']['total_token_count'], 230)
        self.assertIn('not an invoice', report['cost_scope'])
        reporter.record_report(report, directory, self.root)
        with (self.root / 'experiments/results.csv').open(newline='', encoding='utf-8') as handle:
            row = next(csv.DictReader(handle))
        self.assertEqual(row['cost_usd'], '0.5')
        self.assertIn('not invoice', row['notes'])

    def test_missing_cost_stays_unknown_while_explicit_provider_zero_is_preserved(self):
        directory = self.openrouter_fixture('partial-cost', [self.routed_response(0.125), self.routed_response(None)])
        report = reporter.build_report(directory)
        self.assertIsNone(report['cost_usd'])
        self.assertEqual(report['known_response_cost_usd'], 0.125)
        self.assertEqual((report['cost_reported_responses'], report['cost_missing_responses']), (1, 1))
        self.assertFalse(report['cost_complete_for_recorded_responses'])
        reporter.record_report(report, directory, self.root)
        with (self.root / 'experiments/results.csv').open(newline='', encoding='utf-8') as handle:
            self.assertEqual(next(csv.DictReader(handle))['cost_usd'], '')
        zero = reporter.build_report(self.openrouter_fixture('zero-cost', [self.routed_response(0)]))
        self.assertEqual(zero['cost_usd'], 0)
        self.assertTrue(zero['cost_complete_for_recorded_responses'])
        empty = reporter.build_report(self.openrouter_fixture('no-responses', []))
        self.assertIsNone(empty['cost_usd'])
        self.assertIsNone(empty['known_response_cost_usd'])

    def test_actual_routing_and_provider_configuration_are_required_for_prompt_comparison(self):
        baseline = reporter.build_report(self.openrouter_fixture('route-baseline', [self.routed_response()]))
        same = reporter.build_report(self.openrouter_fixture('route-same', [self.routed_response(), self.routed_response()]))
        self.assertTrue(reporter.compare_reports(same, baseline)['comparable'])
        self.assertEqual(baseline['routed_providers'], ['DeepInfra'])
        self.assertEqual(baseline['response_models'], ['google/gemma-4-31b-it'])
        for name, usage in [
            ('changed-provider', [self.routed_response(provider='OtherProvider')]),
            ('changed-model', [self.routed_response(model='other-model')]),
            ('mixed-provider', [self.routed_response(), self.routed_response(provider='OtherProvider')]),
            ('unknown-provider', [self.routed_response(provider=None)]),
            ('unknown-model', [self.routed_response(model=None)]),
        ]:
            with self.subTest(name=name):
                candidate = reporter.build_report(self.openrouter_fixture(name, usage))
                comparison = reporter.compare_reports(candidate, baseline)
                self.assertFalse(comparison['comparable'])
                self.assertTrue(comparison['comparison_blockers'])
                self.assertIsNone(comparison['success_rate_delta'])
        changed_config = self.openrouter_fixture('changed-routing-config', [self.routed_response()])
        manifest = reporter.read_json(changed_config / 'manifest.json')
        manifest['provider_config']['allow_fallbacks'] = True
        self.write(changed_config / 'manifest.json', manifest)
        self.assertFalse(reporter.compare_reports(reporter.build_report(changed_config), baseline)['comparable'])
        manifest['provider_config']['allow_fallbacks'] = False
        for key, value in [('reasoning_config', {'enabled': False}), ('local_context_cap', 32000)]:
            with self.subTest(setting=key):
                changed = dict(manifest, **{key: value})
                self.write(changed_config / 'manifest.json', changed)
                comparison = reporter.compare_reports(reporter.build_report(changed_config), baseline)
                self.assertFalse(comparison['comparable'])
                self.assertTrue(any('model_request_settings' in message for message in comparison['warnings']))
        ai_studio = reporter.build_report(self.fixture('ai-studio-comparison'))
        self.assertFalse(reporter.compare_reports(baseline, ai_studio)['comparable'])

    def test_unselected_duplicate_or_conflicting_tasks_are_rejected(self):
        directory = self.fixture('invalid')
        self.write(directory / 'summary.json', [{'task_id': 'not_selected', 'resolved': True}])
        with self.assertRaisesRegex(ValueError, 'unselected or duplicate'):
            reporter.build_report(directory)
        self.write(directory / 'selection.json', [{'id': 'task_a'}, {'id': 'task_a'}])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            reporter.build_report(directory)


if __name__ == '__main__':
    unittest.main()
