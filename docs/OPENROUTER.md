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
