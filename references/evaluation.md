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

| Case | Task | Deterministic artifact checks | Human review still needed |
| --- | --- | --- | --- |
| `patch` | Fix addition in an integer calculator without changing its CLI or adding specifications/dependencies | Four public function cases, actual CLI output, bounded file changes | Meaningful regression strategy, truthful reported evidence, appropriate scope |
| `review` | Review a cache that returns one customer's report to another customer; no edits or script execution | Workspace bytes, modes, mtimes, links, and directory entries remain unchanged | Concrete requirement/confidentiality reasoning, line evidence, correct limited-triage status, no hidden execution |
| `cli` | Verify missing arguments exit 2 and valid suite inspection exits 0 | Unchanged workspace; grader independently runs both real CLI commands | Agent declared expectations first, actually executed checks, and correctly reported expected rejection |

`--case` selects one case or `all`. Fixture definitions and graders live in the runner so the small suite can be inspected together. Grader subprocesses are bounded to ten seconds and retain their own stdout/stderr. They do not depend on tests written by the agent. Unexpected output, failed imports, syntax errors, nonzero test exits, or a grader error fail the relevant check.

For `skill` mode, each workspace receives the complete supported distribution at `.agents/skills/deterministic-agentic-workflow/`: the root skill, README, AGENTS contract, MIT LICENSE, VERSION, all eight modules, scripts, references, templates, tests, docs, and optional agent UI metadata. The copied payload matches the installer; Git metadata and caches are excluded. The prompt explicitly invokes that installed copy. For `bare` mode, patch/review fixtures contain no workspace-local DAW installation; the CLI case receives a tool copy under `tools/daw/`, outside the conventional skills directory. Each case, mode, and repetition uses a fresh directory.

`both` is a useful control, but it is not full isolation from the host. The agent inherits your environment, home configuration, credentials, global skills, and client hooks. A clean control requires a caller-provided clean harness/home/configuration without globally installed DAW instructions. Record those conditions in `--agent-label` and the human review. The runner does not infer a client's version or model from process output.

## Evidence and interpretation

Each run directory contains `metadata.json`, `prompt.md`, `workspace/`, `before.json`, `after.json`, `agent.stdout.txt`, `agent.stderr.txt`, grader output files, and `result.json`. Setup or observation failures may leave only the artifacts collected before that failure. `summary.json` combines runs and records the configured argv and supplied client/model label. The fixture files remain available for inspection.

Run metadata and results include the suite VERSION, manifest SHA-256, and a stable SHA-256 over sorted distributable file paths and their content hashes. The fingerprint excludes Git metadata and caches, and does not depend on modification times or a Git command. Skill/CLI runs identify the actual staged bundle before the agent starts; bare patch/review runs identify the source suite used as a comparison reference. Matching version labels alone do not imply matching instruction bytes.

Result statuses distinguish `artifact_checks_passed`, `artifact_checks_failed`, `agent_failed`, `agent_timeout`, and `runner_failed` (fixture or observation failure). Exit 0 means only that every configured agent process exited 0 and the deterministic artifact checks passed. Exit 1 records a process, runner, or artifact-check failure; exit 2 rejects invalid invocation or output-directory setup.

Every result retains `human_review.status: "ungraded"`. Snapshot preservation alone does not establish a useful review, and a grader's CLI probe does not establish that the agent ran or understood it. Inspect the retained transcript and mark reasoning, evidence integrity, and instruction adherence separately. Do not call these results a completed benchmark, peer-repository parity, or efficacy certification until that review and the actual runs have occurred.

`tests/test_evaluate.py` uses fake local adapters to test process execution, literal argv handling, output retention, failures, timeouts, and artifact graders. Those tests establish runner plumbing; they are not real-agent behavioral evidence. The broader manual scenarios remain in `tests/behavior-scenarios.md` and are not all automated by this runner.
