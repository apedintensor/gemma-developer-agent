# Roadmap and issue index

GitHub Issues are the source of truth for task status, ownership and acceptance criteria. This file links the milestones; do not maintain a second detailed checklist here.

See [docs/PLAN.md](docs/PLAN.md) for the evidence-based execution plan.

| Order | Milestone | Issue | Dependency |
|---|---|---|---|
| 0 | Portable checks and cross-platform CI | [#1](https://github.com/apedintensor/gemma-developer-agent/issues/1) | None |
| 1 | Official harness and runtime requirements | [#2](https://github.com/apedintensor/gemma-developer-agent/issues/2) | Access obtained; see docs/BASELINE.md |
| 2 | One official task end to end | [#3](https://github.com/apedintensor/gemma-developer-agent/issues/3) | #2; working runtime and compute |
| 3 | Frozen validation split and baseline | [#4](https://github.com/apedintensor/gemma-developer-agent/issues/4) | #3 |
| 4 | Workflow experiments and LoRA decision | [#5](https://github.com/apedintensor/gemma-developer-agent/issues/5) | #4 |

Assign one owner per issue once the collaborator is identified. Keep shared discussion in English; use separate branches and linked pull requests. Use the [Project board](https://github.com/users/apedintensor/projects/1) for Todo, In Progress, In Review and Done. Issues retain acceptance criteria and discussion.
