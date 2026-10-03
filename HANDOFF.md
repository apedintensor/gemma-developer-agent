# Session handoff

Last updated: October 4, 2026 (Australia/Sydney). This is a historical checkpoint; inspect current files and Git state before making changes.

## October 4 OpenRouter switch

At the owner's explicit request, new local API runs now default to OpenRouter
`google/gemma-4-31b-it`, pinned to `deepinfra/fp8` with provider fallback and
SDK/harness error retries disabled. The distinct user-supplied profile was
imported through the central encrypted credential workflow from this chat's
existing authorized message, without a plaintext key file. The private local
`openrouter_profile` selects it; the old AI Studio `profile` is retained.

Authentication and a two-request tool-result roundtrip passed; see
[docs/OPENROUTER.md](docs/OPENROUTER.md). This route has no AI Studio TPM pacing.
Its published context is 262144 tokens, but no local competition-equivalent
32768-token cap is enforced yet. Numeric thinking_budget=4096 is not enforced;
reasoning is enabled using provider defaults. Official submission files remain
unchanged. Select `--backend ai_studio` to reproduce the earlier backend.

One unchanged-prompt `httpx_3672` baseline completed under
`or-iter-001-httpx3672-20261004`: resolved, verifier exit 0, 24 tests passed,
713.592 seconds, 34 model responses, 32 tool calls, 754375 tokens and
US$0.11580450 response-reported cost. There were no API errors. Its largest input
was 32936 tokens, exceeding the official total context window. An explicit
SDK-copy fix was made after the run's source snapshot; preserve its original
manifest and account for the adapter hash difference in future comparisons.
The report and ledger row are recorded; no evaluation process remains active.
Do not compare across backends as a prompt improvement. No ten-task batch,
indefinite iteration loop or additional Kaggle submission was requested.

## October 3 configuration update

The owner then requested one task and a reusable iteration process. Run
`api-iter-001-httpx3672-20261003` is complete: 0/1 resolved, no patch, 322.7 seconds,
56,436 recorded tokens and seven real generation responses. The local adapter
stopped when its conservative input estimate reached 16,501 tokens, above its
15,500-token quota guard. There were no provider errors; 210.3 recorded seconds
were pacing waits. This is an operational stop, not a failed candidate patch.
See docs/ITERATION_RESULTS.md, docs/ITERATION.md and tools/iteration_report.py.
The run source and submission are frozen privately; subsequent automatic
fingerprint collection changed the launcher hash but not inference behavior.
Preserve the original hash and review this difference before comparisons. No
second experiment or additional Kaggle submission was started.

At the owner's request, the local API runner now uses an explicit
`EvaluationBudget(time_minutes=None)` to remove its four-minute per-task session
limit. The 50-tool-call, 80-turn and 120-second command limits remain. Future runs
write their effective limits to `evaluation-config.json`. Historical results and
the official submission configuration remain unchanged. The timeout edit itself
started no inference; the authorized one-task follow-up is described above.

## Latest API checkpoint

The owner authorized running ten public tasks through the Gemma API to measure cost. Final run `api-ten-20261002-v5` completed: 71 generation responses, 386,983 recorded tokens, 41.5 minutes summed task wall time, 0/10 resolved. All ten reached the four-minute agent timeout. Including setup attempts and probes, recorded usage totals 503,701 tokens. Google listed Gemma 4 input/output free of charge; the US$0 estimate is not a verified billing statement.

The account returned a 16,000 input-token/minute limit. Token-aware pacing avoided 429 in the final batch, but waiting counted against task time. Nine reference controls pass; Requests 7502 retains four network-timeout failures. A /tmp write_file instruction mismatch and sparse rich_3105 task description were also observed. See docs/API_RESULTS.md and docs/API_BASELINE.md before interpreting the result or rerunning. Do not repeat the ten-task batch without a new request.

Gemini credentials were loaded from the central registry in memory; live text generation, native function-call responses and usage metadata were verified for gemma-4-31b-it only. No GPU was rented, no model weights were downloaded, and the official quantized-model submission/configuration was not changed. The local task commands use bubblewrap isolation with pinned task dependency overlays. Exact runtime snapshots, task assets and logs remain ignored. PR #8 is stacked on PR #7.

## Earlier October 2 checkpoint

The portable checks and local credential loading pass. Nine isolated tests were added using fake registry fixtures, along with GitHub Actions for Ubuntu/Windows. See the current CI run for remote status. GitHub Issues #1-#5 now hold execution status and docs/PLAN.md contains the implementation plan.

The owner joined the competition and authorized one official Kaggle evaluation. Submission **56753224** was accepted at 2026-10-01 14:45:14 UTC; the latest check remains PENDING with no score. Poll this ID before considering another upload. See [docs/BASELINE.md](docs/BASELINE.md) for the archive hash, exact runtime, evaluator controls and reproduction commands.

The official harness is installed in WSL Ubuntu at `~/.venvs/gemma-baseline` (Python 3.13.15). On rich_2725, the empty-patch control produced 15 passing and 4 failing tests; the reference-patch control passed all 19. These are evaluator checks, not model performance. No local inference, model download or GPU rental occurred. Docker's Linux engine remains unavailable. Official artifacts and private logs are ignored by Git.

The public [Project board](https://github.com/users/apedintensor/projects/1) is linked to the repository. Nine isolated portable tests and Ubuntu/Windows CI already exist; do not duplicate that assignment.

## Start here

Read AGENTS.md, README.md and TASKS.md, then run:

```sh
git status --short
python tools/check_setup.py
```

The user wants a practical competition project and is learning how Codex local and cloud tasks fit together. Explain concepts plainly. Speak Chinese in the owner's local chat; write shared artifacts and cloud reports in English. There is a second collaborator, but their GitHub identity and access have not been configured by this session.

## Project identity and objective

- Public repository: https://github.com/apedintensor/gemma-developer-agent
- Initial scaffolding commit: `201d41f` on `main`.
- Competition: https://www.kaggle.com/competitions/gemma-4-developer-agent
- Build an agent that navigates Python repositories, fixes issues and submits patches verified by tests.
- Official required model: `gemma-4-31b-it-qat-w4a16-ct`.
- Optional Gemini API prototype model: `gemma-4-31b-it`. Preserve both exact IDs and distinguish their results.
- Official submissions use an ADK-based configuration package with agent.yaml at the archive root. LoRA is optional. The authored single-agent package has passed the official compiler; see submission/.
- Strategy: establish a single-agent baseline, inspect failures, improve retrieval/test feedback/time allocation, then decide whether SFT/LoRA or RL is justified.

## What has actually been completed

- Local Git initialized; a public GitHub repository created and the initial project pushed.
- English README, AGENTS instructions, task board, experiment protocol and empty results table.
- Public configs/project.json records the two model IDs and Gemini protocol/endpoint, without credentials or account profile IDs.
- Default tools/check_setup.py validates public configuration offline using the Python standard library. Verified from a clean temporary copy without local configuration.
- Optional --check-registry and --check-credentials reuse the existing central loader on the owner's machine. The selected local Gemini profile loaded successfully in memory; no API request was made.
- Owner-specific registry paths and explicit profile selection remain in ignored configs/local.json. Do not print, publish or overwrite them unnecessarily.
- An authored single-agent package compiled successfully and was submitted to Kaggle; model evaluation remains pending. No local inference, model weights download, GPU provisioning or training occurred.

## Cloud environment evidence and limits

The user supplied a setup screenshot showing Python 3.12.14 installed and `python tools/check_setup.py` passing. Repository files were unchanged; no credentials, models or GPUs were configured. The screenshot showed "Publishing" in progress. Publication completion, environment name/ID and collaborator access have not been independently verified.

An environment is a reusable prepared setup: selected repositories, tools, dependencies and access configuration. A new cloud task uses its own workspace based on the published setup. Continuing an existing task keeps that task's state. Publishing an environment update does not automatically replace existing tasks' state.

Local and cloud do not share the same folder. The local central registry and Windows-bound encrypted credential vault are not automatically available in cloud tasks. The project currently has no cloud API credential adapter; local GPU model inference has not been verified. The separate local API diagnostic above uses remotely hosted Gemma. A passing offline check does not establish provider access or official harness readiness.

## Why use Cloud for this project?

Cloud is optional. Its likely value here is independent coding work that can continue without the local computer, a repeatable setup for a collaborator, and reviewing isolated changes through GitHub. It adds repository synchronization and separate credential configuration.

| Work | Suggested location | Reason |
|---|---|---|
| Planning with the owner, local files and central registry | Local | Existing context, files and credentials are available |
| Self-contained code changes, documentation and offline tests | Cloud or local | Cloud can work independently and produce reviewable changes |
| API experiments | Local initially | Gemma API generation verified for the selected profile; other provider access remains unverified |
| Gemma inference/fine-tuning requiring GPUs | A separately selected GPU environment | No suitable GPU resource has been provisioned or verified here |

Do not migrate everything merely because a cloud environment exists. A sensible first comparison is one small cloud coding task, reviewed locally. If it adds little value, continue local development.

## Possible future cloud work

Portable setup tests are already implemented. Choose a small issue from TASKS.md before dispatching additional work, and use a separate branch. A new session should inspect current Git state and avoid duplicating local changes. No cloud task was dispatched for this baseline.

## Collaboration workflow

Use GitHub as the shared code/history source. The collaborator needs write access to push branches, or can propose changes via a fork. Environment sharing is separate from repository permissions and does not mean shared task files or chat history. Confirm actual account/workspace capabilities before promising a shared environment.

Typical cycle: local commit/push -> cloud task on a branch -> review/merge PR -> local pull. Git changes do not automatically synchronize unsaved local files, conversations, ignored artifacts or credentials. Keep personal credentials separate; any future cloud credential setup must be explicitly scoped and must not expose secrets in this public repository.

## Next competition milestone and blockers

1. Check Kaggle submission 56753224 for its actual terminal result and score.
2. Inspect available error/score evidence before changing the baseline.
3. For detailed public-task agent trajectories, obtain suitable compute with a concrete budget before rental; the existing local GPU cannot run the official serving configuration unchanged.
4. Freeze development/validation splits before tuning prompts or training. The rich_2725 reference-patch control is not held-out evidence.

The competition overview previously reported 129 public development tasks, about 120 hidden tasks, a 12-hour total patch-generation budget, one submission per day and up to five team members. These are dated research notes; recheck official rules before relying on them. Collaboration must comply with competition team/sharing rules. Keep restricted tasks, reference fixes and private code out of this public repository; check permissions before importing official materials.

## Local resources and permissions

On the owner's machine, locate the registry via ignored configs/local.json or AI_REGISTRY_ROOT and follow its API_USAGE.md. Targon and Lium have centrally registered credentials and historical resource-management evidence, but no resources were provisioned for this project. Gemini has a selected local profile with live Gemma API generation verified; see the latest checkpoint above. Do not infer current authentication, balance or model access from those records.

The user authorized creation and publication of this project repository. This is not blanket authorization for paid API calls, renting GPUs, uploading competition data, sharing credentials or accepting agreements. No automatic task monitor or background research job has been configured.

## Useful references

- [Codex Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments)
- [Competition overview](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview)
- [Competition data](https://www.kaggle.com/competitions/gemma-4-developer-agent/data)
- [Competition rules](https://www.kaggle.com/competitions/gemma-4-developer-agent/rules)
- [Gemma on Gemini API](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api)
