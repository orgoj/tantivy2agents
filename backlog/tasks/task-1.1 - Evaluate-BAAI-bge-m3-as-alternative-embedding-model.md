---
id: TASK-1.1
title: Evaluate BAAI/bge-m3 as alternative embedding model
status: Idea
assignee: []
created_date: '2026-11-08T10:54:00Z'
labels: []
dependencies: []
parent_task_id: TASK-1
type: spike
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Candidate alternative to EmbeddingGemma 2 for hybrid search: BAAI/bge-m3 (568M, 8192 tokens, strong Czech). Besides dense vectors it returns sparse lexical weights that could be mapped into the Tantivy inverted index, but /v1/embeddings does not return them, so it would need another connector. Deferred by the user; not part of the first hybrid search implementation. Needs analysis before implementation.
<!-- SECTION:DESCRIPTION:END -->
