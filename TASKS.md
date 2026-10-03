# Roadmap and issue index

GitHub Issues are the source of truth for task status, ownership and acceptance criteria. This file links the milestones; do not maintain a second detailed checklist here.

See [docs/PLAN.md](docs/PLAN.md) for the evidence-based execution plan.

October 4, 2026: the owner selected paid OpenRouter for local development.
The model/tool adapter, explicit central profile, pinned provider and response
cost accounting are implemented. Authentication and the synthetic tool-result
roundtrip pass. One unchanged-prompt `httpx_3672` run then resolved the task:
24 tests passed, 713.6 seconds, US$0.11580450 response-reported cost. Its largest
input (32,936 tokens) exceeds the official total context window, so the
official-model milestone remains separate. See
[OpenRouter setup and verification](docs/OPENROUTER.md).

October 3, 2026: removed the local API diagnostic's four-minute session limit and
completed one `httpx_3672` run: no patch before the local input-quota guard stopped
generation. The repeatable workflow, run snapshots, comparison tool and ledger
recording are ready. See [the result](docs/ITERATION_RESULTS.md) and
[iteration protocol](docs/ITERATION.md). Next development experiment: focused
reads to reduce context growth; official-model milestone #3 remains open.

| Order | Milestone | Issue | Dependency |
|---|---|---|---|
| 0 | Portable checks and cross-platform CI | [#1](https://github.com/apedintensor/gemma-developer-agent/issues/1) | None |
| 1 | Official harness and runtime requirements | [#2](https://github.com/apedintensor/gemma-developer-agent/issues/2) | Access obtained; see docs/BASELINE.md |
| 2 | One official task end to end | [#3](https://github.com/apedintensor/gemma-developer-agent/issues/3) | #2; working runtime and compute |
| 3 | Frozen validation split and baseline | [#4](https://github.com/apedintensor/gemma-developer-agent/issues/4) | #3 |
| 4 | Workflow experiments and LoRA decision | [#5](https://github.com/apedintensor/gemma-developer-agent/issues/5) | #4 |

Assign one owner per issue once the collaborator is identified. Keep shared discussion in English; use separate branches and linked pull requests. Use the [Project board](https://github.com/users/apedintensor/projects/1) for Todo, In Progress, In Review and Done. Issues retain acceptance criteria and discussion.
