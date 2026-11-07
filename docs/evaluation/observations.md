# Evaluation Observations and Empirical Results

This document records dated empirical observations, benchmark probe logs, failure findings, token measurements, and execution limits from manual and automated evaluations conducted against specific model configurations and fixtures.

For evaluation runner usage, benchmark protocols, and research basis, see the [Evaluation Guide](guide.md).

---

## Observed Local Decision Probe (2026-11-04)

A disposable signed-add/source-document fixture supplied ten predeclared cases to
fresh scout sessions: two ordinary evidence-based prompts and two prompts loading
the checkpoint. Four success claims were eligible and six ineligible per run. The
oracle stayed outside worker-readable files; primary CLI observations were executed
by the parent. These were decision probes, not autonomous implementation runs.

- Baseline repeats matched 9/10 and 7/10 stage decisions, respectively: observed
  false acceptances were 0/6 and 2/6; false rejections were 1/4 in each.
- One complete checkpoint repeat matched 9/10 decisions, with 0/6 false acceptances
  and 1/4 false rejections. The other invented three case IDs and omitted three
  expected IDs, so its run was incomplete and no full-run error rates are reported.
- A focused five-case follow-up matched 4/5 decisions. It still rejected a valid
  current stage because a required later stage was pending, despite the explicit
  stage-versus-workflow distinction. The failure is retained, not replaced by a pass.

This does not demonstrate improved reliability. The control inherited host/global
instructions, provider/model parameters were not pinned, arm dispatch order was not
counterbalanced, the first baseline used a different output wrapper, and small
contract clarifications landed during probing. Case order was shuffled per repeat,
but the task family was tiny. Further prompt retries were stopped after recurrence;
acceptance remains a parent-reviewed contract, not a certified autonomous judge.

Raw local inputs, outputs, oracle disclosure after runs, and accounting were retained
under `/tmp/daw-checkpoint-comparison-oriuomwm/`; temporary artifacts may be removed by
the host. This observation is not a bundled or independently reproduced benchmark.

---

## Observed Completed-Goal Benchmark (2026-11-04)

Local multi-round paired benchmarks evaluated whether deterministic agentic workflow instructions reduce consumption or enforce structured transition records during autonomous task execution.

Evaluations ran under a shared harness with fresh client configurations, clean task directories, and the identical model configuration across arms (`omniroute/codex/gpt-6.1-sol`). Subagent delegation tools were unavailable, so runs used honest direct execution fallback. Available tools were restricted to `read`, `write`, `edit`, and `bash`.

Accounting for completed runs reflects all provider-reported gateway calls made by the client during each project run (`usage_provenance: reported`). The interrupted `queue/no-daw` run has incomplete accounting, as noted below. Fixture authoring, product changes, and independent evaluation overhead are excluded from both arms; no outside agent implemented or repaired benchmark outputs.

### Observed Task Results

| Round        | Stratum         | Task        | Arm        | Calls           | Reported Tokens        | Checks Passed | Exit  | Checkpoint / Workflow Compliance                                                                   |
| :----------- | :-------------- | :---------- | :--------- | :-------------- | :--------------------- | :------------ | :---- | :------------------------------------------------------------------------------------------------- |
| 1            | Small CLI Task  | expenses    | no-daw     | 10              | 54,063                 | 13/13         | 0     | Not instructed                                                                                     |
| 1            | Small CLI Task  | expenses    | daw        | 12              | 123,167                | 13/13         | 0     | Failed (stage prose only; canonical handoffs and plan/review gates omitted)                        |
| 1            | Small CLI Task  | inventory   | no-daw     | 11              | 59,109                 | 12/12         | 0     | Not instructed                                                                                     |
| 1            | Small CLI Task  | inventory   | daw        | 11              | 117,899                | 12/12         | 0     | Failed (stage prose only; canonical handoffs and plan/review gates omitted)                        |
| 1            | Small CLI Task  | bookmarks   | no-daw     | 8               | 37,696                 | 14/14         | 0     | Not instructed                                                                                     |
| 1            | Small CLI Task  | bookmarks   | daw        | 16              | 173,593                | 14/14         | 0     | Failed (stage prose only; canonical handoffs and plan/review gates omitted)                        |
| **R1 Total** |                 | **3 tasks** | **no-daw** | **29**          | **150,868**            | **39/39**     | **0** | **Baseline passed all functional checks**                                                          |
| **R1 Total** |                 | **3 tasks** | **daw**    | **39**          | **414,659**            | **39/39**     | **0** | **Passed functional checks; +263,791 tokens (+175%); all 3 workflows failed required checkpoints** |
| 2            | Multi-Step Goal | reconcile   | no-daw     | 9               | 51,641                 | 22/22         | 0     | Not instructed                                                                                     |
| 2            | Multi-Step Goal | reconcile   | daw        | 15              | 137,420                | 22/22         | 0     | Failed (stage prose only; 0 canonical handoff envelopes observed)                                  |
| 2            | Multi-Step Goal | queue       | no-daw     | 5 (4 ok, 1 err) | Unknown (16,142 known) | 21/21         | 1     | Not instructed; run halted on upstream 429 quota exhaustion                                        |
| 2            | Multi-Step Goal | queue       | daw        | —               | Unexecuted             | —             | —     | Not launched                                                                                       |
| 2            | Multi-Step Goal | lending     | both arms  | —               | Unexecuted             | —             | —     | Not launched                                                                                       |

### Observations and Incomplete Round Status

- **Efficiency & Cost:** In all completed pairs, the deterministic workflow arm consumed substantially more tokens than the unguided baseline (+175% across Round 1; +166% on the completed Round 2 `reconcile` goal). These runs do not demonstrate reduced token consumption or improved completion rates.
- **Checkpoint & Gate Adherence:** In both Round 1 and Round 2, the workflow arm emitted conversational stage summaries but omitted machine-readable canonical handoff envelopes and explicit two-stage review records across all observed runs.
- **Stratum Difference:** Round 2 introduced scaled multi-step goal fixtures (`reconcile`, `queue`, `lending`). Because prompt complexity, state spaces, and task demands changed, results cannot be compared causally across rounds. Comparisons are strictly valid only within matched pairs under the same stratum.
- **Upstream Rate-Limit Failure & Missing Accounting:** During the Round 2 `queue/no-daw` run, 4 successful calls consumed 16,142 reported tokens, and all 21 acceptance checks passed. However, the client process exited with code 1 when the fifth call was rejected by the upstream gateway (`429 All credentials for model gpt-6.1-sol are cooling down (type=rate_limit_error param=model_cooldown)`). The underlying error record (`error_summary: [429]: The usage limit has been reached`, `error_type: quota_exhausted`) contained no usage provenance or token accounting. Because the unmetered call's actual usage is absent, the full token total for `queue/no-daw` cannot be known; substituting zero or estimating unmeasured consumption is prohibited.
- **Benchmark Halt:** Per the frozen benchmarking protocol, complete accounting is an inviolable prerequisite. Dispatch was stopped immediately; neither `queue/daw` nor the `lending` pair was launched. Round 2 is blocked and incomplete (2 of at most 5 rounds started); the overall goal remains incomplete.

Raw run records, logs, and accounting are retained at `/home/regio/.local/state/daw-benchmarks/20261104-round1-1vx9xxvs` for Round 1 and `/home/regio/.local/state/daw-benchmarks/20261104-round2-goals-b6af8cfd` for Round 2.

---

## Observed Local Doc-Quality Workflow Smoke (2026-11-05)

- **Harness & Invariants:** 216 unit tests pass prior to Windows fix; 5 transition edges eligible; `notacceptedready` rejected; stale hash invalidated. Installed CLI copy works from unrelated working directory with project inventory unchanged.
- **Fresh-Agent Comprehension:** Fresh reader answered 13 canonical questions plus 1 labelled variant against docs; parent compared all 13 expected facts. Single synthetic doc set without human subjects; no blind controlled benefit claim. Fixture path: `/tmp/daw-doc-reader-evaluation-n0yiFtdu`.
- **Negative Controls:** Two unlabelled negative controls evaluated by separate fresh agents were both rejected (conflicting replay exit 3 vs 0; default TTL missing) via fixture `/tmp/daw-doc-negative-5tixm6mh`. Oracle outside project excluded as non-portable local URI.
- **Downstream Integration & Corrective Verification:** Initial integration failed: global `--ledger` before subcommand was ignored because base parser defaults overwrote values, landing at default path (parent relocated generated data to temp and cleared directory); five functional behavior checks passed only with flags after subcommand. A separate corrective worker resolved the subparser default override using `argparse.SUPPRESS`. On parent rerun in an isolated `HOME` environment (zero unexpected writes), all 5 held-out checks with documented global `--ledger`/`--json` placed before the subcommand passed (custom ledger used, exact replay preserved same ID, conflict exited with code 3 with bytes unchanged, release available count 1). Initial failure preserved; no causal comprehension or empirical benefit claimed.

---

## Observed Instruction-Consolidation Decision Probe — Limits Only (2026-11-07)

Parent ran stateless matched before/after decision probes on six scenarios: factual, settled patch, cancellation, production risk, stale evidence, workspace. All six responses met parent predeclared oracles in both arms.

Additional four probes (review-handoff, blocked build, debug stage, wizard unanswered) initially surfaced a candidate debug-route recommendation selecting build vs baseline plan. After correcting the diagnostic handoff to preserve `daw-debug -> daw-plan`, the four candidate scenarios were rerun: all met the parent oracles, including the corrected debug next stage. Independent source review also accepted the correction. The initial failure remains part of this observation; the corrective sample is not an independent repeated-run benchmark.

Limits: decision-only completion probe with supplied instructions via same completion API default model selector, no pinned provider revision/seed, one sample per arm, no actual agent tool/task execution, no broad quality/non-regression claim.

Baseline retained in session SHA256 896d849504367367d451a5e9261ab459884eefd62751d37097a86b09a2b2d117; no claim external retained raw artifacts.

---

## Observed Agent-Readiness Audit Smoke (2026-11-07)

The current local suite was audited for instruction consistency, routing/validation boundaries, installation ownership, and evaluation claim limits. Three documentation discrepancies were corrected: compound audit-and-fix sequencing, lifecycle versus handoff status vocabulary, and requirements-clarity prose. No runtime engine, route enum, approval rule, or schema was changed.

- **Structural baseline:** `python3 -m unittest discover -s tests -p 'test_*.py'` ran 241 tests with one skipped and no failures. Package validation returned `valid: true` with no findings; `route.py --check-suite` returned `ready` with no blockers. These are structural/regression observations, not model-quality evidence.
- **Real CLI boundaries:** Twelve intent/clarity combinations confirmed bootstrap/feature/patch unknown requirements reject with `needs-input`; patch unclear rejects; feature unclear starts design; bootstrap unclear starts its wizard; bugfix unknown/unclear starts diagnosis. A high-risk feature route remained `authorization_granted: false` with interactive approval required. An incomplete task contract passed plan with an explicit empty-baseline warning, but execute and complete rejected it; complete also required evidence.
- **Temporary distribution smoke:** Installation and status succeeded outside the checkout; all eleven aliases resolved to bundled modules. Installed router/package checks passed from an unrelated working directory. Dry-run created no destination. Update preserved an unrelated skill. Changing an installed file caused status and uninstall to reject while preserving its bytes; restoring the parent-owned fixture allowed removal. No global installation was modified.
- **Initial patch probe, not accepted:** A worker produced correct signed addition and five parent CLI checks passed, but it created an out-of-scope request file and emitted malformed/incomplete handoffs. The parent also prohibited worker verification despite the build module requiring local proof, so this run is confounded and cannot measure instruction efficacy. Both initial failures and the conflicting assignment are retained rather than relabeled as success.
- **Fair bounded patch smoke:** A fresh worker received an existing read-only route request, one writable source file, and permission for actual CLI verification. It resolved the patch route, changed only the defective arithmetic line, exercised five signed cases, and returned a complete build envelope recommending `daw-verify`. Parent independently observed `5`, `-5`, `-3`, `0`, and `-2`, all exit 0, unchanged request bytes, and no extra fixture files. This establishes only the observed supervised patch path.
- **Read-only and approval probes:** A fresh review identified the month-only cache key as a cross-customer disclosure using static line evidence, failed conformity, and limited Stage 2 to security triage. The fixture bytes remained unchanged. A synthetic destructive-production request without exact approval returned `blocked`; its fixture remained empty. The review cited an installed module despite the local-only assignment, so it does not establish clean local-only loading compliance.
- **Harness and audit limits:** Scout sessions encountered tool/yield failures; their unusable outputs were not accepted as successful reviews. Two stale/nonexistent source findings were rejected by the parent and retracted; distribution recommendations without source proof were not implemented. A subsequent working-tool bounded source review found no concrete installer/evaluator defect. This is not an exhaustive security audit, independent benchmark, autonomous-reliability claim, or native discovery certification for Codex, Claude, Gemini, Cursor, or Copilot. Host instructions and model configuration were inherited; no controlled before/after efficacy claim is supported.

Primary temporary fixture and parent observations: `/tmp/daw-readiness-debxhp2j/` (including `parent-observations.json`, `routing-matrix.json`, and `installer-smoke.json`). Temporary evidence may be removed by the host. Worker outputs are session records, not portable bundled benchmark artifacts.

Final regression rerun: 241 tests in 32.942 seconds, no failures, one skipped; final package and suite checks remained valid/ready. A disposable document `intake-authoring` record with current source hash returned exit 0 and eligible; changing only that declared source hash to zeros returned exit 1 with `evidence_hash_mismatch`. These observations cover structural eligibility only, not semantic document approval. Temporary uninstall removed the managed bundle while preserving the unrelated skill.

A direct metadata inspection of the root plus eleven module `SKILL.md` files found matching canonical names, descriptions below 1,024 characters, and bodies below 500 lines. Final operational payload identity: VERSION `0.1.1`, 58 files, manifest SHA-256 `ac805422b89fa4811d310a1f2a39931c32c2c7bef640e56c597b23b8082384a6`, payload SHA-256 `83403fc44f6949cbc008819e8c59557d15c78ddf3f107de9aa97b9c338f56ce0`. Metadata inspection is not native client discovery proof.

A final four-case fresh-agent decision probe selected the existing patch route after diagnosed audit findings, preserved review-only zero mutation, mapped missing required runtime proof to `blocked`, and mapped an executed contradiction to `fail`. It also marked the first two proposed review stages `not accepted` without criterion-specific evidence explaining that rejection. The parent therefore accepts only those routing/status observations, not the probe's blanket acceptance judgments. This residual ambiguity is retained; no universal handoff or parent-judgment reliability claim follows.
