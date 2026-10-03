# Prompt iteration

Run one bounded experiment at a time: baseline, inspect, form one hypothesis,
change one factor, rerun, then keep or revert. The current development task is
`httpx_3672`. It has working local evaluator controls, but tuning on this task
makes its result development evidence, not a generalization claim.

## Fixed conditions

- API prototype: `gemma-4-31b-it`, backend `ai_studio`, existing central Gemini
  profile. The official submission remains `gemma-4-31b-it-qat-w4a16-ct`.
- No per-task wall-clock limit for the local API run. Limits remain 50 tool
  calls, 80 turns, and 120 seconds per command. API pacing and its oversized
  context stop still apply. Waiting counts toward elapsed time.
- Preserve task IDs, repository snapshots, sampling, thinking mode, tools,
  dependencies and effective limits between a baseline and its candidate.
- The earlier ten-task run used a four-minute limit. Keep it as historical
  evidence; establish a new baseline before attributing changes to a prompt.

## One cycle

1. Copy `experiments/iteration-template.json` into ignored run storage and fill
   in a cycle ID, unique run IDs, the intended comparison, and stop criteria
   before execution. Do not overwrite an existing run.
2. Run the unmodified baseline from the project root in WSL:

   ```sh
   ~/.venvs/gemma-baseline/bin/python tools/run_api_baseline.py --task-id httpx_3672 --submission-dir submission --run-id api-iter-001-httpx3672-20261003 --hypothesis "Establish the original-prompt baseline without a wall-clock limit."
   python tools/iteration_report.py runs/api-iter-001-httpx3672-20261003 --record
   ```

   These IDs document the first cycle; choose fresh IDs for another cycle.
   The quota window is local to each runner process. Allow at least 65 seconds
   after the previous process completes before another run, and avoid concurrent
   experiments on the same API profile.

3. Inspect the agent's own tool trace and patch, evaluator outcome, API errors,
   token usage and elapsed time in that run. Classify the failure first: model
   reasoning, prompt/tool misuse, quota/context limit, or environment failure.
   Never inspect reference fixes to write the candidate, feed reference patches
   to the agent, or change the evaluator to make a candidate pass.
4. Write one testable hypothesis and its expected signal. For example: the
   agent spends calls attempting unsupported file paths, so clarify the tool's
   path rules and expect fewer rejected calls. Copy the source submission to a
   separate candidate directory, such as `runs/iteration-candidates/httpx-p01/`,
   and change one factor. Do not edit a completed run's submission snapshot.
5. Run the candidate with the same task and settings:

   ```sh
   ~/.venvs/gemma-baseline/bin/python tools/run_api_baseline.py --task-id httpx_3672 --submission-dir runs/iteration-candidates/httpx-p01 --run-id api-iter-002-httpx3672-20261003 --parent-run api-iter-001-httpx3672-20261003 --hypothesis "REPLACE_WITH_THE_OBSERVED_FAILURE_AND_ONE_EXPECTED_CHANGE"
   python tools/iteration_report.py runs/api-iter-002-httpx3672-20261003 --compare runs/api-iter-001-httpx3672-20261003 --record
   ```

6. Record and compare the two runs offline with `iteration_report.py`. It writes
   a safe `report.json`, checks model/task/configuration/environment compatibility,
   and adds a ledger row with `--record`; it does not promote a candidate. If the
   runs are incompatible, resolve the mismatch before drawing a prompt conclusion.
   Use `resolved` from official
   verification as the task outcome; a plausible patch or successful agent
   message is insufficient. Also compare errors, calls, tokens and time. Retain
   the candidate if it improves the declared outcome without invalidating the
   comparison; otherwise revert or mark it inconclusive. A single stochastic
   result is provisional, and an infrastructure failure is not a prompt score.
7. Confirm each actual run has a row in `experiments/results.csv`. Record the decision and
   evidence paths in the cycle record. Promote a retained prompt into a new
   reviewed source version; keep both prior run directories unchanged.

   Review can be performed by the supervising coding agent within an authorized
   batch; it does not require a new human approval for every round. The reporting
   tool itself never promotes a candidate.

The runner snapshots the chosen submission and records effective configuration
and provenance per run. Keep source revision and file hashes with the comparison
when the working tree is dirty. Unknown billing remains blank; published-rate
estimates and measured token usage do not establish actual charges.

While a process is active, use the reporting command without `--record`. An
ended, interrupted run can be retained with `--record --finalize-incomplete`;
missing task results remain in its predeclared denominator. Never finalize a
still-running process.

## Success and stopping

The current invocation runs one baseline task. The candidate command above
illustrates the next experiment. Future batches can execute their iterations
autonomously within an explicitly scoped plan: declare the task IDs, maximum
iterations, allowed API usage or spending, success condition and stopping rules
before starting. Record each hypothesis and keep/revert decision. A batch does
not need a separate approval for each iteration within its authorized scope.
No scheduled or indefinite loop is configured by this workflow.

Stop the current run on completion, a harness budget stop, quota/context stop,
API failure, or user interruption. Diagnose operational failures before another
call, and halt a batch at its predeclared consecutive no-gain threshold or on
repeated quota/environment failures. Preserve the plan's explicit model,
provider, task scope and usage/spending budget; any retries must fit its declared
retry policy. No wall-clock cap does not guarantee progress:
if a request stalls, interrupt it and preserve its incomplete outcome and usage.

Passing `httpx_3672` meets a development milestone only. Before keeping a change
as a broader improvement, predeclare additional task IDs and run both versions
under identical conditions. Use the existing frozen diagnostic for regression
checks; its previously inspected tasks are not untouched holdout data. Reserve
new, uninspected tasks before further tuning for a separate validation check.
Do not remove failures from the denominator after seeing results. The Requests
task's known environment limitation must remain visible in reports.

Recursive improvement is an experiment process, not a guaranteed outcome.
If a candidate fails its hypothesis, record that result and choose the next
hypothesis explicitly. Confirm promising API changes separately on the official
quantized model before treating them as competition improvements.

## Private artifacts

Keep task source, patches, traces, detailed evaluator output, adapters and local
cycle records under ignored storage. Publish only authored configuration,
sanitized aggregate results and non-sensitive experiment decisions. Credentials
stay in the central registry and memory; no copied keys, environment dumps or
private reference material belong in GitHub. See [API_BASELINE.md](API_BASELINE.md)
for runtime details and [experiment protocol](../experiments/README.md) for the
result ledger.
