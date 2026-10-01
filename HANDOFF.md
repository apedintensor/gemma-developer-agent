# Session handoff

Last updated: October 2, 2026 (Australia/Sydney). This is a historical checkpoint; inspect current files and Git state before making changes.

## October 2 checkpoint

The portable checks and local credential loading pass. Nine isolated tests were added using fake registry fixtures, along with GitHub Actions for Ubuntu/Windows. See the current CI run for remote status. GitHub Issues #1-#5 now hold execution status and docs/PLAN.md contains the implementation plan.

The Kaggle browser remains signed out with files gated by competition-rule acceptance. Docker CLI is installed but the Linux engine is unreachable. The owner subsequently completed Projects authorization. The public [Project board](https://github.com/users/apedintensor/projects/1) is linked to the repository with Todo, In Progress, In Review and Done states. The first-cloud-task suggestion below is historical: tests are now implemented, so do not duplicate that assignment. No live model request, official task or training run has occurred.

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
- Official submissions use an ADK-based configuration package with agent.yaml at the archive root. LoRA is optional. Do not invent the full schema before obtaining the official sample.
- Strategy: establish a single-agent baseline, inspect failures, improve retrieval/test feedback/time allocation, then decide whether SFT/LoRA or RL is justified.

## What has actually been completed

- Local Git initialized; a public GitHub repository created and the initial project pushed.
- English README, AGENTS instructions, task board, experiment protocol and empty results table.
- Public configs/project.json records the two model IDs and Gemini protocol/endpoint, without credentials or account profile IDs.
- Default tools/check_setup.py validates public configuration offline using the Python standard library. Verified from a clean temporary copy without local configuration.
- Optional --check-registry and --check-credentials reuse the existing central loader on the owner's machine. The selected local Gemini profile loaded successfully in memory; no API request was made.
- Owner-specific registry paths and explicit profile selection remain in ignored configs/local.json. Do not print, publish or overwrite them unnecessarily.
- No model downloads, GPU provisioning, inference, training or Kaggle submission have occurred.

## Cloud environment evidence and limits

The user supplied a setup screenshot showing Python 3.12.14 installed and `python tools/check_setup.py` passing. Repository files were unchanged; no credentials, models or GPUs were configured. The screenshot showed "Publishing" in progress. Publication completion, environment name/ID and collaborator access have not been independently verified.

An environment is a reusable prepared setup: selected repositories, tools, dependencies and access configuration. A new cloud task uses its own workspace based on the published setup. Continuing an existing task keeps that task's state. Publishing an environment update does not automatically replace existing tasks' state.

Local and cloud do not share the same folder. The local central registry and Windows-bound encrypted credential vault are not automatically available in cloud tasks. The project currently has no cloud API credential adapter or online agent implementation. A passing offline check does not establish provider access or official harness readiness.

## Why use Cloud for this project?

Cloud is optional. Its likely value here is independent coding work that can continue without the local computer, a repeatable setup for a collaborator, and reviewing isolated changes through GitHub. It adds repository synchronization and separate credential configuration.

| Work | Suggested location | Reason |
|---|---|---|
| Planning with the owner, local files and central registry | Local | Existing context, files and credentials are available |
| Self-contained code changes, documentation and offline tests | Cloud or local | Cloud can work independently and produce reviewable changes |
| API experiments | Local initially | Central credentials already load locally; account access still needs verification |
| Gemma inference/fine-tuning requiring GPUs | A separately selected GPU environment | No suitable GPU resource has been provisioned or verified here |

Do not migrate everything merely because a cloud environment exists. A sensible first comparison is one small cloud coding task, reviewed locally. If it adds little value, continue local development.

## Suggested first cloud task

This is a future suggestion, not an instruction to dispatch another task without user authorization:

> Read AGENTS.md, README.md and HANDOFF.md. Add standard-library unit tests for tools/check_setup.py covering a fresh clone without local configuration and rejection of unexpected model IDs or endpoints. Use temporary fixtures and fake registry metadata only; do not load real credentials or access the network. Keep production model IDs unchanged. Run the tests, document the command and prepare a focused pull request. Report in English.

Use a separate branch. Avoid concurrently changing the same files locally. Review the diff and checks before merging. A new session should verify that its checkout contains this handoff; an older cloud task may need an explicit repository update. Preserve uncommitted work when synchronizing.

## Collaboration workflow

Use GitHub as the shared code/history source. The collaborator needs write access to push branches, or can propose changes via a fork. Environment sharing is separate from repository permissions and does not mean shared task files or chat history. Confirm actual account/workspace capabilities before promising a shared environment.

Typical cycle: local commit/push -> cloud task on a branch -> review/merge PR -> local pull. Git changes do not automatically synchronize unsaved local files, conversations, ignored artifacts or credentials. Keep personal credentials separate; any future cloud credential setup must be explicitly scoped and must not expose secrets in this public repository.

## Next competition milestone and blockers

1. Obtain the official HARNESS_README.md and sample_submission through Kaggle after the user accepts the competition rules. Prior browsing could read the public description but not gated files. Do not claim the rules have been accepted.
2. Check hardware, dependencies, context and time budgets, tools, LoRA compatibility, and redistribution permissions.
3. Build the documented environment and run one public development task end to end.
4. Fix development/validation splits and record the first official-harness baseline before adding complexity.

The competition overview previously reported 129 public development tasks, about 120 hidden tasks, a 12-hour total patch-generation budget, one submission per day and up to five team members. These are dated research notes; recheck official rules before relying on them. Collaboration must comply with competition team/sharing rules. Keep restricted tasks, reference fixes and private code out of this public repository; check permissions before importing official materials.

## Local resources and permissions

On the owner's machine, locate the registry via ignored configs/local.json or AI_REGISTRY_ROOT and follow its API_USAGE.md. Targon and Lium have centrally registered credentials and historical resource-management evidence, but no resources were provisioned for this project. Gemini has a selected local profile with offline loading verified only. Do not infer current authentication, balance or model access from those records.

The user authorized creation and publication of this project repository. This is not blanket authorization for paid API calls, renting GPUs, uploading competition data, sharing credentials or accepting agreements. No automatic task monitor or background research job has been configured.

## Useful references

- [Codex Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments)
- [Competition overview](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview)
- [Competition data](https://www.kaggle.com/competitions/gemma-4-developer-agent/data)
- [Competition rules](https://www.kaggle.com/competitions/gemma-4-developer-agent/rules)
- [Gemma on Gemini API](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api)
