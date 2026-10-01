# Baseline runbook

Checkpoint: October 2, 2026 (Australia/Sydney).

## Verified outcome

The baseline compiled using the official libraries and was submitted to Kaggle as submission **56753224** at 2026-10-01 14:45:14 UTC (2026-10-02 00:45:14 Sydney). The first status check returned **PENDING**, with no score. Do not describe it as a completed model evaluation until Kaggle reports a terminal result.

The uploaded archive SHA256 is `5993d3141be52bf06411eab0718507dae65fd27b6bd1222a1cf01b1b841fd974`. Kaggle requires the filename `submission.zip`; the API rejected an earlier differently named archive with HTTP 400 and created no submission.

## Official sources and local assets

- [Competition data and HARNESS_README.md](https://www.kaggle.com/competitions/gemma-4-developer-agent/data).
- [Harness wheelhouse](https://www.kaggle.com/datasets/metric/gemma-4-developer-agent-wheelhouse).
- [Submission status](https://www.kaggle.com/competitions/gemma-4-developer-agent/submissions).

Downloaded into ignored `data/official/`: official guide, sample submission, Docker specifications, sandbox setup, `tasks.jsonl`, all 124 public dependency wheels (~27.8 MB), and the `rich_2725` snapshot (~91.7 MB). The full 22.42 GB dataset and model weights were not downloaded. Reference fixes and test patches stay in ignored evaluator data and are not packaged or given to the agent.

Downloaded harness wheels are under ignored `data/harness-wheels/`. Installed versions are `swegemma==0.2.7`, `adk-submission==0.2.12`, `adk-eval-core==0.1.0`, `google-adk==1.39.1`, and Python 3.13.15 on WSL Ubuntu. CPU PyTorch was selected for local validation; no local inference service is running.

## Recreate the local validation environment

Use Linux/WSL with Python 3.13 and uv. Download the official artifacts through an authenticated Kaggle account that has accepted the competition rules. Obtain the three exact harness wheels above from the linked wheelhouse, keeping assets outside Git.

From the project root, a portable environment setup is:

```sh
uv venv data/runtime --python 3.13
uv pip install --python data/runtime/bin/python --torch-backend cpu data/harness-wheels/*.whl
uv pip install --python data/runtime/bin/python --no-index --find-links data/official/wheels pytest==9.1.1
uv pip install --python data/runtime/bin/python pytest-timeout==2.1.0
data/runtime/bin/python tools/package_baseline.py
data/runtime/bin/python tools/verify_controls.py --run-id unique-control-run
```

The owner's verified runtime is an existing WSL environment at `~/.venvs/gemma-baseline`; its Python can be used instead of `data/runtime/bin/python`. The first two installation commands resolve transitive dependencies; the exact installed package snapshot and artifact checksums are preserved locally in `runs/baseline-environment/`.

The subprocess backend inherits host site-packages and skips the Docker dependency bootstrap. It therefore needs pytest and task dependencies in the host runtime. The first control attempt failed with `No module named pytest`; installing pytest and pytest-timeout fixed that setup failure without modifying the harness or task code.

## Evaluator controls (not agent performance)

`tools/verify_controls.py` calls the official `verify_task` with an empty patch and then the dataset reference patch in separate fresh subprocess sandboxes. It never starts an agent or calls a model.

| Control on rich_2725 | Outcome | Tests |
|---|---|---|
| Empty patch | Unresolved; pytest exit 1 | 15 passed, 4 failed |
| Reference patch | Resolved; pytest exit 0; JUnit validated by harness | 19 passed |

Private logs: `runs/rich-2725-controls-20261002/`. These controls verify patch application and test evaluation on one public task. They do not establish model accuracy, Docker isolation fidelity or a validation-set score. Treat this task as an environment diagnostic, not a held-out tuning benchmark.

## Model execution

The competition guide specifies 4 NVIDIA L4 GPUs (96 GB aggregate), vLLM tensor parallelism 4, GPU memory utilization 0.80, a 32,768-token context, and `gemma4` tool/reasoning parsers. The exact quantized weights alone are approximately 16–18 GB. The owner's RTX 4060 has 8 GB; the competition serving configuration cannot run there unchanged.

The owner selected Kaggle official evaluation for the first model run. No paid GPU was provisioned and no prototype model was substituted. Docker Desktop failed to bring up its Linux engine locally; WSL subprocess controls succeeded independently.

For a future local run, first start and verify an OpenAI-compatible inference endpoint serving the exact model. The CLI does not start the model server. Then use a clean process with no conflicting provider environment and explicit local routing:

```sh
LOCAL_INFERENCE_URL=http://127.0.0.1:8000/v1 LOCAL_API_KEY=EMPTY \
swegemma eval --tasks data/official/tasks.jsonl \
  --snapshots-dir data/official/snapshots --submission-dir submission \
  --results-dir runs/unique-agent-run --sandbox subprocess \
  --task-id rich_2725 --concurrency 1 --max-tool-calls 50 \
  --max-time-minutes 4 --max-turns 80 --timeout-seconds 120 --display quiet
```

Before running, unset conflicting `MODEL_PROXY_URL`, `LITELLM_API_BASE`, `MODEL_PROXY_API_KEY` and `LITELLM_API_KEY` in that child process only. Use registry-loaded credentials for an authenticated remote endpoint; do not put keys in shell commands. The official CLI does not load submission `eval_config.yaml`, so the matching limits are supplied explicitly above.

Poll submission 56753224 before any additional upload. Keep all failures and timeouts in future baseline denominators. Freeze validation task IDs before prompt tuning, and record actual scores only after evaluation completes.
