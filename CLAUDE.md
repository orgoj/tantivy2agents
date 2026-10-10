# Tantivy2agents Agent Notes

Keep this file short. Put user-facing docs in `README.md`, release history in
`CHANGELOG.md`, and open work in `TODO.md`.

## Commands

- Install dev tools: `mise run install`
- Test suite: `mise run test`
- Lint/format hooks: `mise run pre-commit` (`git add` new files first;
  untracked files are skipped)
- User install: `mise run install-user`

## Project Rules

- Use Typer for CLI commands in `src/tantivy2agents/cli.py`.
- Keep the CLI flat; do not introduce command groups without a clear need.
- Use `OutputFormat` or another Enum for fixed choices.
- Prefer `CLIError` subclasses for user-facing failures. `agent.py` still has
  legacy `print()`/`sys.exit()` paths; do not add more.
- Add permanent tests in `tests/` for bug fixes and behavior changes.
- Keep `README.md` and `CHANGELOG.md` current when behavior changes.
- Bump versions with `mise run bump -- patch|minor|major|X.Y.Z`
  (`scripts/bump_version.py`), never by hand-editing the two version strings.
- Any index read or write must go through the index lock (`locking.py`).
  Never delete or rebuild `idx/` in place; build beside it and publish with a
  rename.
- Windows and macOS are supported but untested on real machines. Route path
  walking, separators and containment checks through `paths.py`, never compare
  against `"/"` or call `commonpath` directly, and cover Windows rules in
  `tests/test_portability.py` using `ntpath`.

## Tantivy API Gotchas

- Tantivy `Document` has no `.get()`. Use `doc[key]`.
- Missing fields return `[]`, not `KeyError`.
- Schema is not iterable. Use `parse_query(query, None)` to search all fields.
- Handle missing fields gracefully for older indexes.

## Packaged Skill Docs

The CLI prints packaged docs from `src/tantivy2agents/skills/*/SKILL.md`.
Do not maintain duplicate skill documentation copies elsewhere.

## Agent Skills

Repo-local agent workflow skills belong under `.agents/skills/` and should be
committed. Keep `.claude/skills` as the tracked symlink to `.agents/skills`.

Do not put internal agent workflow skills under `src/tantivy2agents/skills/`.
That package directory is only for CLI-distributed `skill-usage` and
`skill-setup` documentation.
