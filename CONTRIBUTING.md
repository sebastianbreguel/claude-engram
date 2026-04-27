# Contributing to claude-engram

Thanks for the interest. This is a small pre-launch project; contributions land fast when they follow the repo's conventions.

## Setup

Requires [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/sebastianbreguel/claude-engram.git
cd claude-engram
./install.sh        # copies tools to ~/.claude/, registers hooks
```

After editing anything under `tools/`, re-run `./install.sh` to redeploy to `~/.claude/`. Tests run against the repo copy; hooks run against the installed copy. The two will silently diverge if you skip the install step.

## Running tests

```bash
uv run pytest -q
```

The full suite (~106 tests) should stay green on `main` and on every PR. CI runs the same command — `.github/workflows/test.yml`.

If a single test is failing locally, narrow the run:

```bash
uv run pytest tests/test_engram_cli.py -k <name> -v
```

## Linting and formatting

```bash
uv run ruff check .
uv run ruff format --check .
```

Both must pass before opening a PR. CI runs both. Settings live in `pyproject.toml` (`line-length = 140`, `quote-style = "double"`). Long lines are intentionally permitted in `tools/engram.py`, `tools/memcapture.py`, and `tests/test_e2e.py` for prompts, SQL, and formatted output — don't reformat them blindly.

## Pre-commit (optional but recommended)

```bash
uv run pre-commit run --all-files
```

## Commit conventions

Use conventional prefixes used elsewhere in the repo:

- `feat:` — new user-visible capability
- `fix:` — bug fix
- `chore:` — repo housekeeping, deps, CI
- `docs:` — documentation only
- `refactor:` — internal restructure, no behavior change
- `perf:` — measurable performance change
- `cleanup:` — small dead-code or noise removal

Keep messages short. The body, when present, should explain *why* the change was made — not what (the diff already shows that).

## What we don't accept

- **No `Co-Authored-By` lines** in commit messages.
- **No "Generated with Claude Code" / "🤖 Generated with..." attribution lines** in commits, PR bodies, or any output.
- **No `pip` / `python` / `python3` invocations** — `uv run` is the only Python entry point. The repo assumes `uv`-managed environments end-to-end.
- **No `--no-verify` / `--no-gpg-sign`** to bypass hooks. If a hook fails, fix the cause.
- **No new top-level dependencies without discussion.** The project ships with zero runtime dependencies (Python stdlib only) and treats this as a feature.

## Pull requests

PRs target `main`. The PR template (`.github/PULL_REQUEST_TEMPLATE.md`) pre-fills `## Summary` + `## Test plan` — keep both filled in.

Smaller, focused PRs land faster than batched omnibus PRs. If a change touches multiple unrelated areas, split it.

## Reporting bugs

Open an issue with:

- What you ran (`engram <subcommand>` invocation, or which hook fired)
- What happened (stderr / log output)
- What you expected
- Output of `uv run ~/.claude/tools/engram.py verify-install` (catches repo↔install drift)

## Further reading

- [`docs/architecture.md`](docs/architecture.md) — how the hook + cache + DB pieces fit together
- [`docs/cli-reference.md`](docs/cli-reference.md) — every subcommand
- [`docs/privacy.md`](docs/privacy.md) — what's captured, what isn't, where it lives
