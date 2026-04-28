---
title: "feat: Pre-launch readiness sprint (issue #3 + community-health files + marketplace polish)"
type: feat
status: active
date: 2026-04-27
origin: repo-scout-sebastianbreguel-claude-engram.md
---

# feat: Pre-launch readiness sprint

## Overview

Pre-launch hardening bundle. Closes the only open issue (#3, executive cache atomic write — already implemented in `tools/engram.py:715-742`, just needs verification and a close), adds the missing community-health files (`CONTRIBUTING.md`, `.github/PULL_REQUEST_TEMPLATE.md`) so the post-launch external-PR path is unblocked, and lands the lightest marketplace-polish pass (CI + license badges in `README.md`, screenshot pointer in `.claude-plugin/plugin.json`).

**Out of scope (deferred):** `MemoryDB` god-class refactor (#5 in scout — post-launch shape), `engram doctor --json` (#9 — not blocking), shared SQLite connection in SessionStart (#6, pending memory `#5`), seek-from-end in `_extract_chunk` (#7, pending memory `#9`), eval harness in CI (#4 — non-blocking quality work). All survive in `repo-scout-sebastianbreguel-claude-engram.md`.

---

## Problem Frame

`claude-engram` is a 2-week-old solo plugin sitting at `0.1.0`, ready to launch. Pre-launch scout (`repo-scout-sebastianbreguel-claude-engram.md`) flagged four readiness gaps:

1. **Issue #3 stale.** `executive cache: reorder rotate/write so cache stays present if tmp write fails` — code already does `tmp.write_text` → rotate cache→`.prev` → `os.replace(tmp, cache)` (`tools/engram.py:723-739`), and three tests already cover the case (`test_executive_cache_rotates_to_prev`, `test_executive_cache_survives_tmp_write_failure`, `test_executive_cache_tmp_includes_pid` in `tests/test_engram_cli.py`). Issue is open only because nobody confirmed and closed it.
2. **No `CONTRIBUTING.md`.** External contributors can't see the `uv`-only / `ruff` / `pytest -q` / "no Co-Authored-By" rules that already live in the user's private `CLAUDE.md`. A post-launch PR opened in good faith would trip every guardrail.
3. **No PR template.** Same risk — implicit "Summary / Test plan" convention from `CLAUDE.md` isn't surfaced at PR creation time.
4. **No marketplace surface polish.** `plugin.json` declares the plugin and `README.md` has the demo GIF, but there are no CI / license badges and no screenshot reference in the manifest. Cheap social proof for the plugin marketplace listing.

`LICENSE` (MIT, 2026) and `CHANGELOG.md` (Keep-a-Changelog style) already exist at the repo root — scout report incorrectly flagged these as missing; no work needed.

---

## Requirements Trace

- R1. Verify the atomic-write behavior described in issue #3 is implemented and tested, then close the issue with links to the commit + test names.
- R2. `CONTRIBUTING.md` exists at repo root and codifies: `uv` only (no `pip`/`python`/`python3`), `ruff check + ruff format --check + pytest -q` as the local pre-PR gate, no `Co-Authored-By` lines, no "Generated with Claude Code" attribution, conventional commit prefixes (`feat:` / `fix:` / `chore:` / `docs:` / `refactor:` / `perf:`), `./install.sh` re-run requirement after editing `tools/`.
- R3. `.github/PULL_REQUEST_TEMPLATE.md` exists with a `## Summary` + `## Test plan` skeleton matching `CLAUDE.md` style.
- R4. `README.md` shows at least two badges (CI status, MIT license). `.claude-plugin/plugin.json` includes a pointer to a hero screenshot/GIF if the marketplace schema supports a `screenshots` or `icon` field; otherwise no manifest change.
- R5. None of the above changes affects existing tests, hooks, or banner output. The 106-test suite stays green.

---

## Scope Boundaries

- No code changes in `tools/engram.py`, `tools/memcapture.py`, `tools/memdoctor.py`, or `tools/mempatterns.py` (this is a docs/community-health/manifest sprint).
- No version bump (still `0.1.0`); the launch commit will bump separately per memory `feedback_pre_launch_discipline`.
- No `CODEOWNERS` (solo project; not useful pre-launch).
- No `SECURITY.md` (defer until launched and there's an inbox to receive reports).
- No `Code of Conduct` (defer; not blocking launch).
- No CI workflow changes — `.github/workflows/test.yml` keeps its current `ruff check` + `ruff format --check` + `pytest -q` shape.

### Deferred to Follow-Up Work

- Marketplace schema check for `screenshots`/`icon` in `plugin.json`: if the Claude Code plugin manifest schema does not yet support these fields, U4 lands README badges only and a follow-up issue tracks the manifest field once the schema documents it.
- Eval harness in CI (scout #4): non-blocking, post-launch.
- Refactor seams flagged by scout (`MemoryDB` split, `Hook` class): post-launch.

---

## Context & Research

### Relevant Code and Patterns

- `tools/engram.py:700-742` — `_on_executive` cache write sequence (tmp-first, rotate-then-replace).
- `tools/engram.py:366` — `_executive_cache_path(cwd)` resolves `~/.claude/engram/executive/<cwd-slug>.md`.
- `tests/test_engram_cli.py` — existing executive-cache test trio: `test_executive_cache_rotates_to_prev`, `test_executive_cache_survives_tmp_write_failure`, `test_executive_cache_tmp_includes_pid`.
- `.github/workflows/test.yml` — single `test` job (`ubuntu-latest`, `astral-sh/setup-uv@v5`, Python 3.11). Job name `test` is the badge anchor.
- `.claude-plugin/plugin.json` — current keys: `name`, `description`, `version`, `author`, `homepage`, `repository`, `license`, `keywords`, `privacy_policy`. `keywords` already includes `claude-code-plugin`.
- `README.md:7` — hero GIF reference: `demo/readme-hero-focus.gif`. Same asset usable as marketplace screenshot.
- `CHANGELOG.md` — Keep-a-Changelog format, currently has an `## Unreleased` section. The four sprint items belong here.

### Institutional Learnings (memory)

- `feedback_pre_launch_discipline.md` — skip version bumps / tags until launched. Main-branch work OK pre-launch.
- `feedback_subagent_model.md` — subagents always Sonnet 4.6 (only relevant if any sprint unit dispatches one; none currently planned).
- `project_executive_format.md` — 3-bullet exec format, single-line was tried and reverted Apr 2026. Do not touch in this sprint.

### External References

- Keep-a-Changelog 1.1: existing `CHANGELOG.md` already follows this; new sprint entries go under `## Unreleased`.
- Shields.io badge URLs: `img.shields.io/github/actions/workflow/status/<owner>/<repo>/<workflow-file>?branch=main` for CI status; `img.shields.io/github/license/<owner>/<repo>` for license.
- Claude Code plugin manifest spec: verified `plugin.json` is currently the only published surface; whether `screenshots[]` is a recognized key needs a docs check before U4 (see Deferred to Follow-Up Work).

---

## Key Technical Decisions

- **Issue #3 closes without code changes.** The fix landed in commit `ec8a44a` ("pre-launch trim: friction banner, demos 7→1, atomic exec cache") and `9ecdf19` ("feat: executive cache rotates to .prev"). `tools/engram.py:715-742` and the three tests in `tests/test_engram_cli.py` already match the issue's ask. U1 is verification + a close comment, not a fix.
- **`CONTRIBUTING.md` mirrors `CLAUDE.md` rules verbatim where possible.** Don't paraphrase — paraphrasing creates drift. Quote the relevant `CLAUDE.md` lines ("`uv` only (no pip/python/python3)", "ruff (line 140, double quotes)") and add only the contributor-facing context.
- **PR template stays minimal.** Two H2s (`## Summary`, `## Test plan`), nothing else. `CLAUDE.md` style is short prose + bullet checklist.
- **Badges go in `README.md`, not `plugin.json`.** The plugin manifest is for marketplace metadata (machine-readable). Badges are visual signals for the GitHub UI / README readers.
- **No `gh issue close` from the plan.** U1 verifies + drafts the close comment; the actual close is the user's gh action so the audit trail attributes correctly.

---

## Open Questions

### Resolved During Planning

- *Should `LICENSE` / `CHANGELOG.md` be added?* — No. Both already exist at repo root. Scout report was wrong on this. No work needed.
- *Should issue #3 require any code change?* — No. Code path at `tools/engram.py:715-742` already implements the requested ordering (tmp write → rotate → atomic replace), and three tests cover it.
- *Should this sprint bump the version?* — No. Memory `feedback_pre_launch_discipline` says skip version bumps until launch.

### Deferred to Implementation

- Whether `.claude-plugin/plugin.json` accepts a `screenshots[]` or `icon` field in the current marketplace schema. U4 will check the published Claude Code plugin docs at implementation time; if unsupported, U4 ships README badges only and opens a follow-up.
- Exact badge style (`flat` vs `flat-square` vs `for-the-badge`). Pick one consistent style at U4 implementation time; default to `flat` to match GitHub's native UI density.

---

## Implementation Units

- U1. **Verify + close issue #3 (executive cache atomic write)**

**Goal:** Confirm the atomic-write behavior described in issue #3 is fully implemented and tested, then close the issue with links to the commits + test names.

**Requirements:** R1, R5

**Dependencies:** None

**Files:**
- Read: `tools/engram.py` (`_on_executive` body, lines 700–742)
- Read: `tests/test_engram_cli.py` (`test_executive_cache_rotates_to_prev`, `test_executive_cache_survives_tmp_write_failure`, `test_executive_cache_tmp_includes_pid`)
- No file changes in this unit

**Approach:**
- Re-read the three named tests; confirm each actually exercises a distinct failure mode (rotate semantics, tmp write `OSError`, PID-suffixed tmp filename).
- Re-read `tools/engram.py:715-742`; confirm the sequence is `tmp.write_text` → on `OSError` `unlink` + raise → if `cache.exists()` rotate to `.prev` → `os.replace(tmp, cache)`. Note that if the `os.replace(cache, prev)` rotation fails, a warning is logged and the publish still attempts (matches the inline comment).
- Run `uv run pytest tests/test_engram_cli.py -k executive_cache -v` and confirm all three tests pass on `main`.
- Draft a close comment for issue #3 referencing commits `ec8a44a` ("pre-launch trim: friction banner, demos 7→1, atomic exec cache") and `9ecdf19` ("feat: executive cache rotates to .prev") plus the three test names. Do not run `gh issue close` from the plan — surface the comment and let the user close.

**Patterns to follow:**
- Existing close-comment style in `git log` recent commits — terse, specific, references commits by short SHA.

**Test scenarios:**
- Test expectation: none — verification-only unit; behavior already covered by `test_executive_cache_rotates_to_prev` (Happy path: rotate-then-publish), `test_executive_cache_survives_tmp_write_failure` (Error path: tmp write `OSError` leaves live cache untouched), `test_executive_cache_tmp_includes_pid` (Edge case: concurrent SessionStart hooks don't race on shared tmp filename).

**Verification:**
- `uv run pytest tests/test_engram_cli.py -k executive_cache -v` returns 3 passing tests.
- Issue #3 has a close comment posted (by the user, not the plan) linking the commit SHAs and test names.

---

- U2. **Add `CONTRIBUTING.md`**

**Goal:** Codify the contributor-facing subset of `CLAUDE.md` rules at the repo root so external PRs don't trip implicit guardrails.

**Requirements:** R2, R5

**Dependencies:** None

**Files:**
- Create: `CONTRIBUTING.md`

**Approach:**
- Sections: `## Setup` (clone + `./install.sh`), `## Running tests` (`uv run pytest -q`), `## Linting and formatting` (`uv run ruff check . && uv run ruff format --check .`), `## Pre-commit` (`uv run pre-commit run --all-files`), `## Commit conventions` (prefixes used in this repo: `feat:` / `fix:` / `chore:` / `docs:` / `refactor:` / `perf:` / `cleanup:`), `## What we don't accept` (no `Co-Authored-By` lines, no "Generated with Claude Code" attribution, no `pip`/`python`/`python3` invocations — `uv` only), `## After editing tools/` (`./install.sh` re-run note from `.claude/CLAUDE.md`).
- Quote `CLAUDE.md` rules verbatim where possible (e.g., `> uv only (no pip/python/python3). ruff (line 140, double quotes). ty typecheck.`) so a contributor sees the same rule the maintainer follows.
- Link to `docs/architecture.md` and `docs/cli-reference.md` from a `## Further reading` section so the doc stays slim.
- Length target: ≤120 lines. If it grows past that, split into `CONTRIBUTING.md` (entry point) + `docs/contributing/*.md` (deep dives) — but for this sprint, single file is fine.

**Patterns to follow:**
- `README.md` voice: short prose, code blocks for commands, no marketing language.
- `docs/cli-reference.md` style for any command listings.

**Test scenarios:**
- Test expectation: none — pure documentation file. No CI check beyond markdown rendering.

**Verification:**
- `CONTRIBUTING.md` exists at repo root.
- `gh repo view sebastianbreguel/claude-engram` shows the "Contributing" community-health checkmark filled.
- All commands listed in `CONTRIBUTING.md` execute successfully on a fresh clone (manual smoke test: `uv run pytest -q`, `uv run ruff check .`).

---

- U3. **Add `.github/PULL_REQUEST_TEMPLATE.md`**

**Goal:** Pre-fill PR descriptions with `## Summary` + `## Test plan` so contributors don't have to invent the structure.

**Requirements:** R3, R5

**Dependencies:** None

**Files:**
- Create: `.github/PULL_REQUEST_TEMPLATE.md`

**Approach:**
- Two H2 sections only: `## Summary` (1–3 bullets) and `## Test plan` (markdown checklist of test commands run locally).
- Add a one-line footer: `If this PR adds a new \`tools/*.py\` file, re-run \`./install.sh\` before testing.` (mirrors `.claude/CLAUDE.md` testing rule).
- No `## Screenshots`, no `## Breaking changes`, no `## Checklist` — keep noise out. Contributors who want to add those can; the template stays minimal.

**Patterns to follow:**
- Existing PR titles in `gh pr list --state merged --limit 5` — short, action-led.
- `CLAUDE.md` "Creating pull requests" section format.

**Test scenarios:**
- Test expectation: none — markdown template, no behavior.

**Verification:**
- `.github/PULL_REQUEST_TEMPLATE.md` exists.
- Opening a draft PR via `gh pr create --draft` (or the GitHub web UI) pre-fills the body with the template.
- The template renders as valid markdown in the GitHub PR editor (no broken sections, no escaped headings).

---

- U4. **Marketplace polish: README badges + plugin.json screenshot pointer (if schema supports)**

**Goal:** Add CI status + license badges to `README.md` and, if the Claude Code plugin manifest schema supports it, a screenshot/icon pointer in `.claude-plugin/plugin.json`. Otherwise ship badges only and defer the manifest update.

**Requirements:** R4, R5

**Dependencies:** None

**Files:**
- Modify: `README.md` (insert badges below the H1, above the hero GIF reference at line 7)
- Modify: `.claude-plugin/plugin.json` (only if the schema supports `screenshots[]` or `icon` — see Deferred to Follow-Up Work)

**Approach:**
- Verify the Claude Code plugin manifest schema before touching `plugin.json`. If the schema is undocumented or doesn't support a screenshot field, ship README badges only and open a follow-up issue (do not invent unsupported keys).
- README badges: two badges, `flat` style, on a single line, in this order: CI status (`https://img.shields.io/github/actions/workflow/status/sebastianbreguel/claude-engram/test.yml?branch=main&label=tests&style=flat`), license (`https://img.shields.io/github/license/sebastianbreguel/claude-engram?style=flat`).
- Each badge wraps a link: CI badge → `https://github.com/sebastianbreguel/claude-engram/actions/workflows/test.yml`; license badge → `LICENSE`.
- Place badges immediately under the `# Claude-engram` H1, on their own line, with one blank line above and below. Do not push the existing tagline ("**Claude forgets everything between sessions.**...") down further than necessary.
- If `plugin.json` does support a screenshot field: add `"screenshots": ["demo/readme-hero-focus.gif"]` (relative to repo root, raw GitHub URL constructed by the marketplace, not hardcoded). Do not change any other key.

**Patterns to follow:**
- Existing `README.md` markdown style (no HTML, just markdown image links).
- `.claude-plugin/plugin.json` 2-space indentation, double-quoted keys.

**Test scenarios:**
- Happy path: push branch, open the GitHub README, see two badges rendering with live status (tests = passing/failing matches CI, license = MIT).
- Edge case: badge URLs handle a missing/private workflow gracefully (Shields.io returns "unknown" rather than breaking the page).
- Test expectation: no automated test — pure visual + manifest validity. JSON validity verified by the existing `gh repo view` flow.

**Verification:**
- `README.md` H1 area renders two badges in the GitHub UI.
- `cat .claude-plugin/plugin.json | python -c "import json,sys; json.load(sys.stdin)"` parses cleanly (no JSON syntax breakage).
- `uv run pytest -q` still green (no test touches the manifest's structure beyond `test_version_matches_plugin_manifest`, which only reads the `version` field).
- If a `plugin.json` field was added: a follow-up to manually validate the marketplace listing renders the screenshot once published.

---

## System-Wide Impact

- **Interaction graph:** None. No `tools/*.py` change, no hook change, no schema change, no DB change. Pure docs + manifest surface.
- **Error propagation:** N/A — no code paths added or modified.
- **State lifecycle risks:** None.
- **API surface parity:** `plugin.json` schema is the only consumer-facing surface that could be touched in U4. If the schema doesn't support new fields, U4 declines to add them.
- **Integration coverage:** Existing `test_version_matches_plugin_manifest` reads `version` from `plugin.json` — verify any U4 manifest edit doesn't break that read.
- **Unchanged invariants:** `tools/engram.py` flows (`_on_session_start`, `_on_executive`, `_on_precompact`, `_on_user_prompt`), banner output bytes, schema version (PRAGMA `user_version=2`), CLI flags, `~/.claude/memory.db` shape, `~/.claude/patterns/` wiki format, executive cache file path layout.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| `plugin.json` schema rejects an invented key (e.g., `screenshots[]` not yet supported) and breaks the marketplace listing on next install | U4 verifies the schema before touching `plugin.json`. If unsupported, ship README badges only and open a follow-up issue. Existing `test_version_matches_plugin_manifest` catches obvious JSON corruption locally. |
| `CONTRIBUTING.md` paraphrases `CLAUDE.md` rules and drifts over time | Quote `CLAUDE.md` rules verbatim where possible; treat the maintainer's `CLAUDE.md` as the single source of truth and have `CONTRIBUTING.md` cite it for advanced cases. |
| PR template too opinionated and discourages drive-by fixes | Keep template to two H2s only (`## Summary`, `## Test plan`). Anything else lives in `CONTRIBUTING.md`, not the template. |
| Closing issue #3 without a code change misses a real bug the maintainer noticed but didn't write up | U1 explicitly re-reads the three executive-cache tests and the `_on_executive` body before closing. If a gap appears, U1 raises it and stops; the close is conditional on verification, not automatic. |

---

## Documentation / Operational Notes

- After this sprint lands, `CHANGELOG.md` `## Unreleased` section should gain an entry: `### Added — CONTRIBUTING.md, PR template, README CI/license badges`. Single bullet, one line each. Keep the version unreleased until the actual launch commit per memory `feedback_pre_launch_discipline`.
- No rollout, no migration, no monitoring. Pure docs/manifest sprint.
- Post-merge: a manual `gh repo view sebastianbreguel/claude-engram` to confirm the GitHub community-health checklist now lights up Contributing + PR template.

---

## Sources & References

- Origin document: `repo-scout-sebastianbreguel-claude-engram.md` (this repo, root).
- Related code: `tools/engram.py:700-742` (`_on_executive`), `tests/test_engram_cli.py` (executive-cache test trio).
- Related issues: [#3](https://github.com/sebastianbreguel/claude-engram/issues/3) — closed by U1.
- Related commits: `ec8a44a`, `9ecdf19`.
- External docs: [Keep-a-Changelog 1.1](https://keepachangelog.com/en/1.1.0/), [Shields.io](https://shields.io/).
