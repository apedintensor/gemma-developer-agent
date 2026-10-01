# Agent instructions

## Language and collaboration

Use English for shared documentation, code comments, task records, commits, pull requests and cloud task reports. In local conversations, follow the user's requested language, including Chinese. Preserve existing rules when updating this file.

## Browser preference

When X (Twitter) cannot be accessed through direct web tools, use the user's already logged-in Chrome browser to read it. This is a persistent user preference. It does not authorize posting or sending messages. If that browser is unavailable in a cloud task, report the limitation.

## Central AI resources and API configuration

- On the owner's local machine, resolve the central registry through `AI_REGISTRY_ROOT` or ignored `configs/local.json`. Read its README.md, AGENTS.md and API_USAGE.md first, then query registry/resources.json, profile metadata and relevant sources. Do not duplicate downloads, deployments or credentials. Historical working status does not establish current availability.
- Reuse central `api_registry.load_api(service, profile=...)` or tools/api_run.py; never copy the loader. Explicitly match accounts, endpoints and profiles rather than selecting the first entry.
- Keep credentials in memory. Never print or copy secrets into documentation, ordinary JSON, logs or new .env files. Preserve model IDs, protocols, base URLs, parameters and local model paths. Resource/profile IDs are not model IDs; a missing endpoint must not silently select another provider.
- Prefer explicit SDK configuration. Check environment conflicts and dotenv ordering before changing process variables. Import existing credentials only through the central file-import process, never as command-line secret values. Retain old configuration until a switch is verified.
- Submit independent resource changes to the central inbox using UPDATE_TEMPLATE.md, including IDs, service/profile, sources, affected projects and verification scope. Do not overwrite the formal central catalog from an ordinary project task.
- Before deleting or moving resources, read central HOUSEKEEPING.md and check shared dependencies, unique assets and cloud billing. Models, wallets, SSH keys and authorization sessions are outside API migration scope.
- Registry integration authorizes offline checks only, not paid API calls, cloud provisioning, top-ups, generation, model downloads, migration or cleanup.
- Cloud tasks may lack the local registry and its Windows-bound vault. Use the default offline check; do not copy the vault to the cloud or treat its absence as permission to choose another account. Keep personal local configuration ignored by Git.

## Project and experiments

- The official model remains `gemma-4-31b-it-qat-w4a16-ct`. The optional AI Studio prototype uses `gemma-4-31b-it`. Never equate their scores.
- The official harness and sample submission are available in ignored data storage on the owner's machine. Follow docs/BASELINE.md for source versions, validated configuration and evaluator controls; do not invent framework schemas or silently change model IDs. A fresh clone still requires authorized artifact downloads.
- Maintain TASKS.md and follow experiments/README.md. Record model/backend, split, success rate, time and code version. Establish a single-agent baseline before adding complexity.
- Keep competition data, reference fixes, restricted source and private logs out of this public repository. Check redistribution permissions before committing imported assets.
- Setup baseline (2026-10-01): the project started empty. Local Gemini credential loading was verified offline through the central registry; no online authentication, inference, training or official evaluation has been verified.
