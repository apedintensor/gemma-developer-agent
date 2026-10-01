# Experiment protocol

Use a unique run_id and add a row to results.csv for each actual run. Keep detailed logs in ignored runs/<run_id>/. Never record credentials or full environment dumps.

Record Git commit, exact model ID, backend (ai_studio or official_harness), fixed dataset split version, attempted/solved counts, success rate, wall time, configuration and log paths. Success rate is solved/attempted; include timeouts, missing patches and execution failures in the predeclared denominator. Leave unknown cost blank, not zero.

Preserve sampling parameters, seed when supported, prompt/tool versions, adapter version/path, and hardware/software versions in each run's configuration. Compare prototype and official-harness results separately.

Fix task IDs before evaluation. Reference patch/test_patch files belong only in authorized training or evaluator inputs, never in validation-agent context. Record contamination risks and similarity across tasks from the same repository. Public development data is not the hidden test set. Do not commit restricted tasks, patches or logs to this public repository.

Evaluator controls use backend `official_harness_control` and model ID `none`. They must not be aggregated into agent success rates. A `working-tree:<base SHA>` code version denotes uncommitted additions at run time; the control runner SHA256 is recorded in notes and private environment checksums. Pending Kaggle submissions have unknown counts/scores, left blank until reported.
