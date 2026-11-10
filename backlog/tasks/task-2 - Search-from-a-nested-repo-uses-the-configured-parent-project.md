---
id: TASK-2
title: Search from a nested repo uses the configured parent project
status: Done
assignee: []
created_date: '2026-11-10T10:02:00Z'
updated_date: '2026-11-10T10:15:00Z'
labels:
  - bug
dependencies: []
priority: high
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Running a command inside a nested git repository without its own .tantivy2agents.json picked the nested .git as project root, built a default index there (all files incl. tmp/ and vendor/) and, under the hybrid user config, embedded it all synchronously in the first search (15+ min). User decision: the root is found only by .tantivy2agents.json; .git plays no part; without a config the index commands fail.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Nearest ancestor with .tantivy2agents.json is the project root; .git is ignored
- [x] #2 A nested repo with its own config stays its own project
- [x] #3 Without a config above, index-touching commands fail and create no files
- [x] #4 Regression tests in tests/, incl. Windows path walk; README and CHANGELOG updated
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented in working tree; review sent to agent_review (diff tmp/task-2-review.diff). Cleanup done: removed stray default index .tantivy-data in the nested repo (user order). After review: commit, bump patch, tag, install with the user's word so agents get the fix.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Project root is found only by .tantivy2agents.json (git ignored); index-touching CLI commands fail without a config instead of building a default index. Regression tests for nested repos, Windows walk and no-config CLI. Stray index in the reported nested repo removed. Review PASS.
<!-- SECTION:FINAL_SUMMARY:END -->
