## Summary

<!-- 1-3 bullets. What changed and why (focus on why; the diff shows what). -->

-

## Test plan

<!-- Markdown checklist of what you ran locally. -->

- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run pytest -q`
- [ ] Manual smoke test (if behavior changed)

<!-- If this PR adds or modifies a `tools/*.py` file, re-run `./install.sh` before testing — hooks run against `~/.claude/tools/`, not the repo copy. -->
