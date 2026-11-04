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
- **Grading protocol consistency and JSONL completeness**: Acceptance scripts stream JSONL check objects (`check`, `status` in `pass` or `fail`, `detail`). The runner enforces strict fail-closed protocol consistency: timeouts, unhandled crashes, duplicate check names, non-JSON output, and inconsistent exit codes (such as exit 1 when all emitted checks passed) are recorded as `grading_failed` with `pass_rate: 0.0`. If a custom grader exits with code 1 immediately upon its first failure without executing remaining checks, newline-delimited streaming cannot independently discern whether remaining checks were intentionally omitted or aborted; full check enumeration requires graders to run all checks or emit explicit completion markers.
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
