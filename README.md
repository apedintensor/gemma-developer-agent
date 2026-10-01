# Gemma Developer Agent

A research workspace for the Kaggle Gemma 4 Developer Agent competition. Build a reproducible baseline, improve repository navigation and test-driven repair, then evaluate whether fine-tuning helps.

**Status:** project scaffolding only. The official harness, dataset and sample submission have not been imported. No online inference, training or competition submission has been run.

Continuing in a new local or cloud session? Read [HANDOFF.md](HANDOFF.md) for current context, verification limits and suggested next steps.

## Quick start

Python 3.12 is sufficient for the current standard-library-only tools:

```sh
python tools/check_setup.py
python -m unittest discover -s tests -v
```

This offline check works in a fresh clone and in Codex Cloud. It does not require API keys, a local registry or downloaded models.

The tests use isolated temporary fixtures and fake credentials. GitHub Actions runs the checks on Ubuntu and Windows with Python 3.12 for pull requests and main-branch pushes.

## Codex Cloud setup

1. Select this GitHub repository when creating an environment.
2. Ask for Python 3.12 and run `python tools/check_setup.py`.
3. No dependency installation, API credentials or service startup is currently required.
4. Publish the environment after the check succeeds.

Suggested setup prompt:

> Set up this repository with Python 3.12. Read AGENTS.md and README.md. Run python tools/check_setup.py. Do not download models, create GPU instances, call inference APIs or fabricate an official submission configuration. Report in English.

## Models

- Official competition model: `gemma-4-31b-it-qat-w4a16-ct`.
- Optional AI Studio prototype model: `gemma-4-31b-it` using the Gemini API.
- These backends are separate; prototype results are not official benchmark results.
- GPU providers are not provisioned by this repository.

## Local central registry integration

Existing local credentials remain in the central encrypted registry. Do not copy them into this repository. Create an ignored `configs/local.json` containing only `registry_windows`, `registry_wsl` and an explicitly matched `profile`, or set `AI_REGISTRY_ROOT` and `AI_REGISTRY_PROFILE`.

```sh
python tools/check_setup.py --check-registry
python tools/check_setup.py --check-credentials
```

The second command also loads the selected credential in memory, without making network requests. Windows DPAPI credentials are not portable to Codex Cloud. Cloud coding and offline checks need no credentials; any future cloud API integration must use separately authorized cloud secret configuration.

## Working together

[Project board](https://github.com/users/apedintensor/projects/1) — Todo, In Progress, In Review, Done.

Use English for shared documentation, code comments, tasks, commits and pull requests. Local conversations may use the user's preferred language. Work on separate branches and review pull requests before merging.

- `TASKS.md`: task board and acceptance criteria.
- `docs/PLAN.md`: execution stages, blockers and collaboration workflow; GitHub Issues #1-#5 track status and acceptance criteria.
- `experiments/`: experiment protocol and results table.
- `configs/project.json`: public model and endpoint configuration.
- `submission/`: official harness integration placeholder, not a valid submission.
- `data/`, `models/`, `adapters/`, `runs/`: ignored local artifacts. Reuse existing registered assets where possible.

Do not publish restricted competition data, reference solutions, credentials or private repository contents here.

## Next milestone

Obtain `HARNESS_README.md` and `sample_submission/` through Kaggle after accepting the competition rules. Confirm the actual schema, hardware, dependencies and redistribution terms before integrating files. Run one public development task, then establish a fixed validation split and baseline.

## Sources

- [Competition](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview)
- [Data and harness](https://www.kaggle.com/competitions/gemma-4-developer-agent/data)
- [Rules](https://www.kaggle.com/competitions/gemma-4-developer-agent/rules)
- [Gemma on Gemini API](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api)

Competition details were reviewed on October 1, 2026; recheck before submitting.
