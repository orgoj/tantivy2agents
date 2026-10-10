---
name: todo-roadmap-workflow
description: Work through this project's TODO.md roadmap in order. Use when implementing planned refactors, correctness fixes, test stabilization, release-prep batches, or any user request to work "podle TODO"; requires removing completed TODO items, writing changes to CHANGELOG.md, running tests/checks/review, bumping version when appropriate, and committing after a completed batch.
---

# TODO Roadmap Workflow

Use this workflow for planned project work driven by `TODO.md`.

## Ground Rules

- Treat `TODO.md` as open work only. Remove completed items from it in the same change set that completes them.
- Write completed behavior changes, fixes, and workflow changes to `CHANGELOG.md`.
- Work through roadmap items in order unless the user explicitly reprioritizes.
- Do not start structural refactors while correctness and test-baseline items above them remain ambiguous.
- Keep changes surgical. Do not refactor unrelated code while satisfying a TODO item.
- If an item is only partially done, leave it in `TODO.md` and narrow its remaining acceptance criteria.

## Work Loop

1. Read `TODO.md`, `CHANGELOG.md`, and the files named by the next open item.
2. State the next item and success criteria before editing when the batch is non-trivial.
3. Implement the smallest set of code, docs, and tests needed for the item.
4. Update `TODO.md`: delete completed items; keep or tighten incomplete items.
5. Update `CHANGELOG.md`: record user-visible fixes, test stabilization, docs, and process changes.
6. Run the verification commands listed by the item. If sandbox cache paths fail, retry with cache under `/tmp`.
7. Run broader checks for the completed batch, normally `mise run test`, docs audits, and `mise run pre-commit`.
8. Review the diff yourself before finalizing: verify scope, docs, tests, TODO cleanup, changelog, and no unrelated churn.
9. Bump version for a completed release-worthy batch in both `pyproject.toml` and `src/tantivy2agents/__init__.py`.
10. Commit with a focused message after tests/checks/review/version update pass.

## Verification Defaults

Prefer these commands when relevant:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --extra dev pytest tests -q
MISE_CACHE_DIR=/tmp/mise-cache UV_CACHE_DIR=/tmp/uv-cache mise run pre-commit
```

For docs audits, scope searches to files that should be clean. `TODO.md` may mention removed items as open work; completed or user-facing docs should not.

## Completion Review

Before commit, check:

- Completed TODO items are gone from `TODO.md`.
- `CHANGELOG.md` describes what changed.
- Version bump is present when the batch is meant to be committed/released.
- Verification commands passed and failures were not hidden.
- The diff contains only work traceable to the requested TODO batch.
