# karpathy-scout — sebastianbreguel/claude-engram

> generated 2026-04-27 · target = current cwd · graph: 14 files, 346 nodes, 3419 edges (fresh)

---

## shape & vibe

| metric | value |
|---|---|
| language | python (≥3.12) + 1 .mjs demo + bash install |
| total commits | repo small, pre-launch |
| project python LOC (src) | ~5,275 across 5 tool files |
| project python LOC (tests) | ~2,326 across 4 test files |
| **runtime deps** | **0** (pyproject lists only `pytest` + `ruff` as dev) |
| ruff line-length | 140 |
| top largest files | `memcapture.py` 1334 · `engram.py` 1243 · `memdoctor.py` 773 · `mempatterns.py` 608 · `eval_corrections.py` 217 |
| largest class | `MemoryDB` (700 lines, `memcapture.py:83`) |
| try/except hits | engram.py:66 · memcapture.py:29 (project total ~100) |
| argparse hits | 5 tool files all wire their own argparse |
| ABC / FactoryProvider / Manager / Strategy in src | **0** (only in `.venv`) |

## karpathy diagnostic

ok so this is already kind of karpathy-shaped on the dependency axis. zero runtime deps. no docker, no mcp, no api keys. pyproject is clean. owner already shipped a "demos 7→1" trim PR (#4, +1129/−77). readme literally brags about ~350 ambient tokens. that's the calculator philosophy showing up. good.

what's left that's real:

- `MemoryDB` is a 700-line class. owner already knows this and **explicitly deferred a split as cosmetic-refactor-post-launch**. fine. memory.md says so.
- `engram.py` has 66 try/except blocks in 1243 lines. normally that's slop. but engram.py is a hook orchestrator invoked by claude code on session events — if a hook raises, the user sees a broken session. **defensive try/except is load-bearing here, not slop**. karpathy filter does not apply. skip.
- the 5 tool files each define their own `build_parser()` + `main()`, but `engram.py` *bypasses all of them* via `_memcap_ns(**overrides)` and `_patterns_ns(**overrides)` helpers that construct `argparse.Namespace` directly. so those standalone parsers in `memcapture.py`, `memdoctor.py`, `mempatterns.py`, `eval_corrections.py` are pure dev/test ceremony — duplicating ~30-50 lines each. potential drop. ~150 lines total.
- `memcapture.py::run` is 190 lines but it's a **flat if/elif subcommand dispatch**. each branch is 5-15 lines, single-purpose. probably a terrible idea to wrap that in a handler dict — you'd add abstraction to save 30 lines, lose readability, and karpathy actually prefers the flat version. **leave it**.
- `mempatterns.py` has 3 stateful classes (WikiWriter, PatternDetector, PatternsOrchestrator). they own db connections and config. these are not ABCs and not anti-patterns — flat classes with single responsibility. **leave them**.
- first-order term: capture is the point, and `memcapture.py` is the largest file. mass distribution is honest. no second-order Y eating real estate that should be X.

honest read: this codebase has maybe **3 real karpathy proposals**, and 2 of them already conflict with owner's explicit defer policy. i cannot simplify this any further is not where you are, but you're closer than most.

## owner / maintainer profile

| signal | value |
|---|---|
| total merged PRs | 4 (all by sebastianbreguel) |
| closed-unmerged | 0 |
| open PRs | 0 |
| open issues | 0 |
| recent shape | PR #4 "pre-launch trim" (+1129/-77) · PR #5 "pre-launch readiness" (+105/-0) |
| stated direction | pre-launch, readme emphasizes "~350 ambient tokens / no docker / no mcp" |
| **explicit defer policy** | **L-effort cosmetic refactors deferred post-launch** (split MemoryDB, Hook classes) per memory.md `feedback_cosmetic_refactors.md` |

owner has shipped both deletion-heavy work (PR #4 trim) and additive polish (PR #5 readme/contributing). owner is **karpathy-aligned in spirit** — already collapsed 7 demos to 1, ships zero-dep, dislikes ceremony in stated values — but **pragmatic about timing**: pre-launch focus on shippable, cosmetic refactors deferred.

so: any proposal whose shape matches "L-effort cosmetic refactor of internal structure" gets a maintainer-score haircut even if karpathy adores it.

---

## the table

| # | Proposal | Filter | Anchor | Karpathy | Maintainer | Impact | Effort | Combined |
|---|----------|--------|--------|----------|------------|--------|--------|----------|
| 1 | drop redundant `build_parser()` + `main()` + module-level argparse from `memcapture.py`, `memdoctor.py`, `mempatterns.py`, `eval_corrections.py` — single entrypoint is `engram.py` per stated architecture; tests already invoke via constructed namespaces | ceremony | `tools/{memcapture,memdoctor,mempatterns,eval_corrections}.py::build_parser/main` | 88 | 45 | Medium | M | 64 |
| 2 | inline `parse_digest_output` body callers and confirm `_parse_fact_line` is single-call site — possible flatten | compression | `tools/memcapture.py::parse_digest_output`, `_parse_fact_line` | 60 | 50 | Low | S | 51 |
| 3 | split `MemoryDB` (700 lines) along schema-ops / search-ops / banner-ops seams using natural community boundaries | read-in-one-sitting | `tools/memcapture.py::MemoryDB` (lines 83–782) | 75 | **15** | Medium | L | **44** ← skip per owner policy |
| 4 | flatten `engram.py` `_on_*` hook handlers to a small dispatch dict instead of long if/elif in `main` | what-if-opposite | `tools/engram.py::main`, `_on_session_start`, `_on_precompact`, `_on_user_prompt`, `_on_executive` | 65 | **18** | Medium | M | **42** ← skip per owner policy ("Hook classes" deferred) |

> note: rows #3 and #4 fall below the listing-floor when factoring maintainer. listed for **honest tension**, not as actionable. owner explicitly deferred both as cosmetic-refactor-post-launch in `feedback_cosmetic_refactors.md`. resurface them after launch.

---

## per-opportunity detail

### #1 — drop redundant standalone CLI scaffolding from helper tools

**why karpathy would do it:** "you have one entrypoint, `engram.py`. the four helper tools each ship their own `argparse` + `main` + `build_parser` that the actual entrypoint *bypasses* via `_memcap_ns(**overrides)`. that's ceremony pretending to be flexibility. drop the parsers, keep `run(args, ...)`. tests can build the same namespace the orchestrator does. ~150 lines, four files, one shape."

**graph evidence:**
- `engram.py::_memcap_ns` (line 37) constructs `argparse.Namespace` directly — bypasses `memcapture.build_parser` entirely
- `engram.py::_patterns_ns` does the same for `mempatterns`
- `tools/memcapture.py::build_parser` / `main` exists but only called from `tests/test_e2e.py` and `if __name__ == "__main__"`
- `tools/memdoctor.py::build_parser` / `main` — same shape
- `tools/mempatterns.py::build_parser` / `main` — same shape
- `tools/eval_corrections.py::build_parser` / `main` — same shape

**diff sketch:**
- delete `build_parser()` + `main()` + the `if __name__ == "__main__"` block from `memcapture.py`, `memdoctor.py`, `mempatterns.py`, `eval_corrections.py`
- factor a shared `_make_ns(**overrides)` helper or keep the one already in `engram.py`
- update `tests/test_e2e.py`, `tests/test_memdoctor.py`, `tests/test_mempatterns.py` to call `run(ns)` with constructed namespaces (mirror `_memcap_ns` pattern)
- keep `pyproject.toml` `pythonpath = ["tools"]` — imports unchanged
- net: roughly −150 LOC across 4 tool files, +30 LOC of test-side namespace builders, **−~120 net**

**e2e test plan:**
1. preconditions: clean working tree, deps installed (`uv sync --dev`)
2. trigger: `uv run pytest -v` after the refactor
3. expected: full suite passes (currently 79 tests per readme); no test that previously asserted CLI flag-parsing behavior should disappear silently — port to namespace-building tests
4. regression: install via `./install.sh` and run a real claude-code session; confirm hook flows still operate (engram.py → `run(_memcap_ns(...))` chain unaffected since engram.py was the entrypoint already)
5. tooling: pytest already in CI (`uv run pytest`)
6. manual cmd: `uv run pytest && ./install.sh && bash -c 'echo "{}" | uv run python -m engram on-session-start --transcript-path /tmp/fake.jsonl'`

**maintainer note:** this is a *deletion* PR (karpathy's preferred shape) that touches every tool file. owner shipped trim PR #4 with similar cross-cutting deletion mass (+1129/−77, the −77 was the trim signal). but owner's explicit pre-launch focus is on shippable surface area, and this refactor reshuffles the test contract — meaningful churn for "looks the same from outside". confidence: **medium-low**. surface but flag as *post-launch candidate*.

### #2 — flatten `parse_digest_output` + `_parse_fact_line` if single-callsite

**why karpathy would do it:** "two helpers in `memcapture.py` that handle the digest-text → memory-rows shape. if `_parse_fact_line` only has one caller and `parse_digest_output` only routes, that's a function boundary that exists for symmetry, not for reuse. inline."

**graph evidence:**
- `tools/memcapture.py::parse_digest_output` and `_parse_fact_line` both module-level
- callsites: `engram.py` invokes via `_memcap_ns(ingest_digest=True, ...) → run() → parse_digest_output` (one path)

**diff sketch:**
- inspect actual callsite count via `find_referencing_symbols`
- if exactly one caller each → inline
- if multiple → leave alone, this is bacterial
- net: probably −20 LOC if single-callsite, **0** otherwise

**e2e test plan:**
1. preconditions: confirm callsite count first via `mcp__serena__find_referencing_symbols`
2. trigger: `uv run pytest tests/test_e2e.py::test_ingest_digest_then_inject_surfaces_the_memory -v`
3. expected: existing assertion about ingest-then-inject keeps passing
4. regression: `test_ingest_digest_is_idempotent` and `test_parse_digest_dedupes_duplicate_topics_in_batch`
5. tooling: pytest
6. manual cmd: `uv run pytest tests/test_e2e.py -k "digest"`

**maintainer note:** small surface, low risk, low impact. owner won't reject but won't celebrate. neutral.

### #3 — split `MemoryDB` *(skip per owner policy)*

**why karpathy would do it:** "700-line class is way past read-in-one-sitting. the natural seams are already in the graph: schema ops (`_create_tables`, `_migrate`, `_content_hash`), capture ops (`save_session`, `is_captured`, `fact_exists`, `save_compaction`), retrieval ops (`search`, `inject_context`, `recent_sessions`, `build_banner`, `_format_snapshot`, `_fallback_inject`), memory CRUD (`upsert_memory`, `list_memories`, `forget_memory`, `forget_all_ephemeral`, `cleanup_ephemeral`). split along the seam that already exists."

**graph evidence:**
- `tools/memcapture.py::MemoryDB` lines 83–782, 27 methods grouped by responsibility
- explicit defer in `~/.claude/projects/.../memory/feedback_cosmetic_refactors.md`: *"skip L-effort cosmetic refactors (split MemoryDB, Hook classes) pre-launch; defer until post-launch with PR review"*

**maintainer note:** **explicitly deferred**. do not propose pre-launch. revisit as a post-launch PR with review. Maintainer Score = 15 reflects this.

### #4 — flatten engram.py hook dispatch *(skip per owner policy)*

**why karpathy would do it:** "the hook handlers `_on_session_start`, `_on_precompact`, `_on_user_prompt`, `_on_executive` are dispatched from a long if/elif inside `main`. one dict literal at module level + `dispatch[args.hook](args)` saves the indentation pyramid. but again — flat if/elif is also fine, and the owner has explicitly deferred this."

**graph evidence:**
- `tools/engram.py::main` (line ~1228) routes among `_on_*` handlers
- explicit defer in `feedback_cosmetic_refactors.md` ("Hook classes")

**maintainer note:** same defer. skip pre-launch.

---

## final summary

> "innovation for you is always compression, not addition." — karpathy

**diagnostic in one line:** zero runtime deps, owner already karpathy-aligned, ~3 real proposals survived; 2 of those 3 are explicitly deferred by owner pre-launch.

**top 3 by combined rank:**
1. drop redundant CLI scaffolding from helper tools — Karp 88 / Maint 45 / Combined 64 ← actionable
2. inline single-callsite digest helpers — Karp 60 / Maint 50 / Combined 51 ← low-stakes, optional
3. split MemoryDB or flatten hook dispatch ← skip pre-launch, owner deferred

**file written to:** `karpathy-scout-sebastianbreguel-claude-engram.md`
