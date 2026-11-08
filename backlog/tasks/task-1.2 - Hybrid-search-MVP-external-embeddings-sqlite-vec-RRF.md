---
id: TASK-1.2
title: 'Hybrid search MVP: external embeddings + sqlite-vec + RRF'
status: Done
assignee:
  - '@tantivy2agents_dev'
created_date: '2026-11-08T11:03:00Z'
updated_date: '2026-11-08T11:40:00Z'
labels: []
dependencies: []
parent_task_id: TASK-1
priority: medium
type: feature
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
First working hybrid search to try on real documentation repositories. Embeddings come from an external OpenAI-compatible /v1/embeddings server (run by the local model operator, EmbeddingGemma 2, 256 dims). Vectors per Markdown section are stored with sqlite-vec in idx/vectors.sqlite, built and published together with the Tantivy index under the existing exclusive index lock. Search fuses BM25 and vector ranks per path with RRF. Design notes: parent TASK-1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Without an embeddings config section, indexing and search behave exactly as before and sqlite-vec is not imported
- [x] #2 With embeddings configured, a refresh stores one vector per section in idx/vectors.sqlite, re-embeds only changed files and reuses stored vectors for unchanged chunk content
- [x] #3 search --mode hybrid fuses BM25 and vector rankings per path with RRF; --mode bm25 is the default
- [x] #4 Embedding server unreachable: the BM25 index still refreshes, missing vectors are retried later, hybrid search falls back to BM25 with a warning on stderr and stdout JSON stays valid
- [x] #5 Changing model, dimensions or templates re-embeds from stored chunk text without rebuilding the BM25 index
- [x] #6 sqlite-vec missing while embeddings are configured gives a clean CLI error with the install hint
- [x] #7 Tests with a fake local embedding server cover the cases above
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
MVP implemented (uncommitted): src/tantivy2agents/vectors.py (config, /v1/embeddings client, section chunking, sqlite-vec store with files/chunks tables and stored chunk text), agent.py refresh/search integration (vectors_online flag: only index and hybrid search call the server), cli --mode, tests/test_hybrid.py with a fake server. 207 tests pass. Next: trial on copies of CCA repository docs in tmp/ with the local embedding server.

Review fixes: VectorStore closes its connection on any init error; vector search sqlite errors fall back to BM25; sqlite-vec is loaded only for similarity, so indexing and BM25 work without it; readonly URI via Path.as_uri; default batch_size 32 (server recommends 32-64).
Trial on copies of three infrastructure repositories' indexed docs (tmp/trial, server EmbeddingGemma 2 Q8_0 via Ollama, 256 dims), scripts/eval_search.py (mise run eval-search):
- 119 docs / 1066 chunks: first embedding 46 s; hit@5 7->8/12, MRR 0.42->0.45
- 338 docs / 2157 chunks: 151 s; hit@5 7->11/14, MRR 0.41->0.53
- 1058 docs / 9018 chunks: 399 s; hit@5 13->15/16, MRR 0.63->0.77
- Warm latency: bm25 median ~0.2 s, hybrid +0.03-0.09 s.
Caveat: small hand-written query sets, written while looking at titles.
Problem found: the first embedding of the largest repo took ~400 s under the index lock; concurrent searches would hit the 120 s lock timeout. Needs a fix before real use (embed outside the lock or publish in batches).

User decision: the long index lock during the first embedding is acceptable for now; later updates are incremental (measured on the largest trial copy: one changed file -> hybrid search incl. refresh 1.5 s, next search 0.24 s).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added vectors.py (embeddings config, /v1/embeddings client with client-side Matryoshka truncation, section chunking, sqlite-vec store in idx/vectors.sqlite with stored chunk text), refresh/search integration in agent.py (only index and hybrid search call the server; BM25 fallback on server or store errors), search --mode bm25|hybrid, scripts/eval_search.py. Verified with tests/test_hybrid.py (fake server; 208 tests pass) and a trial on three real documentation sets (hybrid hit@5 and MRR equal or better than BM25, +0.03-0.09 s per search). AC 6 now: sqlite-vec is needed only for hybrid search; indexing and BM25 work without it, hybrid search gives the install hint.
<!-- SECTION:FINAL_SUMMARY:END -->
