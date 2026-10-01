# Baseline execution and collaboration plan

Checkpoint: October 2, 2026 (Australia/Sydney).

## Objective and definition of success

The first research milestone is one real public development task completed through the official harness: prepare the repository, run the required model, generate a patch and record the evaluator result. A setup check, API response or mock test alone does not meet this milestone. After that, establish a reproducible baseline on a fixed validation split before optimizing or training.

## Verified starting point

| Area | Evidence | Status |
|---|---|---|
| Repository | Public GitHub repository; local main matched origin/main at the start of this work | Ready |
| Portable setup | Python 3.12 standard-library configuration check passes | Ready |
| Local credential integration | Selected Gemini profile loads from the central registry offline; endpoint matches | Offline only; provider access unverified |
| Cloud setup | Earlier user screenshot showed Python 3.12.14 and a successful offline check | No official harness or API verification |
| Kaggle access | Data page still shows Sign In and asks for competition-rule acceptance | Blocked for this browser session |
| Docker | CLI installed; engine request fails because the Linux engine pipe is unavailable | Not running/reachable |
| WSL | Ubuntu and docker-desktop distributions listed | Presence only, not a working harness |
| GitHub project board | Owner completed Projects authorization; public board created and linked to this repository | [Available](https://github.com/users/apedintensor/projects/1) |

## Stage 0: reliable development loop

Deliver portable setup checks and isolated tests on Windows and Linux via GitHub Actions. Use no real credentials in CI. Each substantive change should have a linked issue, branch, test evidence and pull request.

This stage verifies our tooling, not the model or competition score.

## Stage 1: unlock and inspect the official harness

Owner: project owner for account/rule acceptance; either contributor for technical review.

1. The owner signs in to Kaggle and accepts the competition rules personally.
2. Obtain HARNESS_README.md and the minimum official sample files into ignored local data storage. Avoid downloading the complete 22.42 GB dataset until required files are identified.
3. Record versions/checksums and inspect the real agent.yaml schema, library versions, model-loading method, tools, inference interface, context compaction, LoRA requirements and evaluator commands.
4. Separate the host Python requirement from the sandbox Python version. The public dataset description mentions Python 3.13 in the sandbox; our Python 3.12 scaffold is not a substitute for that environment.
5. Document redistribution permissions before committing imported code or data. Confirm team membership and code-sharing requirements for both collaborators.

Acceptance: a cited environment/runbook document with exact commands and remaining unknowns. No guessed framework schema or dependencies.

## Stage 2: run one official task

Depends on Stage 1.

1. Choose a supported Linux/Docker execution host and make the Docker engine reachable. Confirm hardware and storage against the harness requirements before any model download or rental.
2. Decide whether available local/Kaggle compute is sufficient or a GPU rental is necessary; obtain a concrete budget before provisioning.
3. Use the official sample and required `gemma-4-31b-it-qat-w4a16-ct` without fine-tuning.
4. Run one task with a bounded timeout and record setup, generation and validation separately.
5. Save the patch, evaluator exit status, relevant test results, exact model/config versions and timings in ignored run artifacts. Report the actual outcome even if the issue remains unsolved.

Acceptance: the complete task pipeline executes reproducibly. A failed patch is a valid diagnostic run, but is not a solved task. An API prototype is not official-harness validation.

## Stage 3: establish a trustworthy baseline

Depends on Stage 2.

- Freeze split IDs before prompt tuning. Group duplicate base commits and closely related tasks to reduce leakage; consider repository-held-out evaluation when practical.
- Begin with a small diagnostic subset spanning repositories, then expand to the full agreed validation split.
- Keep reference fixes and evaluation tests outside the agent's accessible inputs.
- Record attempted and solved counts, success rate, total/per-task time, tool calls, failures and costs where known. Preserve timeouts and no-patch cases in the denominator.
- Classify failures: localization, understanding, patch quality, tool/format errors, dependency/environment problems, timeout.

Acceptance: reproducible baseline report and an explicit prioritized failure list. No invented score targets before observing the baseline.

## Stage 4: improve the agent, then decide on training

Compare one major change at a time: code search vs graph-assisted retrieval, targeted testing and repair loops, context management, and time allocation. Repeat promising changes on the held-out split.

Use failure evidence to decide whether LoRA/SFT is justified. Reference patches alone are not full agent trajectories; training data should reflect tool observations and repair actions where appropriate. Estimate data generation, training and evaluation costs before spending. Consider RL and multiple agents only after simpler changes have measurable results.

Acceptance: a controlled comparison with held-out evidence, runtime/cost tradeoffs and reproducible configs.

## GitHub workflow for two contributors

- GitHub Issues are the source of truth for execution status; TASKS.md is a roadmap/index, not a duplicate detailed board.
- Each issue has one accountable owner, acceptance criteria and dependencies. The collaborator's identity is not yet known; do not assign work to a guessed account.
- Use `task/<issue-number>-<short-name>` branches and link PRs with `Closes #N`.
- Work states: unstarted open issue -> assigned/active branch -> PR under review -> merged/closed. Use the [Project board](https://github.com/users/apedintensor/projects/1); no additional management platform is needed.
- Shared text is English. Local explanations to the owner may be Chinese.
- Do not ask a cloud task and a local task to modify the same files concurrently without coordinating branches.

## Local, cloud and GPU responsibilities

Local: Kaggle browser/account work, central registry, credentials and initial harness access.

Codex Cloud: self-contained coding, documentation and fake-data tests through branches/PRs. It is optional, and no cloud task has been dispatched by this plan.

GPU host: actual inference/training once requirements and budget are established. Codex Cloud setup does not establish that suitable GPU compute is available.

## Optional AI Studio prototype

Use `gemma-4-31b-it` to explore prompts/tool interactions only when useful. Establish account access, quotas, supported tool interface and authorization before live calls. Keep its scores separate; do not delay the official baseline merely to build an alternative framework.

## Next decision

The immediate dependency is official file access, not a choice of training algorithm or project-management vendor. Once the harness is available, finalize the runtime and compute plan. No credible training budget or completion date can be promised before those requirements are known.

## Sources

- [Official data and harness description](https://www.kaggle.com/competitions/gemma-4-developer-agent/data), rechecked October 2, 2026.
- [Competition overview](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview).
- [Competition rules](https://www.kaggle.com/competitions/gemma-4-developer-agent/rules).
