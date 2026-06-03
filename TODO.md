# TODO

This file tracks open work only. Completed items belong in `CHANGELOG.md`.

## Refactor Roadmap

Work in order. Do not start the structural refactor while the basic behavior and
test baseline are ambiguous.

## Assumptions and Non-Goals

- Default search result limit is intentionally `5`, not `10`.
- Do not delete ignored local artifacts (`.venv/`, caches, local agent settings)
  just for cleanliness.
- Do not restore duplicate `.claude/skills` docs; packaged skills are the source
  of truth.
- Do not add command groups unless there is a separate approved design.
- Do not refactor unrelated code while fixing tests or defaults.

## Phase 1: Test Suite Stabilization

## Phase 2: Error Handling Cleanup

## Phase 3: Decompose `agent.py`

## Phase 4: CLI and UX Polish

## Phase 5: Safety and Maintenance

No open roadmap items.
