# Tantivy2agents Agent Notes

Keep this file short. Put user-facing docs in `README.md`, release history in
`CHANGELOG.md`, and open work in `TODO.md`.

## Commands

- Install dev tools: `mise run install`
- Test suite: `mise run test`
- Lint/format hooks: `mise run pre-commit`
- User install: `mise run install-user`

## Project Rules

- Use Typer for CLI commands in `src/tantivy2agents/cli.py`.
- Keep the CLI flat; do not introduce command groups without a clear need.
- Use `OutputFormat` or another Enum for fixed choices.
- Prefer `CLIError` subclasses for user-facing failures. `agent.py` still has
  legacy `print()`/`sys.exit()` paths; do not add more.
- Add permanent tests in `tests/` for bug fixes and behavior changes.
- Keep `README.md` and `CHANGELOG.md` current when behavior changes.
- Bump both `pyproject.toml` and `src/tantivy2agents/__init__.py` for releases.

## Tantivy API Gotchas

- Tantivy `Document` has no `.get()`. Use `doc[key]`.
- Missing fields return `[]`, not `KeyError`.
- Schema is not iterable. Use `parse_query(query, None)` to search all fields.
- Handle missing fields gracefully for older indexes.

## Packaged Skill Docs

The CLI prints packaged docs from `src/tantivy2agents/skills/*/SKILL.md`.
Do not maintain duplicate skill documentation copies elsewhere.
