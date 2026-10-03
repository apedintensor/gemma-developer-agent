# OpenRouter prototype

The user-selected default API backend is `openrouter`, with exact model ID
`google/gemma-4-31b-it`, base URL `https://openrouter.ai/api/v1`, and the
OpenAI Chat Completions protocol. The existing AI Studio `prototype` object is
preserved in `configs/project.json`; select it explicitly with `--backend ai_studio`.
The official competition model remains `gemma-4-31b-it-qat-w4a16-ct`.

## Provider and limits

The route is pinned to `deepinfra/fp8` with provider fallback disabled. Reasoning
is enabled using provider defaults; the submission's numeric 4,096-token thinking
budget is not enforced by this API adapter. Its effective reasoning settings are
recorded in each manifest. On October 4, 2026, [OpenRouter's endpoint metadata](https://openrouter.ai/api/v1/models/google/gemma-4-31b-it/endpoints)
listed tool support, a 262,144-token context, a 16,384-token output maximum, and
prices of US$0.15 per million input tokens and US$0.40 per million output tokens
for this route. These are published route prices, not a billing statement or
guarantee of current availability. Record returned usage and cost information
for each live run; leave unknown actual charges blank.

The AI Studio adapter's 16,000-input-token-per-minute account limit and local
15,500-token guard do not apply to OpenRouter. OpenRouter may impose its own
limits. The local runner retains no per-task wall-clock limit, 50 tool calls,
80 turns and a 120-second command timeout. It does not yet enforce the official
32,768-token context cap. Different model serving, quantization, context and
local sandbox conditions mean this is a prototype result, not a competition
score or an interchangeable AI Studio baseline.

## Configuration and checks

Keep the central registry path and explicit `openrouter_profile` in ignored
`configs/local.json`. The existing `profile` key still selects AI Studio.
`AI_REGISTRY_ROOT` and `AI_REGISTRY_PROFILE` are explicit environment overrides;
the selected profile must match the selected service and exact endpoint. Do not
copy keys into project files, commands, notebooks or logs. The central loader
supplies credentials in memory, and no provider is silently substituted.

Portable checks do not require the local registry or make network requests:

```sh
python tools/check_setup.py
python tools/check_setup.py --backend ai_studio
```

On the owner's machine, validate central metadata and optionally load the
credential offline:

```sh
python tools/check_setup.py --backend openrouter --check-registry
python tools/check_setup.py --backend openrouter --check-credentials
```

An offline check does not verify authentication, credit or model inference.
On October 4, authenticated account lookup succeeded and a two-request synthetic
tool roundtrip passed through the exact adapter: 345 total tokens and US$0.00007875
reported cost, both responses served by DeepInfra. Private evidence is in
`runs/openrouter-setup-20261004-v2/`. The first setup attempt had one successful
response (US$0.00004855) followed by a 404 for disabled tool choice; a separate
minimal probe confirmed that parameter incompatibility. The adapter now omits
tool declarations when tools are disabled while preserving complete prior tool
history and reasoning state. This does not change normal agent AUTO tool mode.
A public metadata lookup alone verifies only the published route description.

## First complete task result

Run `or-iter-001-httpx3672-20261004` used the unchanged baseline prompt on
the existing development task `httpx_3672`. The local official verifier resolved
the task with exit code 0 and 24 tests passing. It took 713.592 seconds, 34 model
responses and 32 tool calls, with no API errors or quota stops.

| Recorded metric | Value |
|---|---:|
| Input tokens | 743,782 |
| Visible output tokens | 4,244 |
| Reasoning tokens | 6,349 |
| Total tokens | 754,375 |
| Cached input tokens | 0 |
| Response-reported task cost | US$0.11580450 |
| Task plus successful setup-response costs | US$0.11593180 |
| Largest single input | 32,936 tokens |

All task responses identify DeepInfra and `google/gemma-4-31b-it`. Costs are
recorded provider metadata, not a reconciled invoice; rejected setup requests
did not return usage/cost metadata. Full raw traces and the generated patch stay
in ignored `runs/`; the public ledger contains only aggregate metrics.

The largest input alone exceeded the competition's 32,768-token total context
window. This result therefore does not establish feasibility under official
context limits, official-model accuracy, or generalization beyond one development
task. No prompt change or training produced this result. A later experiment
should enforce/compact to a declared context budget before making competition
claims. The generated patch also retained a scratch reproduction script; note
that cleanup issue for a separate prompt experiment, without altering this result.

The run froze source revision `2c4bb0d814cc4ce1d81601ae9f32c91b6ea035f6`
with a working-tree marker and exact source/artifact hashes in its manifest.
The initial SDK model clone emitted a nonfatal destructor warning while the
compiler fell back to a shallow copy. An offline check confirmed shared metering
and transport. A subsequent explicit copy implementation removes that warning;
its 13 adapter tests pass, including the real official compiler with a fake key.
The frozen run source was preserved. The adapter hash now differs, so do not
silently attribute a future comparison to prompt changes alone.

## Run one task

Use the existing WSL harness environment and local prerequisites described in
[API_BASELINE.md](API_BASELINE.md): authorized official task/snapshot artifacts,
the central registry, dependencies and the isolated task-command wrapper.
From the project root in WSL:

```sh
~/.venvs/gemma-baseline/bin/python tools/run_api_baseline.py --backend openrouter --task-id httpx_3672 --run-id UNIQUE
python tools/iteration_report.py runs/UNIQUE --record
```

Choose a new run ID each time. Paid inference belongs within the user's declared
task scope and usage/spending limits; setup alone does not authorize it. Preserve
run snapshots, backend, provider route, effective configuration and token/cost
records. Follow [ITERATION.md](ITERATION.md) to compare changes within the same
backend and frozen conditions before testing broader improvements.
