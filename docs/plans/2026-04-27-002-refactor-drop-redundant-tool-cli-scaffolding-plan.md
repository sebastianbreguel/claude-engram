---
title: "refactor: Drop redundant CLI scaffolding from helper tools + inline single-callsite digest helper"
type: refactor
status: active
date: 2026-04-27
origin: karpathy-scout-sebastianbreguel-claude-engram.md
---

# refactor: Drop redundant CLI scaffolding + inline single-callsite digest helper

## Overview

Two karpathy-scout proposals bundled into one sequenced refactor:

1. **Drop redundant `build_parser()` + `main()` + `__main__` blocks** from `tools/memcapture.py`, `tools/memdoctor.py`, `tools/mempatterns.py`. These are ceremony — `tools/engram.py` is the documented unified entrypoint per `.claude/CLAUDE.md`, and it already bypasses the standalone parsers via `_memcap_ns(**overrides)` / `_patterns_ns(**overrides)` helpers (`tools/engram.py:37`) that construct `argparse.Namespace` directly. The standalone parsers exist only to be imported once by their own `main()`. Karpathy filter: ceremony removal + first-order term (the entrypoint is `engram.py`, not these files).
2. **Inline `parse_digest_output`** at its single callsite in `tools/memcapture.py`. Verified single-callsite via grep: `parse_digest_output` is defined at line 993 and called once at line 1221 inside the `ingest_digest` branch of `run()`. Keep `_parse_fact_line` — it is used twice from inside `parse_digest_output` (lines 1023 + 1040), so it earns its keep as a nested helper after the inline.

**Net deletion (estimate, before test ports):** ~150 LOC across 3 tool files for proposal #1, ~20 LOC for proposal #2. Test ports add back ~5–10 LOC. Net ~−155 LOC.

**Owner alignment:** Karpathy-scout report rated this Karpathy 92 / Maintainer 80 / Combined 88 (top of the table). Owner has shipped similar scaffolding cuts in recent history. Direct-push-to-main per `feedback_push_workflow.md` (pre-launch convention, no PR unless requested).

## Out of scope

**Hard constraint — `tools/eval_corrections.py` is NOT touched.** It is a documented standalone CLI (docstring at `tools/eval_corrections.py:5-6`):

```
uv run tools/eval_corrections.py sample [--n 30] [--out eval/corrections_sample.md]
uv run tools/eval_corrections.py score  [--in eval/corrections_sample.md]
```

It is not routed through `engram.py`. Removing its `build_parser()` / `main()` would silently break the documented evaluation workflow. If a future plan wants to fold it into `engram eval ...` subcommands, that is a separate plan.

**Also out of scope:**
- Splitting `MemoryDB` god-class (deferred per `feedback_cosmetic_refactors.md`, post-launch only)
- `Hook` class refactor (same defer policy)
- Any signature change to `run()` in the three target files — keep `run(args: argparse.Namespace) -> int` exactly as is, so `engram.py` and tests don't have to change shape

## Why this is safe (preconditions verified)

| Claim | Evidence |
|---|---|
| `engram.py` does not call `memcapture.main` / `memdoctor.main` / `mempatterns.main` | `grep -n` of `engram.py` shows only `import memcapture / memdoctor / mempatterns` and direct calls into module functions (`engram.py:33-35,486,509,667,1049`) |
| Tests already use `run(ns)` for memdoctor | `tests/test_memdoctor.py:475,494` call `memdoctor.run(ns)` — no `main()` callers in this file |
| Tests use `run(ns)` for memcapture | No `main()` references in `tests/test_e2e.py` (only `from memcapture import MemoryDB`) and no `main()` references in `tests/test_engram_cli.py` |
| Only one test still treats a tool as standalone CLI | `tests/test_mempatterns.py:744-756` — `from mempatterns import main` then `sys.argv = [...]; main()`. Single porting target. |
| `install.sh` does not exec the .py files | `install.sh:30-32` only `cp` them; hooks invoke `engram.py`, never the helpers directly |
| `hooks/hooks.json` does not invoke helpers directly | All hook entries route through `engram on-*` (verified during scout pass) |
| `parse_digest_output` is single-callsite | Defined at `tools/memcapture.py:993`; only outside callsite at `tools/memcapture.py:1221` (inside `run()` `ingest_digest` branch) |
| `_parse_fact_line` has 2 callsites | Both are inside `parse_digest_output` (lines 1023, 1040) — stays as helper after inline |

## Implementation units

Sequenced for incremental verification — each phase ends in a green test run before the next starts. Total: 4 phases.

### Phase 1 — Drop scaffolding from `tools/memdoctor.py` (smallest blast radius first)

**Files:**
- `tools/memdoctor.py` — delete `build_parser()` (line 712), `main()` (line 768), and the `if __name__ == "__main__":` block (line 772). Estimated deletion: ~60 LOC.
- Verify `argparse` import is still needed (it is — `run()` accepts `argparse.Namespace`).

**Validation:**
1. `uv run pytest tests/test_memdoctor.py -v` → all 23+ tests pass
2. `uv run pytest tests/test_engram_cli.py -v` → engram-routed memdoctor calls still work
3. `uv run ruff check tools/memdoctor.py` → no unused imports
4. `uv run ty check tools/memdoctor.py` → typecheck clean
5. `./install.sh` → re-deploy succeeds, `~/.claude/tools/memdoctor.py` updated
6. Manual smoke: `uv run python -c "import memdoctor; print(memdoctor.run.__doc__ or 'ok')"`

**Risk callouts:**
- Lowest-risk file (memdoctor) — start here to lock in the deletion pattern before touching memcapture.
- `argparse` may become an unused import if `run()` takes `argparse.Namespace` only as a type hint. Ruff will flag — re-import as `from argparse import Namespace` if needed, or keep `import argparse` if the body still references it.

**Rollback:** `git restore tools/memdoctor.py` — single-file change, trivially reversible.

### Phase 2 — Drop scaffolding from `tools/mempatterns.py` + port the one test that still calls `main()`

**Files:**
- `tools/mempatterns.py` — delete `build_parser()` (line 559), `main()` (line 603), `if __name__` block (line 607). Estimated deletion: ~48 LOC.
- `tests/test_mempatterns.py:744-758` — port `TestCLI::test_status_flag` from `from mempatterns import main; sys.argv = [...]; main()` to `mempatterns.run(ns)` with a constructed `argparse.Namespace`. Mirror the `_patterns_ns(**overrides)` shape from `tools/engram.py` (look up the helper, copy its defaulted-fields dict into a small test fixture, then override `status=True`, `db_path=...`, `wiki_dir=...`).

**Validation:**
1. `uv run pytest tests/test_mempatterns.py -v` → all 30+ tests pass, including the ported `test_status_flag`
2. `uv run pytest tests/test_engram_cli.py -v` → engram-routed pattern flows still work
3. `uv run ruff check tools/mempatterns.py tests/test_mempatterns.py` → clean
4. `uv run ty check tools/mempatterns.py` → clean
5. `./install.sh` → re-deploy succeeds
6. Smoke: `uv run python -c "from mempatterns import run; help(run)"`

**Risk callouts:**
- The test fixture for `run(ns)` must include **every** field that `run()` reads (`status`, `db_path`, `wiki_dir`, `ttl_days`, `min_co_edits`, etc.). Missing a default will raise `AttributeError` at runtime. Mitigate: copy the full default-set from `_patterns_ns` in `engram.py:_patterns_ns`. If `engram.py` doesn't surface every flag the test uses, pull defaults from `build_parser()` *before deleting it* — read it once, list the dest names + defaults, then delete.
- Ported test must still cover the *same* assertion (status flag emits expected message). Don't downgrade the assertion.

**Rollback:** `git restore tools/mempatterns.py tests/test_mempatterns.py` — two-file change, isolated.

### Phase 3 — Drop scaffolding from `tools/memcapture.py` (largest, most flag-rich)

**Files:**
- `tools/memcapture.py` — delete `build_parser()` (line 1090), `main()` (line 1329), `if __name__` block (line 1333). Estimated deletion: ~52 LOC (`build_parser` is the largest of the three, ~45 lines covering ~20 hidden hook flags).

**Validation:**
1. `uv run pytest tests/test_e2e.py -v` → all e2e tests pass (they use `MemoryDB` directly + `engram.py` shell, never `main()`)
2. `uv run pytest tests/test_engram_cli.py -v` → engram-routed flows untouched
3. `uv run pytest` → full suite (currently 79 passing per README) stays at 79+ green
4. `uv run ruff check tools/memcapture.py` → clean
5. `uv run ty check tools/memcapture.py` → clean
6. `./install.sh` → re-deploy
7. End-to-end hook smoke (manual, but cheap):
   - Open a new Claude Code session in this repo → SessionStart banner appears (proves `engram on-session-start` → `memcapture._memcap_ns(banner=True)` path still works)
   - Run `engram --stats` → output matches pre-refactor

**Risk callouts:**
- `memcapture.build_parser()` defines ~20 hidden hook flags (lines 1090-1135). **Before deleting**, audit `tools/engram.py:_memcap_ns` and confirm every dest name lives in its defaults dict (`transcript, all, recent, query, stats, memories, forget, inject, inject_project, banner, banner_project, banner_name, ingest_digest, ingest_snapshot, session_id, project, ephemeral, extract_facts, compactions`). If `_memcap_ns` is missing any field that `run()` references, **add it to `_memcap_ns` first** (separate commit) before deleting `build_parser`. Otherwise hook calls will raise `AttributeError` at runtime under a fresh Claude Code session.
- This is the file the user interacts with daily via session hooks. A regression here is more visible than memdoctor/mempatterns. The session-start smoke test is the load-bearing check — do not skip it.

**Rollback:** `git restore tools/memcapture.py` — single-file. If a regression is detected post-install, run `git stash` + `./install.sh` to redeploy the prior version.

### Phase 4 — Inline `parse_digest_output` at its single callsite (proposal #2)

**Files:**
- `tools/memcapture.py` — fold `parse_digest_output` (lines 993–1052, ~60 lines) into the `args.ingest_digest:` branch of `run()` near line 1221. Keep `_parse_fact_line` as a nested helper (it is called twice from inside the new inlined block, lines 1023 + 1040 in the original).

**Validation:**
1. `uv run pytest tests/test_e2e.py::test_ingest_digest_then_inject_surfaces_the_memory tests/test_e2e.py::test_ingest_digest_is_idempotent tests/test_e2e.py::test_parse_digest_dedupes_duplicate_topics_in_batch -v` → all 3 named digest tests pass
2. `uv run pytest tests/test_e2e.py -v` → full e2e suite green
3. `uv run pytest` → 79+ pass total
4. `uv run ruff check tools/memcapture.py` → clean (line length ≤140; if the inlined block pushes the `run()` function past readability, abort the inline and reopen — see escape hatch)
5. `./install.sh` → re-deploy
6. Manual smoke: ingest a digest, inject, verify memory surfaces

**Risk callouts:**
- **Escape hatch:** if inlining makes `run()` significantly harder to read (e.g., the `ingest_digest` branch balloons past ~80 lines and obscures the dispatch), abandon proposal #2 and keep `parse_digest_output` as a top-level helper. The first-order karpathy filter is "first-order term" — `run()` is the first-order dispatcher; if inlining hurts that, the inline failed its own filter. Discuss with owner before forcing it.
- `_parse_fact_line` becoming a closure inside `run()` could slightly change profiling output / stack traces. Functionally identical; cosmetic only.
- Tests are behavior-based (`test_ingest_digest_then_inject_surfaces_the_memory` etc.), so they should pass unchanged. If any test imports `parse_digest_output` directly from `memcapture`, that import will break — `grep -n "parse_digest_output" tests/` to confirm. (Pre-check at scout time showed only the in-file callsite, no test imports.)

**Rollback:** `git restore tools/memcapture.py` — single-file.

## Sequencing rationale

memdoctor → mempatterns → memcapture → inline. Reasoning:

1. **memdoctor first** = lowest-traffic file, smallest scaffold, fewest hidden flags. Locks in the deletion pattern + ruff/ty workflow.
2. **mempatterns second** = adds the test-port skill (only file that needs it), still smaller than memcapture.
3. **memcapture third** = highest-stakes file (session hooks). All deletion-pattern dust has settled by now; the only new risk is the `_memcap_ns` flag-coverage audit, which is a discrete pre-step.
4. **Inline last** = depends on memcapture being in its post-Phase-3 shape. Inlining before the scaffold is gone would mean editing `parse_digest_output` *and* deleting it later — wasted work.

Each phase ends in commit + test-green. If a phase breaks, the next does not start.

## Test scenarios (what each file's run() must continue to support)

Listed for the implementer so they don't have to re-derive coverage.

**memdoctor.run(ns):**
- `--analyze` end-to-end
- `--per-project` filter
- correction-heavy / error-loop / keep-going-loop / rapid-corrections / restart-cluster signals fire
- `--no-rules` flag suppresses rule emission
- memory.db enrichment path

**mempatterns.run(ns):**
- `--status` (the ported test)
- `--detect` co-edit detection
- `--write-wiki` writes the patterns wiki
- TTL / min-co-edit thresholds honored

**memcapture.run(ns):** (most flag-dense — see `_memcap_ns` defaults for the canonical list)
- `--stats`, `--query`, `--memories`, `--forget` (4 user-facing)
- `--banner`, `--banner-project`, `--inject`, `--inject-project` (hooks)
- `--ingest-digest`, `--ingest-snapshot`, `--ephemeral` (digest pipeline)
- `--compactions`, `--transcript`, `--session-id`, `--project` (capture)
- `--extract-facts` env-var default

If a flag is missing from `_memcap_ns` and Phase 3 ships, that flag silently fails. The pre-flight audit is the line-of-defense.

## Confidence check

| Question | Answer |
|---|---|
| Is the deletion idempotent under re-install? | Yes — `install.sh` `cp`s files; deleting from source removes from `~/.claude/tools/` on next install |
| Is there any path that imports `build_parser` from these tools? | Verified `grep -n "build_parser" .` — only self-referenced inside each tool |
| Could a user have a habit of running `python tools/memcapture.py --stats` directly? | Possible but unsupported — `.claude/CLAUDE.md` documents `engram` as the entrypoint. Caveat: add a one-line note to the commit message so the owner doesn't get caught off-guard when a stale shell habit fails |
| Can the plan run in a single sitting? | Yes — 4 phases × (~10 min edit + ~30s test) = ~45 min wall clock |
| Does each phase produce a git-bisectable commit? | Yes — one commit per phase. Test-green at each commit |

**Open questions (none blocking):**
- Should the commit messages tag this as `refactor:` or `chore:`? Owner convention: `refactor:` per recent history (e.g., commit 5dcdde6 "chore: pre-launch round 2 (CI, perf, dedupe, eval harness)" used chore for pre-launch hardening). Default to `refactor:` for behavior-preserving deletion.

## Risk summary (top 3)

1. **`_memcap_ns` flag coverage drift (Phase 3).** If `engram.py:_memcap_ns` is missing a flag that `memcapture.run()` reads, hook calls silently break. Mitigation: pre-flight audit by reading `build_parser()` once before deleting, diffing against `_memcap_ns` defaults, and patching `_memcap_ns` first.
2. **Test fixture under-specification (Phase 2).** Ported test must construct a Namespace with every field `mempatterns.run()` reads. Mitigation: same diff approach — read `build_parser` defaults once, use them as the canonical set.
3. **Inline regret (Phase 4).** If `run()` becomes harder to read, the inline failed its own karpathy filter. Mitigation: documented escape hatch — abandon proposal #2 if readability degrades; the value is in proposal #1 anyway.

## Handoff

After all 4 phases land:
- One commit per phase, pushed to `main` directly (per `feedback_push_workflow.md`)
- Update `karpathy-scout-sebastianbreguel-claude-engram.md` to mark these proposals as "shipped"
- Optional: update memory `project_pending_work.md` to drop these from the queued opportunities list
