"""Summarize locally recorded provider usage without exposing task contents."""

import argparse
import json
from pathlib import Path


def summarize(directory: Path) -> dict:
    usage_path = directory / 'usage.jsonl'
    rows = [json.loads(line) for line in usage_path.read_text().splitlines()] if usage_path.exists() else []
    fields = ['prompt_token_count', 'candidates_token_count', 'thoughts_token_count',
              'cached_content_token_count', 'total_token_count']
    totals = {field: sum((row.get('usage') or {}).get(field) or 0 for row in rows) for field in fields}
    summaries = json.loads((directory / 'summary.json').read_text()) if (directory / 'summary.json').exists() else []
    return {
        'run_id': directory.name,
        'completed_tasks': len(summaries),
        'resolved_tasks': sum(bool(r.get('resolved')) for r in summaries),
        'successful_api_responses': sum('usage' in r for r in rows),
        'api_errors': sum('error_type' in r for r in rows),
        'tokens': totals,
        'task_wall_seconds': sum(r.get('duration_seconds', 0) for r in summaries),
        'tasks': [{k: r.get(k) for k in ['task_id', 'resolved', 'duration_seconds',
                                      'tool_calls', 'total_llm_calls', 'error_message']}
                  for r in summaries],
        'usage_scope': 'Successful responses with returned usage only; interrupted in-flight requests may be absent.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.run_directory), indent=2))
