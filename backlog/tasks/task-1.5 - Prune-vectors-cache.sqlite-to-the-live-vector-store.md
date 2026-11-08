---
id: TASK-1.5
title: Unify search auto-refresh and index; drop the vector cache file
status: Done
assignee:
  - '@tantivy2agents_dev'
created_date: '2026-11-08T13:13:00Z'
updated_date: '2026-11-08T13:45:00Z'
labels: []
dependencies: []
parent_task_id: TASK-1
priority: low
type: enhancement
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
User: the auto-refresh in search did something different from index; unify them so nothing extra has to be managed. vectors-cache.sqlite only grew (searches also wrote it) and was needed only because index embedded outside the lock while search embedded up to max_fill_per_search sections under the lock. Change: one refresh path for both: under the lock refresh BM25 and chunks and read the pending section texts; without the lock embed them; under the lock apply the vectors (kept in memory) and publish. No cache file, no per-search limit; a leftover vectors-cache.sqlite is deleted by the next refresh.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 search and index refresh vectors through the same code path and call the embedding server only while the index lock is not held
- [x] #2 No vectors-cache.sqlite is created; a leftover one is deleted by the next refresh
- [x] #3 Changed sections get vectors on the next search without any per-search limit
- [x] #4 Tests cover the cases above
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
One vector refresh path (_refresh_vectors) for index and the hybrid-search auto-refresh: locked refresh + pending texts, unlocked embed_pending, locked apply and publish. Removed vectors-cache.sqlite (leftover deleted by the next refresh) and max_fill_per_search. Tests: index and search-only flows call the server only without the lock, leftover cache removed; 216 pass; reviewed.
<!-- SECTION:FINAL_SUMMARY:END -->
