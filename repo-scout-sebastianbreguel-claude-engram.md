# Repo Scout — sebastianbreguel/claude-engram

> **Scope note.** This is a **self-scout**: the repo is the user's own pre-launch project (created 2026-04-13, public, 2 stars, 0 forks, no external PRs to date). Treated as a gap analysis for what to ship before/after launch, not as a third-party contribution map. Small-repo fallback applied: direction inferred from owner commits, README, docs, plugin manifest, and one open issue.

## 0. Gate Check

| Gate | State |
|---|---|
| `CONTRIBUTING.md` | **missing** |
| `CLA` | none required |
| `CODEOWNERS` | **missing** |
| `.github/PULL_REQUEST_TEMPLATE.md` | **missing** |
| `LICENSE` | MIT (declared in `plugin.json`, not yet a top-level file) |
| CI gates | `ruff check .`, `ruff format --check .`, `uv run pytest -q` (single workflow `.github/workflows/test.yml`) |

> Pre-launch implication: every "external contributions" gap below is a future blocker, not a today blocker.

## 1. Repo Shape

- **Language**: Python (>=3.11, `uv`-only), one JS file (`demo/render-gifs.mjs`).
- **Build/format**: `ruff` (line 140, double quotes), `ty` typecheck (per CLAUDE.md), `pre-commit run --all-files`.
- **Tests**: `pytest`, 106 tests passing per session context.
- **Architecture (per `docs/architecture.md` + plugin.json)**: single `tools/engram.py` entrypoint orchestrating hooks (SessionStart, PreCompact, UserPromptSubmit) backed by `tools/memcapture.py` (SQLite + FTS5), `tools/memdoctor.py` (friction-signal detector), `tools/mempatterns.py` (Obsidian wiki).
- **Data plane**: `~/.claude/memory.db` (PRAGMA user_version=2, downgrade-refusal landed pre-launch), `~/.claude/patterns/`, `~/.claude/engram/executive/<cwd-slug>.md` (+ `.prev` rotation).
- **LLM**: all background calls go through `claude --print --model claude-sonnet-4-6` (no external API).

### Recent activity (last ~14 days)

40+ commits since 2026-04-13. Main themes:

1. **Pre-launch hardening** (top of stack): `49f86e7` cache rotation + schema downgrade-refusal + plugin.json, `5dcdde6` CI/perf/dedupe/eval harness, `66489e3` ruff in dev deps for CI.
2. **Friction-signal pipeline**: memdoctor signals (`error-loop`, `correction-heavy`, `keep-going-loop`, `rapid-corrections`, `restart-cluster`) wired into SessionStart banner + executive summary.
3. **Latency wins**: `68c2529` 8 perf wins on SessionStart + UserPromptSubmit hot paths.
4. **Demo polish**: 7 hero animation iterations (`f9aa70e`, `caa2ff7`, `1857341` …) — currently in scale-beat.html redesign per session context.
5. **CLI surface**: `version`/`verify-install`/`forget --expired`/`forget --project`/`patterns --report`/`doctor --propose`/`self-check`/`usage`.

## 2. Code Indexing (graph + serena)

Graph built (full rebuild, postprocess=full): **14 files, 349 nodes, 3483 edges, 19 flows, 3 communities, 0 cross-community edges**.

> Note: `get_hub_nodes_tool`, `get_bridge_nodes_tool`, `get_knowledge_gaps_tool`, `get_surprising_connections_tool` errored on this repo (`'NoneType' object has no attribute 'resolve'`) — likely a code-review-graph postprocessor edge case on Python-only repos with file-based communities. Macro picture below derived from the tools that did run.

### 2.1 Communities

| ID | Name | Size | Cohesion | Dominant lang |
|---|---|---|---|---|
| 2 | tests-session | 165 | 0.124 | python |
| 3 | tools-detect | 155 | 0.165 | python |
| 1 | demo-wait | 12 | 0.208 | javascript |

Zero cross-community edges → tests don't import demo, tools don't import tests at module level (good encapsulation; cohesion is low because file-based communities aren't semantic clusters).

### 2.2 Top flows by criticality

1. `_verify_install` (0.485) — repo↔install drift detector
2. `signals_for_executive` (0.457, 22 nodes) — friction-signal injection into executive cache
3. `signals_banner_line` (0.457, 22 nodes) — friction-signal injection into SessionStart banner
4. `_on_session_start` (0.443) — banner builder, ambient-cost budget, zero-latency path
5. Multiple `main`s (0.43, 32–41 nodes) — CLI dispatch in `engram.py`, `memcapture.py`, `memdoctor.py`, `mempatterns.py`
6. `_run_llm` (0.37) — fire-and-forget Sonnet pass

### 2.3 Hot files (>=60 lines flagged)

| File / class | Lines | Note |
|---|---|---|
| `tools/memcapture.py` | 1319 | hosts `MemoryDB` (700-line class), `TranscriptParser`, parsers, CLI |
| `tools/engram.py` | 1241 | unified CLI + hook orchestrator, `_on_session_start`/`_on_executive`/`_on_precompact` etc. |
| `tools/memdoctor.py` | 744 | friction signal detectors + `propose_memories` |
| `tools/mempatterns.py` | 609 | `WikiWriter` + `PatternDetector` + `PatternsOrchestrator` |
| `MemoryDB` | 700 | god class: connect/migrate/CRUD/search/banner/inject/cleanup/snapshots — splits along clear seams |
| `TranscriptParser` | 164 | OK boundary |
| `PatternsOrchestrator` | 226 | OK boundary |

Two structural risks worth naming:
- `MemoryDB` (700 LOC, 30+ methods): mixes schema (`_create_tables`/`_migrate`), capture (`save_session`/`upsert_memory`), retrieval (`search`/`stats`/`recent_sessions`), banner/inject (`build_banner`/`inject_context`/`_format_snapshot`), and lifecycle (`cleanup_ephemeral`/`forget_*`/`close`). A natural split: `MemoryStore` (schema+CRUD) + `MemoryReader` (banner/inject/snapshot) + `MemoryJanitor` (cleanup/forget).
- `engram.py` 1241 lines as "single entrypoint" is intentional per `CLAUDE.md`, but 30+ private `_on_*` / `_run_*` handlers in one module makes hook-flow tracing harder than it needs to be.

## 3. GitHub Intelligence

| Signal | Count |
|---|---|
| PRs total (all states) | 3 |
| PRs by external contributors | 0 |
| Issues total (all states) | 1 |
| External issues | 0 |
| Forks | 0 |
| Stars | 2 |

**The only open issue** (#3, `enhancement`, by owner): *"executive cache: reorder rotate/write so cache stays present if tmp write fails"*. Already covered by tests `test_executive_cache_rotates_to_prev`, `test_executive_cache_survives_tmp_write_failure`, `test_executive_cache_tmp_includes_pid` — verify whether the in-code fix landed and the issue is just stale.

PR sizes range from +1/-1 to +1129/-77 — no review history (all self-merged).

## 4. Contribution Profile

> External-PR merge rate: **N/A** (zero external PRs). Profile reflects owner's own discipline.

**Owner style**:
- Atomic commits with prefix tags (`fix:`, `feat:`, `chore:`, `docs:`, `refactor:`, `perf:`, `cleanup:`).
- Pre-launch trims tend to be batch PRs (#4 = 1129/77 across 21 files).
- Prefers `uv` over `pip`, classes for stateful logic (per CLAUDE.md), `str | None` over `Optional`.
- Tests: real DB integration over mocks (per session context). `pytest -q` is the gate.
- Lint: `ruff check + format --check`, with per-file E501 ignores for `engram.py`/`memcapture.py`/`test_e2e.py` (long-line-tolerant for prompts, SQL, formatted output).

**What gets merged**: hardening (cache atomicity, schema versioning), latency wins, friction-signal additions to memdoctor, demo polish.
**What's avoided**: big abstraction passes (DISPATCH dict refactor explicitly dropped per memory `project_pending_work.md`), feature-flag/backwards-compat shims, half-implementations.

**Implicit standards inferred from diffs**:
- Subagents ONLY for 3+ parallel research / pre-merge / >30 min jobs (per CLAUDE.md token-discipline rule).
- Sonnet model for all LLM calls (`claude --print --model claude-sonnet-4-6`).
- No mock LLM beyond `claude --print` shimming in tests.
- Banner output: `systemMessage` (visible) + `hookSpecificOutput.additionalContext` (invisible). User-facing labels say "memories" not "prefs".

## 5. Project Interest Map

**Direction (per README + plugin.json + memory)**: ship a Claude Code plugin that gives persistent memory at ~350 ambient tokens, no Docker / no API keys / no MCP, distributed via `/plugin install claude-engram@…`. Differentiation table in README pits it against claude-mem / OpenMemory / cortex on token cost + runtime simplicity.

**Hot zones**:
- `tools/engram.py` SessionStart hot path + executive summary cache (top criticality flows). Recently churned: latency wins, signal banner, atomic write.
- `tools/memdoctor.py` signal detection + `--propose` flag for LLM-drafted feedback memories.
- `demo/` HTMLs (current visible focus per session context: scale-beat.html vertical project→memory layout).

**Pain points (from owner memories + commits)**:
- Friction loops (correction-heavy, error-loop, keep-going-loop) detected and surfaced — meaning the owner has felt these and wants them visible.
- Schema migrations: `LATEST_SCHEMA_VERSION=2`, downgrade-refusal landed pre-launch — implies fear of corrupting installs across versions.
- `executive cache rotates to .prev`: rotation safety net implies prior data-loss scare.

**Neglected but needed**:
- No `CONTRIBUTING.md` / no PR template / no `LICENSE` file at repo root → blocks any external contribution path post-launch.
- No `CHANGELOG.md` (despite `chore: pre-launch round 2` etc. — version is still `0.1.0`).
- No marketplace verification (search-friendly description, screenshots, `keywords` arr OK in plugin.json).
- `eval/` exists (`eval_corrections.py`) but is a one-shot harness, not in CI.
- Two marginal items skipped per `project_pending_work.md` (#5 double DB open in SessionStart, #9 seek-from-end in `_extract_chunk`).
- Issue #3 (executive cache atomic write) — verify already-shipped, close.

**Work in progress (open PRs)**: none.

## 6. Opportunity Table

Ranked by combined score `(Impact × Merge Score) / Effort`. "Merge Score" here = self-merge confidence (would the owner ship this if proposed today). Impact is on user-visible quality, ambient cost, or post-launch readiness.

| # | Feature/Fix | Reason | Impact | Effort | Lines | Flows touched | Anchor files | E2E test plan (summary) | Merge Score |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Verify + close issue #3 (executive cache atomic write) | Tests already cover rotate/tmp-fail/pid-in-tmp; just confirm code matches and close | High | XS | <20 | `_on_executive`, `signals_for_executive` | `tools/engram.py::_on_executive`, `tools/engram.py::_executive_cache_path` | Pre: clear `~/.claude/engram/executive/`. Trigger: simulate tmp write failure (monkeypatch `Path.write_text` to raise). Expect: `<cwd>.md` still present at original content; `.prev` only rotates on success. Regression: `_on_session_start` still emits 3-bullet banner. Tooling: extend existing `test_executive_cache_*` in `tests/test_engram_cli.py`. Manual: `uv run pytest tests/test_engram_cli.py -k executive_cache`. | 95 |
| 2 | Add `LICENSE` file + `CHANGELOG.md` at repo root | plugin.json declares MIT but no top-level LICENSE; pre-launch sanity for marketplace + GitHub auto-detection | High | XS | ~30 | none | `LICENSE`, `CHANGELOG.md` | Pre: none. Trigger: `git log --oneline | head -1`, `gh repo view --json licenseInfo` after push. Expect: GitHub UI shows MIT badge; `CHANGELOG.md` parses as markdown. Regression: README + plugin.json licence claims align. Tooling: visual + `gh repo view`. Manual: `gh api repos/sebastianbreguel/claude-engram --jq .license`. | 90 |
| 3 | Add minimal `CONTRIBUTING.md` + `PULL_REQUEST_TEMPLATE.md` | Post-launch unblocks external PRs; codifies `uv` / `ruff` / `pytest` / "no Co-Authored-By" rules from CLAUDE.md | High | S | ~80 | none | `.github/PULL_REQUEST_TEMPLATE.md`, `CONTRIBUTING.md` | Pre: none. Trigger: open a dummy PR. Expect: template body pre-fills with "Summary / Test plan" headers. Regression: existing CI still green. Tooling: visual on PR creation page. Manual: `gh pr create --draft -t "test" -b "" --head test-branch`. | 88 |
| 4 | Wire `eval_corrections.py` into CI as a non-blocking job | Eval harness exists but isn't run; precision tracking is a launch story for the README | Medium | S | ~40 | `eval` flow | `.github/workflows/test.yml`, `tools/eval_corrections.py` | Pre: ensure `eval/` fixtures committed. Trigger: push branch. Expect: new GH Actions job `eval-corrections` runs `uv run python tools/eval_corrections.py score --json` and uploads artifact. Regression: `test` job still passes; eval job is `continue-on-error: true` initially. Tooling: GitHub Actions UI + `gh run view`. Manual: `act -j eval-corrections` or `uv run python tools/eval_corrections.py score`. | 80 |
| 5 | Split `MemoryDB` into `MemoryStore` / `MemoryReader` / `MemoryJanitor` | 700-line god class mixes schema + CRUD + retrieval + banner + cleanup; raises bar for future migrations | Medium | M | ~300 (move only) | `_on_session_start`, `signals_for_executive`, `_on_precompact` | `tools/memcapture.py::MemoryDB` | Pre: 106 tests baseline green. Trigger: refactor methods into 3 classes preserving public API surface (or facade for backward compat). Expect: every existing `test_engram_cli.py` / `test_e2e.py` test stays green; no signature change in `_on_*` callers. Regression: hooks JSON unchanged, banner output byte-identical. Tooling: `uv run pytest -q`, `uv run ruff check .`, `uv run pre-commit run --all-files`. Manual: `uv run ~/.claude/tools/engram.py stats` + open new Claude session and confirm 3-bullet banner unchanged. | 60 |
| 6 | Single shared SQLite connection in SessionStart (memory `pending #5`) | `_on_session_start` opens DB twice; latency win on the visible-ambient hot path | Medium | S | ~50 | `_on_session_start`, `signals_for_executive`, `signals_banner_line` | `tools/engram.py::_on_session_start`, `tools/memcapture.py::MemoryDB.__init__` | Pre: 106 tests green. Trigger: thread one `MemoryDB` instance through `_on_session_start` → banner build + signals injection. Expect: same JSON output as current; one fewer `sqlite3.connect` call (verify with `strace`/`opensnoop` or counter monkeypatch). Regression: `test_session_start_*` suite passes; `test_session_start_surfaces_schema_downgrade_error` still triggers. Tooling: `uv run pytest tests/test_engram_cli.py -k session_start`. Manual: time `uv run ~/.claude/tools/engram.py on-session-start --transcript-path /dev/null` before/after; expect ≥10ms drop on cold cache. | 75 |
| 7 | Seek-from-end in `_extract_chunk` (memory `pending #9`) | Avoids reading full JSONL files when transcript is large; latency win for long sessions | Low | S | ~60 | `_extract_chunk`, `_read_tail_lines` | `tools/engram.py::_extract_chunk`, `tools/engram.py::_read_tail_lines` | Pre: existing `test_extract_chunk_keeps_recency_and_salience` + `test_read_tail_lines_skips_early_content` baseline. Trigger: build a 50MB synthetic JSONL fixture, call `_extract_chunk`. Expect: byte read count ≤2MB (verify via `os.read` patch); top-K turns identical to current implementation. Regression: existing chunk-test assertions stable. Tooling: extend `tests/test_engram_cli.py`. Manual: `uv run python -c "from engram import _extract_chunk; ..."` with timer. | 65 |
| 8 | Marketplace polish: hero screenshot in plugin.json + README badges | Pre-launch surface for plugin discovery; cheap social proof | Medium | XS | ~15 | none | `.claude-plugin/plugin.json`, `README.md` | Pre: working demo GIF. Trigger: add `screenshots` array to `plugin.json` if schema supports; otherwise add CI-status + license badges to README. Expect: `gh repo view sebastianbreguel/claude-engram` shows badges; plugin marketplace listing has hero image. Regression: README rendering unchanged elsewhere. Tooling: visual GitHub render. Manual: `gh markdown-preview README.md` or push to test branch + visit. | 70 |
| 9 | `engram doctor --json` flag for tooling/CI integration | Friction signals are visible in banner but not consumable programmatically; downstream dashboards / hooks can act on them | Medium | S | ~70 | `_print_summary`, `_print_rules`, `signals_for_executive` | `tools/memdoctor.py::run`, `tools/memdoctor.py::_print_summary` | Pre: existing memdoctor tests baseline. Trigger: `uv run python tools/memdoctor.py --json --per-project`. Expect: stdout is single JSON object with `signals: [...]`, `rules: {...}`, `meta: {...}`; non-zero exit if any high-severity signal. Regression: default human-readable output unchanged. Tooling: extend `tests/test_memdoctor.py`. Manual: `uv run ~/.claude/tools/engram.py doctor --json | jq`. | 70 |
| 10 | Replace `engram.py` 30+ private `_on_*`/`_run_*` handlers with a thin `Hook` class per event | Lowers cognitive load when adding a 4th hook; helps onboarding contributors post-launch | Low | M | ~250 | `_on_session_start`, `_on_precompact`, `_on_user_prompt`, `_on_executive` | `tools/engram.py` | Pre: 106 tests green. Trigger: introduce `class SessionStartHook` etc. with `run(payload)` methods; `main()` dispatches. Expect: every existing CLI/hook test passes byte-identical output. Regression: `tests/test_engram_cli.py::test_help_lists_all_subcommands`, `test_on_session_start_emits_valid_json`, `test_on_precompact_captures_session`. Tooling: `uv run pytest`, `uv run ruff check .`. Manual: open Claude Code, confirm SessionStart banner unchanged. | 45 |

> Items 1–4 cluster as the **pre-launch readiness** sprint. Items 6–7 close the two known-marginal pending items. Items 5 and 10 are "wait for post-launch" because they're refactor-shaped and CLAUDE.md prefers shipping over restructuring at this stage.

### Combined-score sort (Impact × Merge / Effort, XS=1 / S=2 / M=4 / L=8)

| Rank | # | Combined |
|---|---|---|
| 1 | #1 (close issue #3) | High × 95 / XS = 285 |
| 2 | #2 (LICENSE + CHANGELOG) | High × 90 / XS = 270 |
| 3 | #8 (marketplace polish) | Med × 70 / XS = 140 |
| 4 | #3 (CONTRIBUTING + PR template) | High × 88 / S = 132 |
| 5 | #4 (eval in CI) | Med × 80 / S = 80 |
| 6 | #6 (shared DB connection) | Med × 75 / S = 75 |
| 7 | #9 (`doctor --json`) | Med × 70 / S = 70 |
| 8 | #7 (seek-from-end) | Low × 65 / S = 33 |
| 9 | #5 (split MemoryDB) | Med × 60 / M = 15 |
| 10 | #10 (Hook class) | Low × 45 / M = 6 |

## Inline summary

- **Profile**: pre-launch solo project, ~14-day-old, MIT plugin, 106 tests passing, single CI workflow (ruff+pytest), zero external contributions to date.
- **Top 3 opportunities**: (1) verify + close issue #3 (atomic exec cache write), (2) add `LICENSE` + `CHANGELOG.md` at repo root, (3) marketplace polish (badges/screenshots) + `CONTRIBUTING.md` + PR template.
- **File**: `repo-scout-sebastianbreguel-claude-engram.md` (this document).
