# Gemma API ten-task result

Run: `api-ten-20261002-v5`; October 2, 2026 (Australia/Sydney).

The ten-task API diagnostic completed with **0/10 resolved** and **41.5 minutes** summed task wall time. This uses `gemma-4-31b-it`, not the quantized competition model. It is not a Kaggle score.

## Cost and usage

**Published-rate estimate: US$0.** Google listed Gemma 4 input/output as free of charge on the run date. This is not a verified billing statement; local electricity is excluded.

| Scope | Input tokens | Candidate output | Thinking tokens | Total tokens |
|---|---:|---:|---:|---:|
| Final ten-task batch | 376,288 | 3,323 | 7,372 | 386,983 |
| Setup and probes | 113,662 | 1,627 | 1,429 | 116,718 |
| All recorded usage | 489,950 | 4,950 | 8,801 | 503,701 |

The final batch returned 71 generation responses with usage records and recorded 0 API/quota error events. Cached tokens are included in input counts, not added again. Interrupted requests without returned metadata may be missing; these totals are recorded usage rather than a complete provider billing ledger.

## Per-task outcome

| Task | Resolved | Wall seconds | Tool calls | Patch bytes | Outcome note |
|---|---|---:|---:|---:|---|
| fastapi_14266 | False | 244.3 | 7 | 0 | Agent exceeded session timeout (4 min) |
| fastapi_13207 | False | 248.6 | 5 | 615 | Agent exceeded session timeout (4 min) |
| fastapi_14487 | False | 243.8 | 9 | 0 | Agent exceeded session timeout (4 min) |
| fastapi_14463 | False | 248.9 | 5 | 1143 | Agent exceeded session timeout (4 min) |
| rich_3468 | False | 243.0 | 8 | 0 | Agent exceeded session timeout (4 min) |
| rich_3105 | False | 243.2 | 6 | 0 | Agent exceeded session timeout (4 min) |
| rich_3064 | False | 246.8 | 8 | 403 | Agent exceeded session timeout (4 min) |
| rich_4075 | False | 243.1 | 7 | 0 | Agent exceeded session timeout (4 min) |
| requests_7502 | False | 285.3 | 8 | 557 | Agent exceeded session timeout (4 min); reference control also fails four network-timeout tests |
| httpx_3672 | False | 242.4 | 8 | 0 | Agent exceeded session timeout (4 min) |

## Interpretation and limits

- The account reported 16,000 input tokens/minute. Token-aware pacing eliminated immediate overload but waiting consumed the four-minute task budget. Elapsed time includes setup, tools and verification; it is not pure model latency.
- Nine tasks pass reference-patch controls in this environment. Requests 7502 retains four network-timeout failures even with its reference patch, so it is not a clean model-accuracy measurement. It was retained in the declared split.
- The prompt directs temporary scripts to /tmp, while write_file only accepts workspace paths. This caused failed tool attempts. Future changes should align instructions with tools and reduce unnecessary full-file context before considering training.
- The same submitted workflow and fixed ten-task selection were retained during the final batch. Earlier interrupted setup runs are reported separately. No reference patch was given to the model.
- The rich_3105 task statement largely references another issue rather than describing the bug; offline execution cannot fetch that missing issue context. This is another limitation on interpreting failures.
- No GPU rental or alternate model/provider was used. The competition submission is unchanged.

See [API runtime and protocol](API_BASELINE.md), [frozen selection](../experiments/api-diagnostic-10-v1.json) and [official pricing](https://ai.google.dev/gemini-api/docs/pricing#gemma_4). Detailed patches, traces and provider records remain in ignored runs/.
