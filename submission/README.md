# Single-agent baseline

The baseline uses the required `gemma-4-31b-it-qat-w4a16-ct` model, six workspace tools, no adapters and no subagents. It is our initial configuration, not an unchanged copy of the official multi-agent/LoRA example.

Run `python tools/package_baseline.py` in the official harness environment to compile the configuration and create `dist/submission.zip`. The archive includes only `agent.yaml`, `eval_config.yaml` and `prompts/system.md`, with no enclosing directory. Compilation makes no model request.

Per-task limits: four minutes, 50 tool calls, 80 turns and a 120-second command timeout. Sampling follows the official example: temperature 0.2, top-p 0.95, 16,384 output tokens and a 4,096-token thinking budget.

See [the runbook](../docs/BASELINE.md) for source versions, evaluator controls and the initial Kaggle submission. A compiled package is not evidence of a successful model run.
