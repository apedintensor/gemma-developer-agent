"""Check empty/reference patches with the official evaluator; never call a model.

Reference fixes remain evaluator-only. These controls are not agent scores.
Run in the Linux harness environment with the task's test dependencies installed.
"""

import argparse
import asyncio
import json
from pathlib import Path
import time


async def run(args: argparse.Namespace) -> None:
    from adk_submission import ModelRegistry
    from swegemma.config import EvalConfig
    from swegemma.harness.verification import verify_task
    from swegemma.models import load_tasks
    from swegemma.sandbox import SubprocessManager

    root = Path(__file__).resolve().parents[1]
    data = root / "data" / "official"
    task = next(t for t in load_tasks(data / "tasks.jsonl") if t.instance_id == args.task)
    if not task.patch.strip() or not task.test_patch.strip():
        raise ValueError("Both reference patch and evaluation tests are required")
    output = root / "runs" / args.run_id
    output.mkdir(parents=True, exist_ok=False)
    manager = SubprocessManager(timeout_seconds=120)
    results = []
    try:
        for name, patch in [("empty_patch", ""), ("reference_patch", task.patch)]:
            destination = output / name
            destination.mkdir()
            config = EvalConfig(
                tasks_path=data / "tasks.jsonl",
                snapshots_dir=data / "snapshots",
                submission_dir=root / "submission",
                results_dir=destination,
                models=ModelRegistry(),
                sandbox="subprocess",
                timeout_seconds=120,
            )
            result = await verify_task(
                manager, config, task, data / "snapshots" / f"{args.task}.tgz",
                agent_patch=patch, start_time=time.perf_counter(),
            )
            (destination / "test-output.log").write_text(result.test_output, encoding="utf-8")
            record = {
                "control": name,
                "task": args.task,
                "resolved": result.resolved,
                "test_exit_code": result.test_exit_code,
                "error": result.error,
                "duration_seconds": result.duration_seconds,
                "model_calls": 0,
            }
            results.append(record)
            print(json.dumps(record), flush=True)
    finally:
        manager.cleanup_all()
    (output / "controls.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    if (results[0]["test_exit_code"] != 1 or results[0]["resolved"]
            or results[1]["test_exit_code"] != 0 or not results[1]["resolved"]
            or any(r["error"] for r in results)):
        raise RuntimeError("Evaluator controls did not meet expected outcomes; inspect private logs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", default="rich_2725")
    parser.add_argument("--run-id", required=True)
    asyncio.run(run(parser.parse_args()))
