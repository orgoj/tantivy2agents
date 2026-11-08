---
id: TASK-1.4
title: Per-user hybrid config and default search mode
status: Done
assignee:
  - '@tantivy2agents_dev'
created_date: '2026-11-08T12:29:00Z'
updated_date: '2026-11-08T12:36:00Z'
labels: []
dependencies: []
parent_task_id: TASK-1
priority: medium
type: feature
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
User request: try hybrid search in chosen projects without changing anything in them and without their agents noticing; they should just get better results. Per-user config supplies embeddings and search.default_mode for listed project roots; a default hybrid falls back to BM25 silently; index embeds outside the index lock so the first embedding of a large repository does not block searches.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A per-user config file with a projects list supplies embeddings and search.default_mode for those projects only; project config values win; project files are not modified
- [x] #2 With default_mode hybrid, search without --mode uses hybrid and falls back to BM25 without any warning when the server, vectors or sqlite-vec are missing
- [x] #3 index calls the embedding server only while the index lock is not held
- [x] #4 A hybrid search embeds at most embeddings.max_fill_per_search sections under the lock
- [x] #5 Tests cover the cases above
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Per-user config (config.apply_user_config, projects list required) supplies embeddings and search.default_mode; default hybrid falls back to BM25 at debug level; index embeds through vectors-cache.sqlite outside the lock and the locked phase only copies cache hits; hybrid search embeds at most max_fill_per_search sections under the lock. Covered by tests/test_hybrid.py (215 tests pass); reviewed.
<!-- SECTION:FINAL_SUMMARY:END -->
