# Changelog

## Unreleased

### Changed
- Consolidated 5 shell hooks into 2 inline `engram.py` invocations (`on-precompact`, `on-session-start`). Net -381 lines.
- Pass A LLM calls now use Haiku 4.5 (was Sonnet).
- Removed semantic error regex from session capture; now relies only on Claude Code's `is_error=true` tool-result signal.

### Deprecated
- `engram compile` and `~/.claude/compiled-knowledge/` markdown artifact — planned removal in v2, to be replaced by an automatic cross-project `concepts` table in `memory.db`. Use `engram export-concepts` as the migration bridge.

### Migration
Existing installs: run `./install.sh` again to migrate `settings.json` from the 5 legacy `.sh` hook entries to the 2 new `engram.py` entries. Old shell scripts are removed automatically. `memory.db` and `patterns/` are preserved.
