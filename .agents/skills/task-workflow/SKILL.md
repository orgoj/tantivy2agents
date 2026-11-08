---
name: task-workflow
description: Work on this project's Backlog.md tasks (`backlog/`). Use when implementing a backlog task, planned refactors, correctness fixes, test stabilization or release-prep batches, or any request to work on a TASK-n; requires updating the task through the backlog CLI, writing changes to CHANGELOG.md, running tests/checks/review, bumping the version when appropriate, and committing the task file with the work.
---

# Task Workflow

Open work lives in Backlog.md tasks under `backlog/`, managed only through the
`backlog` CLI (`backlog task list --plain`, `backlog task view TASK-n --plain`,
`backlog task edit ...`). Never hand-edit task files.

## Ground Rules

- A task with status `Idea` is not specified yet: specify it (goal, scope,
  acceptance criteria, plan) before implementing it.
- Set `In Progress` before the first edit; set `Done` with a final summary and
  checked acceptance criteria only when the work is verified.
- Commit the task file in the same commit as the work.
- Write completed behavior changes, fixes, and workflow changes to `CHANGELOG.md`.
- Keep changes surgical. Do not refactor unrelated code while working on a task.
- If a task is only partially done, keep it open and narrow its remaining
  acceptance criteria.

## Work Loop

1. Read the task, `CHANGELOG.md`, and the files the task names.
2. State the success criteria before editing when the batch is non-trivial.
3. Implement the smallest set of code, docs, and tests needed for the task.
4. Update `CHANGELOG.md`: record user-visible fixes, test stabilization, docs,
   and process changes.
5. Run the verification commands named by the task, then `mise run test` and
   `mise run pre-commit`.
6. Review the diff yourself: scope, docs, tests, changelog, no unrelated churn.
7. Bump the version for a release-worthy batch with
   `mise run bump -- patch|minor|major|X.Y.Z`.
8. Close the task (`--check-ac`, `--final-summary`, `-s Done`) and commit it
   with the work after tests, checks and review pass.

## Completion Review

Before commit, check:

- The task's acceptance criteria literally match the implementation and tests.
- `CHANGELOG.md` describes what changed.
- Version bump is present when the batch is meant to be released.
- Verification commands passed and failures were not hidden.
- The diff contains only work traceable to the task.
