# Gemma API diagnostic

This experiment uses Google AI Studio `gemma-4-31b-it` through the Gemini
generateContent API. It is separate from Kaggle's required quantized model and
must not be reported as an official competition score.

Measured outcome: see [API_RESULTS.md](API_RESULTS.md) for final usage, cost estimate and all ten task outcomes.

The October 3 single-task follow-up is documented in
[ITERATION_RESULTS.md](ITERATION_RESULTS.md). Follow [ITERATION.md](ITERATION.md)
for scoped baseline/candidate comparisons.

## Frozen selection and configuration

The ten IDs in `experiments/api-diagnostic-10-v1.json` were selected before model
execution with Python `random.Random(42)` from sorted IDs within each repository:
four FastAPI, four Rich, one Requests and one HTTPX. The previously inspected
rich_2725 diagnostic was excluded. This small stratified diagnostic is not an
estimate of hidden-test performance.

The runner uses the official agent compiler, six tools, task orchestration and
verification logic. It copies the submitted configuration into ignored run
storage and explicitly selects the API prototype model. The original submission
and both configured model IDs remain unchanged. Sampling is temperature 0.2,
top-p 0.95 and 16,384 maximum output tokens. The API supports Gemma thinking as
on/off, so the adapter requests `thinking_level=high` rather than the submitted
4,096-token thinking budget. Since October 3, 2026, the local API runner has no
per-task wall-clock limit. It explicitly sets `EvaluationBudget(time_minutes=None)`;
omitting the flat timeout alone would restore the harness's 60-minute default,
and zero would immediately time out. Each task still has 50 tool calls, 80 turns
and a 120-second command timeout. This is an API-only override: the official
submission configuration and already-uploaded archive retain their original
four-minute limit. Historical API runs also retain their original budgets and
results. The account reported a 16,000 input-token-per-minute limit. The adapter uses
countTokens on a conservative serialized request and admits at most 15,500
estimated tokens in a rolling 65-second window. Requests exceeding that ceiling
end the task with an explicit local quota-stop record and retain any existing
patch. Rate-limit waiting is included in measured elapsed time but no longer
triggers a per-task session timeout in the local API runner.

## Runtime

Use the existing WSL Python 3.13 harness environment described in BASELINE.md.
`tools/run_api_baseline.py` loads the explicitly configured Gemini profile using
the central registry. Credentials remain in memory and are not passed to task
commands. The API client runs outside the task sandbox.

Docker is unavailable locally. Task commands use the official SubprocessManager
with an additional bubblewrap wrapper: a separate process/network namespace,
read-only system/Python dependencies, and only the current task's writable files.
Neither the Windows filesystem, registry nor evaluator task/patch data is mounted
inside those commands. This is a local execution adapter, not the official Docker
image or a change to the scoring criterion.

The local bubblewrap binary was extracted from Ubuntu's bubblewrap package into
`~/.local/opt/gemma-bwrap`. The task dependency overlay at
`~/.local/opt/gemma-task-deps` contains Starlette 0.49.3 and Pygments 2.15.1.
The Starlette version satisfies all four sampled FastAPI snapshots; Pygments is
pinned to the rich_3064 lockfile to reproduce its rendering assertions. The
workspace and its `src/` directory precede installed packages in PYTHONPATH.
Additional test dependencies and exact versions are recorded in private run
dependency snapshots. Reference-patch controls are evaluator-only and never
included in model requests.

```sh
~/.venvs/gemma-baseline/bin/python tools/run_api_baseline.py --run-id unique-api-run
python tools/summarize_api_run.py runs/unique-api-run
```

For one task, add `--task-id httpx_3672`; `--submission-dir` selects a baseline or
candidate directory to snapshot. Record the predeclared change with `--hypothesis`
and the comparison run with `--parent-run`. The finalized launcher saves its
source files, exact package versions (including the task dependency overlay),
task-data hashes, submission hashes and Git revision in each private run.
Use `python tools/iteration_report.py runs/unique-api-run --record` after completion
to save the aggregate report and append the experiment ledger idempotently.

The runner deliberately rejects an existing output directory. Download all ten
authorized repository snapshots before invoking it. A fresh clone also needs
the official harness wheels and local registry access; this is not a portable
credential-free CI command.

## Usage and cost accounting

`usage.jsonl` contains provider-returned token counts, latency and sanitized API
errors without prompts or keys. `summary.json` records per-task results.
`evaluation-config.json` records the effective runner limits, with `null` meaning
no per-task wall-clock limit. The frozen selection file also documents the original
four-minute experiment; the runner uses its task IDs, not those historical limits.
Patches,
task traces and detailed test output stay in ignored run directories.

Prompt tokens already include cached prompt tokens; do not add cache counts to
them again. Candidate output and thought tokens are reported separately. Use
the provider's total count for total consumption. Interrupted requests without a
returned usage record are unknown, not zero.

On October 2, 2026, [Google's official pricing table](https://ai.google.dev/gemini-api/docs/pricing#gemma_4)
listed Gemma 4 input and output as free of charge, with no paid tier. Dollar
estimates use those published rates; they are not a verified billing statement.
No paid GPU or alternative provider is provisioned by this experiment.

Early runs `api-ten-20261002-v1` and `v2` were interrupted during the first task:
the initial request cadence hit rate limits, and reference controls then revealed
an incompatible host Starlette version. Retain their recorded usage as setup
overhead rather than silently excluding it from the experiment's total.

## Environment controls

All four FastAPI, all four Rich and the HTTPX task pass the reference-patch
control and fail with an empty patch in the final local environment. Requests
7502 still has four network connect-timeout test failures with the reference
patch (334 tests pass); its model outcome cannot be treated as a clean accuracy
measurement in this isolated local environment. Keep it in the declared ten-task
run and report this limitation instead of replacing it after seeing outcomes.

Run v3 was also interrupted while adding token-aware pacing. Run v4 exposed an
SDK countTokens incompatibility before any generation; the adapter was corrected
to count serialized request text. Run v5 is the final ten-task batch. All earlier
recorded generation usage is retained as setup overhead.
