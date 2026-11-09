---
id: TASK-1.6
title: Raise default query embedding timeout to 15 s
status: Done
assignee:
  - '@tantivy2agents_dev'
created_date: '2026-11-09T08:11:00Z'
updated_date: '2026-11-09T08:15:00Z'
labels: []
dependencies: []
parent_task_id: TASK-1
priority: medium
type: bug
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Default embeddings.search_timeout of 3 s is shorter than a cold Ollama model load (3.7-4.3 s from page cache, ~10.5 s disk-cold). A request cancelled mid-load aborts the load, so every query after the server's idle unload stays cold and hybrid search silently falls back to BM25. Raise the default to 15 s.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 DEFAULTS search_timeout in vectors.py is 15
- [x] #2 A test asserts the default search_timeout is 15 s when the config omits it
- [x] #3 README and CHANGELOG state the new default
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Default embeddings.search_timeout raised from 3 to 15 s (vectors.py DEFAULTS); regression test test_default_search_timeout_covers_a_cold_model_load failed before and passes after; README and CHANGELOG updated. mise run test 217 passed, pre-commit clean, review passed.
<!-- SECTION:FINAL_SUMMARY:END -->
