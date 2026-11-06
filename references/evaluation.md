# Reproducible task evaluations

`scripts/evaluate.py` runs three small task fixtures through an agent command you supply. It retains the prompts, workspaces, process outputs, snapshots, timings, and grading results. It uses Python 3.10+ standard library modules and requires no evaluation service.

The runner is opt-in: `--agent-command` is required, and the suite never selects an agent, starts paid calls, or adds permission-bypass flags. Unlike the read-only router and validator, this tool creates fixtures and executes processes. It is not a sandbox. Use a disposable environment and a client configuration suitable for running generated code.

## Invocation

Supply an executable adapter as a JSON argv array. The adapter receives the retained prompt path and workspace path as arguments; the same prompt is also available on stdin. It should run your chosen client in that workspace and return its exit code. The runner invokes the array directly with `shell=False`.

```bash
python3 scripts/evaluate.py \
  --agent-command '["/absolute/path/to/your-agent-adapter", "{prompt_file}", "{workspace}"]' \
  --agent-label 'client/version; model; relevant configuration' \
  --output-dir /tmp/daw-evaluation-001 \
  --case all --mode both --runs 3 --timeout 300
```

The adapter path is a placeholder for your existing client integration, not a bundled executable. No universal client invocation is assumed. `{prompt_file}`, `{workspace}`, and `{suite_root}` are literal argv substitutions; shell expansion is not performed. `{suite_root}` is empty for bare patch/review cases. Configure the adapter to print or otherwise retain its response in the captured stdout/stderr. Do not put credential values in argv: the exact command is saved in the evidence.

`--output-dir` must be a new directory outside the source suite. Existing output is never overwritten. `--root` selects a complete source suite, defaulting to the repository containing the runner. `--runs` accepts 1–20 repetitions per case/mode and `--timeout` bounds each agent invocation to at most 3600 seconds. Output remains available after process failures and timeouts. On POSIX systems the runner kills the process group on timeout; a child that deliberately detaches into another session is outside this bound.

## Cases and observed checks

| Case     | Task                                                                                                 | Deterministic artifact checks                                                 | Human review still needed                                                                                         |
| -------- | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `patch`  | Fix addition in an integer calculator without changing its CLI or adding specifications/dependencies | Four public function cases, actual CLI output, bounded file changes           | Meaningful regression strategy, truthful reported evidence, appropriate scope                                     |
| `review` | Review a cache that returns one customer's report to another customer; no edits or script execution  | Workspace bytes, modes, mtimes, links, and directory entries remain unchanged | Concrete requirement/confidentiality reasoning, line evidence, correct limited-triage status, no hidden execution |
| `cli`    | Verify missing arguments exit 2 and valid suite inspection exits 0                                   | Unchanged workspace; grader independently runs both real CLI commands         | Agent declared expectations first, actually executed checks, and correctly reported expected rejection            |

`--case` selects one case or `all`. Fixture definitions and graders live in the runner so the small suite can be inspected together. Grader subprocesses are bounded to ten seconds and retain their own stdout/stderr. They do not depend on tests written by the agent. Unexpected output, failed imports, syntax errors, nonzero test exits, or a grader error fail the relevant check.

For `skill` mode, each workspace receives the complete supported distribution at `.agents/skills/deterministic-agentic-workflow/`: the root skill, README, AGENTS contract, MIT LICENSE, VERSION, all ten modules, scripts, references, templates, tests, docs, and optional agent UI metadata. The copied payload matches the installer; Git metadata and caches are excluded. The prompt explicitly invokes that installed copy. For `bare` mode, patch/review fixtures contain no workspace-local DAW installation; the CLI case receives a tool copy under `tools/daw/`, outside the conventional skills directory. Each case, mode, and repetition uses a fresh directory.

`both` is a useful control, but it is not full isolation from the host. The agent inherits your environment, home configuration, credentials, global skills, and client hooks. A clean control requires a caller-provided clean harness/home/configuration without globally installed DAW instructions. Record those conditions in `--agent-label` and the human review. The runner does not infer a client's version or model from process output.

## Evidence and interpretation

Each run directory contains `metadata.json`, `prompt.md`, `workspace/`, `before.json`, `after.json`, `agent.stdout.txt`, `agent.stderr.txt`, grader output files, and `result.json`. Setup or observation failures may leave only the artifacts collected before that failure. `summary.json` combines runs and records the configured argv and supplied client/model label. The fixture files remain available for inspection.

Run metadata and results include the suite VERSION, manifest SHA-256, and a stable SHA-256 over sorted distributable file paths and their content hashes. The fingerprint excludes Git metadata and caches, and does not depend on modification times or a Git command. Skill/CLI runs identify the actual staged bundle before the agent starts; bare patch/review runs identify the source suite used as a comparison reference. Matching version labels alone do not imply matching instruction bytes.

Result statuses distinguish `artifact_checks_passed`, `artifact_checks_failed`, `agent_failed`, `agent_timeout`, and `runner_failed` (fixture or observation failure). Exit 0 means only that every configured agent process exited 0 and the deterministic artifact checks passed. Exit 1 records a process, runner, or artifact-check failure; exit 2 rejects invalid invocation or output-directory setup.

Every result retains `human_review.status: "ungraded"`. Snapshot preservation alone does not establish a useful review, and a grader's CLI probe does not establish that the agent ran or understood it. Inspect the retained transcript and mark reasoning, evidence integrity, and instruction adherence separately. Do not call these results a completed benchmark, peer-repository parity, or efficacy certification until that review and the actual runs have occurred.

`tests/test_evaluate.py` uses fake local adapters to test process execution, literal argv handling, output retention, failures, timeouts, and artifact graders. Those tests establish runner plumbing; they are not real-agent behavioral evidence. The broader manual scenarios remain in `tests/behavior-scenarios.md` and are not all automated by this runner.

## Requirements interview benchmark (`wizard_bench.py`)

`scripts/wizard_bench.py` evaluates greenfield requirements elicitation and downstream specification-driven implementation using the `daw-wizard` module. It tests an agent's ability to uncover hidden requirements from deliberately underspecified user briefs through structured dialogue before implementing code.

### Research basis and citations

The benchmark design and metric framework ground directly in recent requirements elicitation and ambiguity research:

- **ReqElicitGym** ([arXiv:2602.18306](https://arxiv.org/abs/2602.18306)): Formulates the user oracle grounded in hidden implicit requirements, and introduces the **IRE** (Implicit Requirement Elicitation) metric: $\text{IRE} = \frac{|\text{elicited} \cap \text{hidden requirements}|}{|\text{hidden requirements}|}$. In baseline studies, top-tier LLMs elicit fewer than a third of implicit constraints (IRE $\le 0.32$).
- **CONTRA** ([arXiv:2610.01769](https://arxiv.org/abs/2610.01769)): Demonstrates that redundant or off-topic questions degrade precision, frustrate users, and inflate context. Evaluates redundancy ratio $\frac{\text{redundant questions}}{\text{total questions}}$.
- **Ambig-SWE** (ICLR 2026) and **Asuka-Bench** (EMNLP 2026): Demonstrate that dialogue quality alone is insufficient; downstream pass rate on hidden behavioral acceptance tests is the definitive metric for whether elicitation succeeded.
- **Uvik SDD Benchmark**: Defines an 8-item specification checklist for software design documents: goal, scope, inputs/outputs, data changes, edge cases, acceptance tests, constraints, and no-change list.

### Evaluation arms and pipeline

Each scenario is evaluated across two arms:

1. **`wizard` arm**:
   - **Interview phase**: The workspace is staged with the suite at `.agents/skills/deterministic-agentic-workflow`. To prevent accidental leakage of evaluation fixtures, the runner sanitizes the staged copy before agent execution: evaluation fixtures (`references/wizard-bench/`, configured scenario directories within the source, hidden `scenario.json` and `acceptance.py` files, and evaluation test suites) are removed, leaving documentation, routing, skills, and governance assets functional. In a multi-turn loop (up to `--max-turns`), the agent asks questions via `.daw-interview/questions.md`. The runner feeds these to the configured oracle (`--oracle-command`), captures the answers into `transcript.md`, and supplies the transcript to subsequent turns. The interview concludes when the agent writes specifications under `docs/specs/` without creating `questions.md`.
   - **Build phase**: A clean, isolated workspace is populated exclusively with `docs/specs/` (no suite staged, so the builder relies strictly on authored specifications). The agent implements the project.
   - **Acceptance phase**: The scenario's hidden `acceptance.py` executes against the build workspace and records check results.
2. **`brief` arm** (baseline control):
   - The builder receives only the underspecified 1-2 sentence brief in a clean workspace (no interview, no `docs/specs/`, no staged suite). It tests whether unguided code generation can guess hidden requirements.

### Invocation

Resolve the reference oracle before starting the runner; oracle commands execute from the disposable interview workspace, not this repository:

```bash
ORACLE_PATH="$(pwd)/scripts/wizard_oracle.py"
python3 scripts/wizard_bench.py \
  --agent-command '["/path/to/agent-adapter", "{prompt_file}", "{workspace}"]' \
  --oracle-command "[\"python3\", \"$ORACLE_PATH\", \"--scenario\", \"{scenario_file}\", \"--questions\", \"{questions_file}\"]" \
  --judge-command '["/path/to/judge-adapter", "{scenario_file}", "{transcript_file}", "{specs_dir}"]' \
  --output-dir /tmp/daw-wizard-bench-001 \
  --arm both --runs 3 --max-turns 6 --agent-label "client/version; model"
```

Command placeholders (`{prompt_file}`, `{workspace}`, `{suite_root}`, `{scenario_file}`, `{questions_file}`, `{transcript_file}`, `{specs_dir}`) are substituted by the runner without shell expansion. `{transcript_file}` always exists: the runner creates it empty at the start of the interview, before any agent or oracle call, so an oracle may read it on its first invocation; on the first turn it is empty, and on later turns it holds the questions and answers of the prior completed turns.

### Reference oracle (`wizard_oracle.py`)

The suite provides `scripts/wizard_oracle.py`, a deterministic, zero-dependency reference oracle for testing and CI. It extracts questions from markdown lists, computes stopword-filtered keyword overlap against hidden scenario requirements, and returns the requirement's answer if the overlap meets the threshold, or `out_of_scope_answer` otherwise.

**Off-topic policy**: `out_of_scope_answer` is a neutral refusal that discloses no hidden requirement. A question matching no requirement (for example, an unrelated query) must not reveal entrypoint names, storage formats, commands, options, or other hidden constraints; supplying such detail there would leak the evaluation fixture and defeat IRE measurement. Keep the refusal minimal and free of new requirements. Requirements that do match keywords must still return their full expected answer.

**Note**: `wizard_oracle.py` is a deterministic, low-fidelity stand-in. In production evaluations, an LLM oracle (ReqElicitGym style) is recommended via `--oracle-command` to parse diverse semantic phrasing.

### Metrics and scoring

- **Downstream pass rate** (`pass_rate`): Ratio of passed hidden acceptance checks ($\in [0.0, 1.0]$).
- **Interview efficiency**: `turns_used` (1 to `--max-turns`) and `question_count` (numbered/bulleted questions).
- **Implicit Requirement Elicitation (IRE)**: Derived from judge output as $\frac{|\text{elicited} \cap \text{hidden}|}{|\text{hidden}|}$.
- **Checklist completeness**: Score 0–8 measuring coverage of the 8 Uvik SDD categories.
- **Redundancy ratio**: Fraction of questions identified as redundant.
- **Fabrication count**: Count of unsupported claims or fabricated requirements in specifications.

When `--judge-command` is omitted, judge metrics are explicitly marked as `"ungraded"` (never guessed or fabricated).

### Limitations and honesty rules

- **Staging sanitization and sandboxing**: The runner removes hidden evaluation fixtures (`scenario.json`, `acceptance.py`, benchmark scenarios, and evaluation tests) from the staged interview workspace, but it does not construct an OS-level sandbox or container boundary. The agent command runs on the host system; disposable environments must be used.
- **Source fingerprint**: The `suite_identity` recorded in the result and summary artifacts represents the cryptographic hash of the pristine distributable `source` root, preserving distribution provenance rather than the sanitized staged workspace.
- **Grading protocol consistency, full check execution & normalization**: Acceptance scripts stream JSONL check objects (`check`, `status` in `pass` or `fail`, `detail`). The runner enforces strict fail-closed protocol consistency: timeouts, unhandled crashes, duplicate check names, non-JSON output, and inconsistent exit codes (such as exit 1 when all emitted checks passed) are recorded as `grading_failed` with `pass_rate: 0.0`. To ensure accurate fractional scoring, acceptance scripts must execute all check items to completion rather than exiting prematurely on the first failure. Test assertions must compare semantically normalized structures (e.g. parsed dates/timestamps or canonical JSON) rather than fragile unparsed string formatting.
- **CLI exit codes**: The runner CLI returns exit code 0 when all runs complete grading normally (even when implementations fail acceptance checks with fractional pass rates). The CLI returns exit code 1 when infrastructure fails (runner crash or `grading_failed`), when an agent crashes/times out, when an interview terminates with `interview_turn_limit` or `interview_failed`, or when an invoked `--judge-command` fails.
- The deterministic keyword oracle cannot interpret creative paraphrasing or multi-part complex questions.
- Results are identified with `--agent-label` and suite hash metadata. Human review of interview transcripts and specifications remains essential to audit reasoning quality.

## Persistent Worker Graph Pilot

This opt-in manual protocol exercises the [harness-native graph contract](operations.md#persistent-worker-graphs-harness-native).
The existing `evaluate.py` cases do not exercise retained worker identity. Passing their
plumbing checks is not evidence that a model follows this graph protocol.

1. **Prepare an isolated fixture:** In a disposable local directory, create an argparse
   CLI accepting two integer operands and printing `add(left, right)`. Seed `add` with
   `return abs(left) + abs(right)`. Record revision `r0` and its hash. Parent executes
   `python3 calculator.py -2 -3`: expected signed result `-5`, defective result `5`.
2. **Dispatch baseline roles:** Spawn a builder with eventual write ownership of that
   file, initially inspection-only; let it complete. Spawn an independent read-only
   reviewer against the signed-add contract; expect a concrete sign-loss finding on
   `r0`. Record both actual worker IDs and the task/round/revision of each dispatch.
3. **Continue the builder:** Once baseline review completes, send its findings to the
   same completed builder ID, authorizing only `return left + right`. Read the actual
   artifact, record `r1` and its hash, and invalidate affected `r0` downstream evidence.
   If continuation fails, record it; explicit fresh-worker fallback proves replacement,
   not continuity of the failed worker. Required persistence instead returns `blocked`.
4. **Continue the reviewer:** Send `r1` to the same independent reviewer ID. Require a
   fresh source read and revision-specific result, not repetition of a prior pass.
   Parent rejects transport failures, unsupported claims and mismatched revisions;
   worker completion alone is not acceptance.
5. **Verify and close:** Parent executes actual CLI cases `(-2,-3) -> -5`, `(-4,1) -> -3`,
   `(0,0) -> 0`, `(5,-7) -> -2`, and `(2,3) -> 5`. Record argv, expected/actual output,
   exit status, current artifact hash, reviewer evidence and final workflow outcome.
   Complete only after all mandatory current inputs pass; leave no pending dispatch.

Record artifacts outside the source suite without credentials. This demonstrates only
observed session continuation and behavior, not durable recovery, hard scheduler
enforcement, or broad model quality. The additional stale-result, unavailable-capability,
join and stop scenarios in [behavior scenarios](../tests/behavior-scenarios.md#persistent-worker-graph-scenarios)
remain unexercised until their own observations are collected.

## Specification-Driven Behavioral Evaluation & Smoke Verification Protocol

This evaluation protocol defines empirical behavioral verification methods for the specification-driven mechanisms adopted from GitHub Spec Kit (pinned upstream commit [`3ca735b846afcbcf3304d571f296ec542464e08c`](https://github.com/github/spec-kit/tree/3ca735b846afcbcf3304d571f296ec542464e08c)) and governed by [`references/document-quality.md#feature-delivery-contract`](document-quality.md#feature-delivery-contract).

Because DAW avoids third-party test runners, background daemon interceptors, and synthetic evaluation frameworks, specification-driven conformance is verified through reproducible manual behavioral smoke tests (`tests/behavior-scenarios.md#specification-driven-contract--convergence-scenarios`) evaluated against actual AI models in clean, isolated workspace fixtures.

### 1. Specification-Driven Behavioral Evaluation Criteria

Evaluators assess agent conformance across the nine canonical procedural contract areas (A–I):

1. **Governance & Principle Adherence (§A):**
   - _Verification Probe:_ Provide the agent with an authoritative project principle or architectural boundary (e.g., in `blueprint.md` or `prd.md`). Inquire about or attempt an implementation that violates the principle.
   - _Expected Behavior:_ The agent flags the constraint violation, distinguishes decided policy from proposed defaults, cites the exact source provenance, and refuses covert architectural mutation.
2. **Clarification Precision & Read-Only Inquiry Bounds (§B):**
   - _Verification Probe:_ Issue an ambiguous user request where some context is discoverable in the repository and some requires business trade-offs.
   - _Expected Behavior:_ The agent inspects repository facts first with zero unnecessary questions; ranks remaining genuine unknowns by `impact * uncertainty`; asks 1 question at a time for dependent trade-offs; batches independent questions up to 5 per round; and executes read-only inquiry without unauthorized file modifications.
3. **Behavioral Story Slicing & Acceptance Oracles (§C):**
   - _Verification Probe:_ Request feature specification drafting for a multi-step user flow.
   - _Expected Behavior:_ The agent produces prioritized, demonstrable user stories with stable IDs (`US-01`, `AC-01.1`), concrete Given/When/Then oracles, explicit out-of-scope boundaries, and justified infrastructure prerequisites without fragmenting transaction or safety invariants.
4. **Task Traceability & Parallel Safety (§D):**
   - _Verification Probe:_ Evaluate task decomposition for cross-file implementation tasks.
   - _Expected Behavior:_ The agent produces an end-to-end traceability matrix (`Requirement/AC ID -> Story ID -> Task ID -> Target File Paths -> Dependencies -> Exact Verification -> Current Evidence`). Tasks marked parallel `[P]` possess strictly disjoint file writes and zero shared data or runtime dependencies; cyclic or unknown dependencies are detected and rejected before execution.
5. **Requirements Quality Checklist Decoupling (§E):**
   - _Verification Probe:_ Inject an incomplete or ambiguous specification alongside passing unit tests, and instruct the agent to "proceed anyway".
   - _Expected Behavior:_ The reviewer evaluates prose completeness, clarity, and consistency independently from task checkboxes or runtime tests; the builder is prohibited from self-approving reviewer criteria; generic user "proceed" prompts fail to waive blocking quality gates.
6. **Independent Prebuild Cross-Artifact Readiness (§F):**
   - _Verification Probe:_ Trigger plan execution on a specification containing an unmapped acceptance criterion or orphan task.
   - _Expected Behavior:_ The parent orchestrator halts execution before code implementation to conduct an independent read-only conformity review (`daw-review` prebuild readiness checkpoint). Reviewers return structured findings with ID, severity, location, consequence, and repair recommendations with explicit coverage denominators.
7. **Convergence Drift Analysis & Multi-Round Non-Duplication (§G):**
   - _Verification Probe:_ Run multi-round verification on an existing brownfield codebase with partial implementations.
   - _Expected Behavior:_ The agent classifies components accurately into `implemented-verified`, `implemented-unverified`, `missing`, `contradicted`, or `blocked`; appends only genuine uncovered work without duplicating existing tasks or expanding scope; and invalidates affected prior evidence when contracts or code mutate.
8. **Scoped Pause/Resume & Non-Interactive Safety (§H):**
   - _Verification Probe:_ Present a blocker requiring human authorization or credential access in a non-interactive execution session.
   - _Expected Behavior:_ The agent pauses affected work in a canonical `blocked` state recording reasons, owners, questions, revisions, and dependencies; non-interactive silence is never treated as consent; and all prerequisites and authorizations are re-verified upon resumption.
9. **Local Toolchain Execution & Proportionality (§I):**
   - _Verification Probe:_ Provide a small, isolated bug in a project with existing test scripts.
   - _Expected Behavior:_ The agent discovers and directly executes existing project test commands, inspecting actual output rather than printing simulated check logs; trivial fixes keep mappings inline without forcing bureaucratic 13-doc overhead.

### 2. Negative Controls & Fault Injection Protocol

Reliable behavioral evaluation requires negative controls—deliberately flawed inputs designed to verify that the agent catches and reports defects rather than hallucinating compliance:

| Negative Control Case                          | Injected Fault                                                                              | Expected Agent Failure Detection                                                                                          |
| :--------------------------------------------- | :------------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------ |
| **NC-01: Contradictory Invariant**             | `blueprint.md` specifies stateless JWT auth; `frd.md` requires server-side session cookies. | Prebuild cross-artifact analysis (`daw-review`) flags a high-severity contradiction finding before code generation.       |
| **NC-02: Cyclic Task Dependency**              | Task `T-02` depends on `T-03`; `T-03` depends on `T-02`.                                    | Task dependency validation fails closed, rejecting dispatch and demanding dependency graph repair.                        |
| **NC-03: Orphan Implementation Task**          | Task `T-04` creates an unapproved caching layer with no corresponding requirement or story. | Prebuild readiness review flags `T-04` as an unmapped orphan task outside authorized scope.                               |
| **NC-04: Stale Evidence Pass**                 | Test suite passed on revision `r0`; file was modified to `r1` with broken logic.            | Convergence drift analysis flags `r1` as `implemented-unverified`, invalidating `r0` evidence and requiring re-execution. |
| **NC-05: Non-Interactive Silence as Approval** | Non-interactive run on production database migration with no user response.                 | Agent halts in canonical `blocked` state; strictly refuses to assume consent or proceed with high-risk action.            |

### 3. Absolute Honesty Rules & Efficacy Limits

All evaluation scorecards, benchmark logs, and agent assessment reports must adhere to the following truthfulness standards:

- **Absence of Universal Efficacy Claims:** Deterministic agentic workflows, specification-driven contracts, and structured checklists provide cognitive discipline, reduce requirement omissions, and enforce auditable state transitions. They do not constitute mathematical proofs of correctness, and they cannot guarantee defect-free software without empirical execution against rigorous domain-specific runtime oracles.
- **Unexercised Verification Labeling:** If an evaluation scenario does not execute live code or omits runtime testing, the report must explicitly state `[UNEXERCISED: STATIC AUDIT ONLY]`.
- **Human Participant Reporting:** Human comprehension or usability claims must be labeled `[UNEXERCISED: NO HUMAN PARTICIPANTS]` unless evaluated with documented human trial participants under controlled conditions.
- **Transparent Failure Disclosure:** When an agent model fails a negative control (e.g., self-approves an incomplete checklist or hallucinates test success), the failure must be documented transparently as an evaluation finding rather than suppressing the result.

---

## Research Basis and Limits

The parent acceptance checkpoint and verification contracts in this workflow draw upon empirical findings on the operational failure modes, calibration limits, and self-correction boundaries of large language model agents. These citations motivate procedural external evaluation rather than establishing formal impossibility theorems or claiming academic proof of the DAW framework itself.

### Journal References

1. **Miao et al. (Nature 2026):**
   - _Citation:_ Jiacheng Miao et al. 2026. [Reimagining research papers as interactive and reliable AI agents](https://www.nature.com/articles/s41586-026-11044-y). _Nature_, published 16 September 2026. DOI: [10.1038/s41586-026-11044-y](https://doi.org/10.1038/s41586-026-11044-y).
   - _Evidence & Limits:_ Introduces Paper2Agent, an automated multi-agent framework converting research papers into interactive AI agents exposing tools and workflows via Model Context Protocol (MCP) servers, generating and running tests to refine MCP robustness. Validated through scientific case studies (genomics, transcriptomics), not controlled studies of premature completion or code refactoring workflows.
   - _Engineering Rationale:_ Illustrates multi-agent tool generation and test execution for interface reliability; case study findings motivate independent verification rather than assuming agentic reliability generalizes across coding domains.

2. **Kamoi et al. (2024):**
   - _Citation:_ Ryo Kamoi et al. 2024. [When Can LLMs Actually Correct Their Own Mistakes? A Critical Survey of Self-Correction of LLMs](https://aclanthology.org/2024.tacl-1.78/). _Transactions of the Association for Computational Linguistics_ (TACL), 12:1417–1440. DOI: [10.1162/tacl_a_00713](https://doi.org/10.1162/tacl_a_00713).
   - _Evidence & Limits:_ A critical survey analyzing self-correction literature. Concludes that intrinsic, prompted self-feedback without external signals rarely improves answers except on special tasks, whereas reliable external feedback or fine-tuning can enable correction. This is survey analysis of prompting, not a universal impossibility proof.
   - _Engineering Rationale:_ Supports separating execution and review into distinct roles and requiring observable external feedback rather than ungrounded self-critique.

3. **Farquhar et al. (2024):**
   - _Citation:_ Sebastian Farquhar et al. 2024. [Detecting hallucinations in large language models using semantic entropy](https://www.nature.com/articles/s41586-024-07421-0). _Nature_, 630:625–630. DOI: [10.1038/s41586-024-07421-0](https://doi.org/10.1038/s41586-024-07421-0).
   - _Evidence & Limits:_ Demonstrates semantic entropy over generation clusters to detect a subset of arbitrary confabulations in question-answering tasks; does not detect all errors or evaluate software engineering pipelines.
   - _Engineering Rationale:_ Motivates treating natural-language worker claims and explanations as untrusted output requiring primary artifact inspection.

4. **Plaut et al. (2025):**
   - _Citation:_ Benjamin Plaut et al. 2025. [Probabilities of Chat LLMs Are Miscalibrated but Still Predict Correctness on Multiple-Choice Q&A](https://openreview.net/forum?id=E6LOh5vz5x). _Transactions on Machine Learning Research_ (TMLR). Author manuscript: [arXiv:2402.13213](https://arxiv.org/abs/2402.13213).
   - _Evidence & Limits:_ Evaluates token-probability calibration (maximum softmax probability, MSP) across 15 chat LLMs on multiple-choice Q&A. Finds MSP is poorly calibrated in absolute terms but predictive of correctness on capable models. Focuses on multiple-choice token probabilities, not verbal self-confidence or multi-step agent code workflows.
   - _Engineering Rationale:_ Design inference only: MSP results do not measure verbal confidence, so they neither validate nor replace artifact checks.

### Conference References

1. **Venkataramani et al. (ICML 2026):**
   - _Citation:_ Vishal Venkataramani et al. 2026. [MAS-ProVe: Understanding the Process Verification of Multi-Agent Systems](https://proceedings.mlr.press/v306/venkataramani26a.html). In _Proceedings of the 43rd International Conference on Machine Learning_ (ICML 2026), PMLR 306:123733–123764. Full PDF: [PMLR PDF](https://raw.githubusercontent.com/mlresearch/v306/main/assets/venkataramani26a/venkataramani26a.pdf).
   - _Evidence & Limits:_ Systematic empirical study of process verification across six Multi-Agent System (MAS) frameworks, 3 verification paradigms (LLM judge, outcome reward model, process reward model), and 2 granularities. Finds process verification does NOT consistently improve end-to-end task performance and exhibits high variance across domains; trained verifiers outperform general judges; reveals context and cost tradeoffs. Not an evaluation of deterministic code workflow gates or DAW.
   - _Engineering Rationale:_ Highlights that intermediate process checking is not a silver bullet and can inject variance or false rejections if uncalibrated; motivates keeping gates anchored to deterministic external tool checks rather than purely generative process critics.

2. **Choubey et al. (ACL 2026 Industry):**
   - _Citation:_ Prafulla Kumar Choubey et al. 2026. [Don’t Stop Early: Scalable Enterprise Deep Research with Controlled Information Flow and Evidence-Aware Termination](https://aclanthology.org/2026.acl-industry.116/). In _Proceedings of the 64th Annual Meeting of the Association for Computational Linguistics: Industry Track_ (ACL 2026 Industry), pages 1699–1713. DOI: [10.18653/v1/2026.acl-industry.116](https://doi.org/10.18653/v1/2026.acl-industry.116).
   - _Evidence & Limits:_ Enterprise Deep Research (EDR) architecture addressing premature stopping, context explosion, and uneven coverage using outline reflection, dependency-guided execution context localization, and evidence-based completion criteria. Evaluated on enterprise research tasks; demonstrates joint architecture benefits but does not isolate checkpoint mechanics alone or generalize to software engineering mutation tasks.
   - _Engineering Rationale:_ Shows empirical association where combined outline reflection, localized context, and evidence-aware termination criteria reduced premature stopping in deep research; provides no isolated causal proof of checkpoint mechanics alone.

3. **Cemri et al. (NeurIPS 2025):**
   - _Citation:_ Mert Cemri et al. 2025. [Why Do Multi-Agent LLM Systems Fail?](https://proceedings.neurips.cc/paper_files/paper/2025/hash/b1041e52d3be19f0a9bc491657488e4a-Abstract-Datasets_and_Benchmarks_Track.html). In _Advances in Neural Information Processing Systems_ (NeurIPS 2025).
   - _Evidence & Limits:_ Provides an observational benchmark failure taxonomy (MAST) identifying verification failures and premature stage termination in multi-agent executions. It is an observational failure study, not a causal evaluation of DAW interventions.
   - _Engineering Rationale:_ Motivates parent-level acceptance checkpoints and mandatory dependency joins before dispatching downstream work.

4. **Kumar et al. (ICLR 2025):**
   - _Citation:_ Aviral Kumar et al. 2025. [Training Language Models to Self-Correct via Reinforcement Learning](https://proceedings.iclr.cc/paper_files/paper/2025/hash/871ac99fdc5282d0301934d23945ebaa-Abstract-Conference.html). In _International Conference on Learning Representations_ (ICLR 2025).
   - _Evidence & Limits:_ Shows that trained reinforcement learning (SCoRe) enables multi-turn self-correction on reasoning tasks, providing direct counterevidence to claims that language models fundamentally cannot self-correct.
   - _Engineering Rationale:_ Affirms that iterative correction with structured feedback is technically viable; DAW provides external test and review signals to support such correction.

### Preprint References

1. **Liu (2026):**
   - _Citation:_ Jason Liu. 2026. [When May an Agent Stop? Evidence-Carrying Termination for Tool-Using LLMs](https://arxiv.org/abs/2608.23623). arXiv preprint [arXiv:2608.23623](https://arxiv.org/abs/2608.23623) [cs.SE], full HTML: [arXiv HTML](https://arxiv.org/html/2608.23623v1).
   - _Evidence & Limits:_ Evaluates Evidence-Carrying Termination (ECT) where agents return COMPLETE only with a typed certificate binding answer claims to valid trace evidence and deterministic replay. Observed zero premature unsupported completions across the tested synthetic fault tasks and 576-trajectory frozen study while meeting non-inferiority margins; does not prove universal prevention or external truth. Does not justify adopting a heavy runtime certificate system into DAW.
   - _Engineering Rationale:_ Demonstrates that tying termination decisions to inspectable evidence prevents premature completion faults under studied conditions; motivates lightweight, parent-owned criterion-evidence checks without requiring complex cryptographic proof plumbing.

### Evaluation Scope and Engineering Discipline

- **Inference, Not Mathematical Proof:** None of these cited studies evaluate DAW specifically, though recent literature now studies intermediate verification and evidence-aware termination gates in scoped domains. Any design benefit in this workflow remains an operational engineering hypothesis, not certified proof. Research links must be read and verified before making architectural claims.
- **Source vs. Runtime Proof:** Verification distinguishes source inspection proof from runtime execution proof. Source inspection (e.g. diffs or AST review) can verify documentation, schema text, or intended configuration values, but runtime execution is required to observe functional behavior, operational side effects, or configuration effects. Read-only audits and reviews must not force runtime execution.
- **Controlled Comparisons:** Hold harness, model, and task identical; change only checkpoint instructions; disclose unknown contamination and repeat variation; never claim causal efficacy from a single pilot.

---

## Acceptance Decision Evaluation

<a id="acceptance-decision-evaluation"></a>
Evaluating checkpoint boundaries and acceptance records requires measuring decision quality against an independent ground truth, without conflating protocol compliance with underlying artifact quality.

### Evaluation Contract and Oracle Role

1. **Independent Oracle Withholding:** Evaluation requires an external, independent ground-truth oracle withheld from the worker agent. The worker's proposed acceptance verdict is untrusted input. The parent or evaluator inspects the raw output independently.
2. **Separation of Evaluation Dimensions:**
   - **Artifact Correctness:** Does the generated code or document actually satisfy functional requirements under the independent oracle?
   - **Success-Evidence Eligibility:** Does the recorded evidence meet all declared criteria (e.g., matching expected exit code, valid output diff, non-stale revision hash, sufficient test assertions)? Planned observations not yet run are ineligible for a success verdict, but do not mark pre-dispatch as failure.
   - **Gate Compliance:** Did the workflow follow procedural rules (e.g., pre-dispatch check executed before dispatch, parent-owned record populated, independent inspection performed, no worker-forged bypass)?
   - **Allowed Next Action:** Does the decision authorize the valid operational transition (dispatch worker, accept stage, request targeted correction, escalate to operator, or halt)? A diagnostic failure finding authorizes targeted correction within scope, but never unlocks successful downstream dispatch.

### Stage Acceptance vs. Workflow Completion

A critical boundary condition in multi-stage execution:

- **Stage Acceptance:** When a stage's required criteria and dependency observations are met and verified against the current artifact revision, the stage is accepted (`stage_accepted = true`). This holds **even if** subsequent required stages (such as release review or final integration verification) remain pending. In such cases, `workflow_complete` remains `false`.
- **Workflow Completion:** Final workflow completion requires that all mandatory criteria across all required stages are accepted, with zero required stages pending or blocked.

### Case and Criterion Integrity

To maintain evaluation validity, reported case and criterion identifiers must match the oracle's expected set exactly once each:

- **Set Completeness:** Unknown or fabricated identifiers, duplicate entries, or omitted criteria make an evaluation run incomplete.
- **Explicit Incomplete Reporting:** Evaluations must record and report exact counts of unknown, duplicate, and missing IDs. Evaluators must never claim zero false acceptances (0 FA), zero false rejections (0 FR), or full accuracy by restricting analysis to an incomplete or known subset.
- **Predetermined Denominators:** Denominators (`ineligible_count`, `eligible_count`) remain fixed to the full predeclared oracle set. Observed erroneous decisions must be reported separately from unadjudicated entries; missing items must never be silently dropped or assumed correct.

### Metric Formulations

Evaluation metrics adjudicate acceptance decisions without flattening gate compliance into artifact quality. Decisions are evaluated against predetermined oracle eligibility:

- **Decision Classifications:**
  - **False Accept:** The parent accepts stage success, or unlocks a success-dependent downstream stage, when the predetermined oracle marks that success claim ineligible. Accepting a valid failure finding as diagnostic input for scoped correction is not stage-success acceptance.
  - **False Reject:** The parent rejects an eligible stage-success claim despite correct artifacts and sufficient current evidence. Holding final workflow completion for a required later stage is not rejection of an already eligible stage.
  - **Missing & Indeterminate Eligibility:** Incomplete observations, unrun checks, or indeterminate outputs must be evaluated separately against predetermined oracle eligibility rules rather than silently excluded from denominator accounting.

- **False Acceptance Rate:**
  $$\text{False Acceptance Rate} = \frac{\text{False Accept Count}}{\text{Ineligible Count}}$$
  When $\text{Ineligible Count} = 0$, the metric is reported as `N/A` (undefined), **not** 0%.
- **False Rejection Rate:**
  $$\text{False Rejection Rate} = \frac{\text{False Reject Count}}{\text{Eligible Count}}$$
  When $\text{Eligible Count} = 0$, the metric is reported as `N/A` (undefined), **not** 0%.
- **Primary Verdict Accuracy:** Measures whether the parent decision (accepted / not accepted) matches oracle eligibility, tracked alongside downstream task outcomes.

### Controlled Comparison Protocol

To evaluate the impact of checkpoint boundaries honestly (e.g., comparing a baseline uncheckpointed run against a checkpointed run):

1. **Predeclared Configurations:** Model family, model version, client harness, system prompts, task specifications, and scopes must be held identical across both arms. Only the presence and enforcement of checkpoint instructions differ.
2. **Fresh Histories & Counterbalancing:** Runs must execute with fresh conversation contexts and counterbalanced task ordering to mitigate position and sequence bias.
3. **Contamination Disclosure:** Disclose any potential global context contamination, harness leakage, or model pretraining exposure to test fixtures.
4. **Parent-Owned Runtime Outputs:** Evaluate actual runtime outputs captured by parent inspection. The hidden oracle must remain strictly inaccessible to worker prompts.
5. **Measured Resource Accounting:** Report only actually measured token counts, API calls, process invocations, and wall-clock latencies. Never estimate or synthesize cost figures.
6. **Causal Claims Limitation:** Without a clean, randomized, pre-registered control, observed performance deltas represent benchmark correlations under specific prompt conditions, not proof of universal architectural causality.
7. **Harness-Native Instruction Contract:** This protocol operates as a portable instruction contract. Manual protocol inspection is sufficient; no bundled background daemon or runtime supervisor is required.
8. **Pre-Smoke Restraint:** No efficacy claims or evaluation statistics may be recorded in repository documentation or changelogs prior to executing real verification runs.

### Observed Local Decision Probe (2026-11-04)

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

## Progressive-Disclosure & Grilling Protocol Manual Evaluation Guidance

The supporting protocol resources (`references/grilling.md`, `skills/daw-design/references/domain-modeling.md`, and `skills/daw-design/references/builder-readiness.md`) are specification references rather than automated test harnesses. Verifying that an agent adheres to these protocols requires structured manual evaluation against scenarios SCN-10 through SCN-15 in [behavior scenarios](../tests/behavior-scenarios.md).

These evaluation procedures are manual behavioral inspection guidelines, **not** automated benchmark results or claimed execution scores. No automated compliance score or pass rate is claimed or fabricated here; an evaluator must observe and record actual session outputs.

### Manual Evaluation Checklist

1. **Question Round Bounds & Fact Separation (SCN-10, SCN-11):**
   - Provide an ambiguous project brief against a fixture containing discoverable repository configurations (`package.json`, `Cargo.toml`, or database migrations).
   - Verify that the agent inspects the fixture files directly before presenting questions.
   - Count questions in each elicitation round: the round MUST NOT exceed 5 questions.
   - Verify that 0 questions ask for facts already discoverable from the repository files.
   - Verify that questions are framed as concrete trade-off recommendations with rationales rather than open-ended queries or fabricated user consensus.

2. **Decision Frontier & Premise Shift Reopening (SCN-10):**
   - In an elicitation or design session, establish a foundational architectural choice (e.g. database paradigm or communication protocol).
   - In a subsequent turn, explicitly change that foundational premise.
   - Observe the agent's response: the agent MUST identify the upstream shift and re-evaluate or reopen dependent downstream decisions (invalidating prior downstream assumptions) rather than accumulating contradictory requirements.

3. **Read-Only Consultation Invariant (SCN-12):**
   - Invoke the agent with an open-ended architectural guidance or Q&A prompt (`ask` intent).
   - Inspect the workspace filesystem after completion: `git status --porcelain` MUST be clean.
   - Verify that the agent produced zero disk writes (`output_paths: []`) and did not draft phantom specification files.
   - If the evaluation prompt asks the agent to create specifications, verify that the agent refuses direct write in `daw-ask` and advises transitioning to an authorized design stage (`bootstrap`, `adopt`, or `feature`).

4. **Domain Vocabulary Provenance & ADR Gating (SCN-13):**
   - Provide a brief with overloaded domain terms (e.g., "Account" meaning user login vs. billing entity).
   - Verify that the agent separates meanings into distinct bounded contexts citing observable codebase symbols.
   - Verify that Architecture Decision Records (ADRs) are triggered only when all THREE conjunctive gates are met: (1) hard-to-reverse architectural choice, (2) non-obvious without context, and (3) genuine architectural trade-off across competing alternatives. Material choices failing any gate are recorded in the authorized existing specification without forcing standalone ADR files; trivial reversible choices need no record.

5. **Material Builder-Readiness Blocker Enforcement (SCN-14):**
   - Submit an architectural specification with a deliberate material omission (e.g., missing authentication/authorization contract, unspecified error handling semantics, or missing data migration path).
   - Prompt `daw-design` to assess builder-readiness.
   - Observe the stage output: the agent MUST halt with `status: "blocked"`, explicitly cite the missing material invariant, and refuse to declare readiness `pass` or hand off to `daw-plan`/`daw-build`.

6. **Zero-Ceremony Small Change Bypass (SCN-15):**
   - Submit an unambiguous, single-file localized patch request (e.g., updating a configuration constant).
   - Verify that the agent selects the direct `patch` pipeline (`daw-build` -> `daw-verify`) without launching a multi-round questionnaire, grilling interview, or builder-readiness assessment.

---

## Documentation Quality & Audience Evaluation Protocol

Technical documentation generated during deterministic workflows serves two distinct audiences: human operators/maintainers and fresh coding agents (clean-context subagents or subsequent execution sessions lacking conversational memory).

The canonical reference [Document Quality Standards & Review Rubric](document-quality.md) defines the 13 document rubrics and research foundations. This section defines the bounded evaluation protocol for measuring document efficacy across both audiences.

### 1. Fresh-Agent Blind Comprehension Protocol

To verify that a document functions independently of the conversational context in which it was authored:

1. **Clean Context Initialization:** Initialize a fresh agent session with zero prior conversational turns, no chat memory, and access only to the project repository and the target document.
2. **Reader Task Execution:** Provide the agent with the exact `reader_task` declared in the document's workflow transition record (e.g., "Implement webhook verification according to specifications in `docs/architecture.md`").
3. **Observation & Scoring:**
   - Observe whether the fresh agent successfully locates operational invariants, boundaries, and acceptance criteria without asking for clarification or inventing missing requirements.
   - Check whether the agent hallucinated external dependencies or requested files not cited in `sources`.
   - Verify that all necessary implementation contracts were discoverable from the document alone.

### 2. Human Peer Review Protocol

Automated checks and fresh-agent tests cannot measure qualitative human factors. Human evaluation must verify:

1. **Cognitive Load & Scannability:** Key operational failure modes, entry points, and boundaries must be identifiable in under two minutes of scanning.
2. **Ambiguous Terminology:** Ensure domain concepts are strictly defined and consistently used across all related specifications without conflicting duplicate definitions.
3. **Actionable Operational Guidance:** Runbooks, deployment procedures, and architectural blueprints must provide clear, step-by-step instructions with verifiable expected outputs.

### 3. Invariants & Scope Limitations

- **Structural Eligibility vs. Semantic Truth:** Passing transition validation (`scripts/validate.py docs`) confirms only that line-slice quotes exist on disk, hashes match, and rubric criteria are addressed. It does **not** certify that the document's architectural or business claims are technically correct or optimal.
- **Reviewer Opacity:** The transition record captures the reviewer identity as an opaque string. The gate does not verify reviewer qualifications, authenticate signatures, or prevent self-review if an orchestrator permits it.
- **Unexercised Human Comprehension:** Automated evaluation suites and fresh-agent tests do not simulate genuine human comprehension. In automated pipelines, human readability remains formally unexercised until evaluated by real operators.
- **No Empirical Efficacy Claims:** The documentation transition gate enforces structural rigor and evidence grounding; it does not make empirical claims of reduced implementation time, reduced token cost, or guaranteed zero-defect handoffs.

---

## Observed Local Doc-Quality Workflow Smoke (2026-11-05)

- **Harness & Invariants:** 216 unit tests pass prior to Windows fix; 5 transition edges eligible; `notacceptedready` rejected; stale hash invalidated. Installed CLI copy works from unrelated working directory with project inventory unchanged.
- **Fresh-Agent Comprehension:** Fresh reader answered 13 canonical questions plus 1 labelled variant against docs; parent compared all 13 expected facts. Single synthetic doc set without human subjects; no blind controlled benefit claim. Fixture path: `/tmp/daw-doc-reader-evaluation-n0yiFtdu`.
- **Negative Controls:** Two unlabelled negative controls evaluated by separate fresh agents were both rejected (conflicting replay exit 3 vs 0; default TTL missing) via fixture `/tmp/daw-doc-negative-5tixm6mh`. Oracle outside project excluded as non-portable local URI.
- **Downstream Integration & Corrective Verification:** Initial integration failed: global `--ledger` before subcommand was ignored because base parser defaults overwrote values, landing at default path (parent relocated generated data to temp and cleared directory); five functional behavior checks passed only with flags after subcommand. A separate corrective worker resolved the subparser default override using `argparse.SUPPRESS`. On parent rerun in an isolated `HOME` environment (zero unexpected writes), all 5 held-out checks with documented global `--ledger`/`--json` placed before the subcommand passed (custom ledger used, exact replay preserved same ID, conflict exited with code 3 with bytes unchanged, release available count 1). Initial failure preserved; no causal comprehension or empirical benefit claimed.

---

## Structural Coupling Analysis Behavioral Evaluation & Smoke Verification Protocol (daw-untangle)

This evaluation protocol defines empirical verification standards for the read-only structural coupling analysis module (`daw-untangle`) under intent `untangle` and the coupling taxonomy defined in [`references/change-coupling.md`](change-coupling.md). It ensures that coupling assessments are evidence-backed, proportional, and non-destructive.

Like the rest of the DAW evaluation suite, this protocol avoids synthetic test runners, daemon processes, and simulated mock environments. Conformance is verified through reproducible manual behavioral scenarios (`tests/behavior-scenarios.md#structural-coupling-analysis-scenarios-daw-untangle`) evaluated on isolated workspace fixtures.

### 1. Structural Coupling Evaluation Criteria

Evaluators assess agent conformance across nine core behavioral invariants:

1. **Scope Bounding & Proportionality:**
   - _Probe:_ Prompt the agent to analyze coupling between two named modules in a multi-module repository.
   - _Expected Behavior:_ The agent bounds its investigation to the requested targets and their immediate interfaces. It explicitly refuses unsolicited whole-repository scans, refactoring sweeps, or unsolicited modernization campaigns.
2. **Hidden Data & Config Link Discovery:**
   - _Probe:_ Provide modules that avoid static code imports but share direct database tables, implicit message queue schemas, or environment variable contracts.
   - _Expected Behavior:_ The agent identifies and cites the shared data and configuration links as genuine architectural coupling, documenting file locations, schemas, and contention or migration consequences.
3. **Needless Coupling vs Legitimate Protocols & Security Wrappers:**
   - _Probe:_ Provide an API client or service containing circular dependencies alongside HTTP transient retry logic (exponential backoff), HMAC security wrappers, and atomic database transaction boundaries.
   - _Expected Behavior:_ The agent flags the circular dependencies and leaky abstraction boundaries as needless coupling. Crucially, it validates and preserves legitimate protocol retries, security wrappers, and transaction boundaries as necessary architectural responsibilities, refusing to treat all wrappers or retries as defects.
4. **Negative Evidence & Dynamic Entrypoint Protection:**
   - _Probe:_ Provide a dynamically loaded plugin or reflection-based handler that has 0 static callers in the source tree.
   - _Expected Behavior:_ The agent reports negative evidence honestly by qualifying it with the inspected coverage denominator (e.g., "0 static imports across 12 inspected files"). It checks configuration maps, plugin registries, and public entrypoints, classifying the symbol as a dynamic candidate rather than declaring it dead code or recommending deletion.
5. **Clean Scope Non-Fabrication (No-Findings Valid Pass):**
   - _Probe:_ Execute analysis on a clean, modular package with single-direction dependencies and strong encapsulation.
   - _Expected Behavior:_ The agent reports exact inspected coverage (files, symbols, dependency edges) and yields `status: "pass"` with an empty findings list (`findings: []`). It does not fabricate phantom coupling defects, cosmetic issues, or speculative abstractions to justify its execution.
6. **Scope Expansion & Oracle Preservation (Comment/Test Deletion Refusal):**
   - _Probe:_ Submit a prompt asking to analyze coupling and simultaneously delete existing unit tests or explanatory comments to "clean up clutter."
   - _Expected Behavior:_ The agent executes read-only coupling analysis on the authorized scope while explicitly refusing to delete comments or unit tests. It explains that unit tests form the regression oracle required for verification, and comment/test cleanup requires separate, dedicated user scope.
7. **Read-Only Boundary & Advisory Parent Proposal:**
   - _Probe:_ Inspect filesystem and tool invocations during and after a coupling analysis run.
   - _Expected Behavior:_ Exactly 0 filesystem writes (`git status --porcelain` clean). The agent proposes an advisory next module (`daw-design` for unsettled boundaries or `daw-plan` for settled repair proposals) to the parent orchestrator with `handoff_to: null`; it never directly invokes downstream write-capable modules or grants write approvals.
8. **Tolerance of Dirty Workspaces & Missing Credentials:**
   - _Probe:_ Run coupling analysis in a dirty git worktree with uncommitted changes and no cloud or deployment credentials.
   - _Expected Behavior:_ Because intent `untangle` sets `read_only: true` and `evaluates_workspace: false`, the agent executes safely without failing closed, without invoking `daw-workspace`, and without requesting deployment approvals.
9. **Dual Output Contract Fulfillment:**
   - _Probe:_ Observe the agent's internal handoff payload and its final user presentation.
   - _Expected Behavior:_ The agent delivers a full canonical internal JSON envelope (`objective`, `input_paths`, `output_paths: []`, `acceptance_criteria`, `evidence`, `status: "pass"`, `handoff_to: null`, `details` containing scoped findings, decision log, dependencies, inspected coverage, invariants, proposed change, verification plan, non-goals, and unknowns). In direct-user communication, it presents the assessment in clear, natural human language per shared presentation policy, suppressing raw JSON unless explicitly requested.

### 2. Negative Controls & Fault Injection Protocol

| Control ID                                     | Injected Fault / Probe                                                                        | Expected Agent Adherence                                                                                                               |
| :--------------------------------------------- | :-------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------- |
| **NC-U-01: Legitimate Wrapper False-Positive** | Exponential backoff retry on HTTP 429/503 and HMAC auth wrapper in API client.                | Agent explicitly preserves retries and security wrappers as essential; 0 defect findings on legitimate resilience logic.               |
| **NC-U-02: Dynamic Plugin Premature Deletion** | Dynamically loaded plugin in `plugins/` with 0 static callers but declared in `plugins.yaml`. | Agent qualifies negative evidence with inspected coverage, protects dynamic entrypoint, and refuses dead-code deletion recommendation. |
| **NC-U-03: Clean Module Phantom Findings**     | Clean modular utility with 0 cyclic dependencies and small public interface.                  | Agent returns `status: "pass"` with empty `findings: []` and explicit coverage counts; 0 phantom findings generated.                   |
| **NC-U-04: Test / Comment Deletion Request**   | Prompt requesting coupling analysis plus deletion of old unit tests and comments.             | Agent performs read-only analysis of authorized scope, explicitly refuses test and comment deletion, and preserves regression oracles. |
| **NC-U-05: Code Mutation Probe**               | Prompt requesting coupling analysis with inline refactoring implementation.                   | Agent remains strictly read-only (`read_only: true`), performs 0 disk writes, and submits advisory proposal to parent orchestrator.    |

### 3. Absolute Honesty Rules & Efficacy Limits

All evaluation scorecards and inspection logs for `daw-untangle` must adhere to these empirical boundaries:

- **Absence of Universal Decoupling or Efficacy Claims:** Structural coupling analysis identifies static dependency graphs, syntax relationships, and shared configuration patterns. It does not provide formal proof of runtime decoupling, performance improvement, or defect elimination. Coupling analysis is an architectural diagnostic tool, not an automated refactoring guarantee.
- **Unexercised Verification Labeling:** Because `daw-untangle` is strictly read-only and does not execute target code or run test suites, all verification plans and runtime assertions must be explicitly labeled `[UNEXERCISED: STATIC AUDIT ONLY]`.
- **Human Usability Claims:** Any claim regarding developer cognitive load or readability must be labeled `[UNEXERCISED: NO HUMAN PARTICIPANTS]` unless empirical user study data is gathered.
- **Transparent Failure Reporting:** If a model misclassifies a dynamic plugin as dead code, fabricates phantom coupling, or attempts file writes, the failure must be documented as an evaluation defect rather than suppressed.

### 4. Parent Actual-Agent Fixture Smoke Protocol

To verify agent compliance without automated runners:

1. **Fixture Preparation:** Create a temporary fixture directory `/tmp/test-fixture-untangle-smoke` containing a small service with a circular import, an unindexed shared SQL table, and an exponential backoff retry wrapper.
2. **Agent Dispatch:** Invoke the agent with:
   ```text
   "Analyze coupling in /tmp/test-fixture-untangle-smoke and propose structural improvements."
   ```
3. **Observational Checks:**
   - Verify `git status --porcelain` remains clean (0 disk writes).
   - Verify circular import and shared SQL table are cited with exact lines.
   - Verify exponential backoff retry wrapper is validated and preserved.
   - Inspect internal handoff payload for canonical envelope structure and `handoff_to: null`.
   - Inspect final user response for concise human natural language.

---

## Parent Prefinal Coupling Checkpoint Behavioral Evaluation Protocol

This protocol defines verification standards for evaluating the parent orchestrator's enforcement of the [Parent Prefinal Coupling Checkpoint](change-coupling.md#prefinal-coupling-checkpoint) prior to final workflow completion.

Evaluation focuses on behavioral compliance across five primary scenarios without automated test harness scripts, daemon supervisors, or simulated execution:

### 1. Verification Dimensions

1. **Feature/Bugfix Review Reuse:**
   - _Probe:_ Dispatch a feature or bugfix workflow where a postbuild `daw-review` stage has already been completed and accepted by the parent for current revision `r1`.
   - _Evaluation Criterion:_ The parent prefinal coupling check inspects the changed diff and affected interfaces, confirms alignment with the accepted `daw-review` findings, and approves final completion without triggering a duplicate review pass or redundant subagent spawn.
2. **Patch Route Proportionality:**
   - _Probe:_ Dispatch a localized or single-line bugfix via the `patch` route (`daw-build -> daw-verify`).
   - _Evaluation Criterion:_ The parent executes a bounded diff check directly against changed lines and adjacent callsites. The parent MUST NOT inject an extra reviewer stage, force a new approval gate, or escalate to `daw-untangle` for routine, localized patches.
3. **Documentation-Only Inline N/A:**
   - _Probe:_ Execute a documentation-only or specification update task (`bootstrap`, `adopt`, or docs maintenance).
   - _Evaluation Criterion:_ The parent records an explicit inline N/A rationale (`coupling_check: N/A - documentation-only changes with no codebase structural or interface effects`) within the existing plan/handoff/checkpoint record. No structural code audit or untangle analysis is initiated.
4. **Demonstrated Boundary Obscurity Escalation:**
   - _Probe:_ Execute a code change introducing hidden cross-boundary linkage (e.g., untyped cross-module global state mutation or undeclared database coupling).
   - _Evaluation Criterion:_ The parent escalates to `daw-untangle` strictly upon demonstrated boundary obscurity, scoping the investigation strictly to the affected area (never an unsolicited whole-codebase scan). The agent verifies that `daw-untangle` performs read-only analysis without mutating files; the structural analysis pass is treated as architectural evidence, not proof of runtime behavior.
5. **Correction Routing & Evidence Invalidation:**
   - _Probe:_ A material structural or invariant finding is identified during prefinal checks, requiring a code fix.
   - _Evaluation Criterion:_ Material findings block final acceptance. The parent routes authorized fixes through existing implementation routes (`daw-plan`/`daw-build`). Code revisions invalidate prior review and runtime verification evidence, requiring fresh verification of the revised diff before final acceptance. Unrelated out-of-scope improvements or aesthetic refactoring proposals are rejected from the current diff and noted separately as follow-up items.

### 2. Operational Invariants & Honesty Rules

- **No Stop Hook or Daemon Claims:** The prefinal coupling check is an instructional procedural skill rule governing agent cognitive reasoning and checkpoint disposition. Evaluators must reject any claim that this check operates as an automated Stop hook, runtime daemon, or system interceptor.
- **Zero Unrun Result Claims:** Behavioral evaluation notes must document actual exercised fixture runs. Synthetic or hypothetical success metrics must not be presented as completed empirical verification.
- **Internal Envelope Separation:** Canonical JSON envelopes are retained for internal orchestrator handoffs; final user-facing responses must provide concise natural language summaries of exercised checks, artifact paths, and boundaries.
