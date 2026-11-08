---
id: TASK-1
title: 'Hybrid search: BM25 + dense vectors fused with RRF'
status: Idea
assignee: []
created_date: '2026-11-08T09:34:00Z'
labels: []
dependencies: []
type: feature
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Goal: cross-lingual search in mixed Czech/English documentation (a Czech query finds an English guide and vice versa). Combine the existing Tantivy BM25 ranking with dense-vector retrieval and fuse both rankings with Reciprocal Rank Fusion (RRF). Needs an approved design before implementation (new index data, new dependency, new search mode).

Known facts and open design points:
- Candidate model: EmbeddingGemma 2 text backbone (google/embeddinggemma-2, 270M parameters, 768 dims, Matryoshka truncation to 256 dims, context up to 8192 tokens). Verify availability, license and real multilingual quality first. Alternatives if it does not fit: BAAI/bge-m3, intfloat/multilingual-e5-small, sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2.
- Where embeddings are computed: an external local embedding server (HTTP endpoint in config) or in-process (ONNX/GGUF). BM25-only search stays the default and keeps working without the model, a GPU or the extra dependency (optional extra).
- Vector storage inside idx/ (beside the Tantivy segment files), so it is built in the build dir and published atomically by the same rename, covered by the index lock and the t2a_state.json manifest. A separate sibling directory cannot be renamed atomically together with idx/. Incremental refresh re-embeds only changed files; older indexes keep working (INDEX_STATE_FORMAT rules).
- Chunking granularity for embeddings (whole file vs. sections/outline entries), RRF constant k, per-source top-N before fusion.
- CLI: search mode as an Enum option (e.g. bm25|hybrid); keep the existing JSON output keys stable.
- Evaluation: a small CZ/EN query set with expected hits, comparing BM25 vs. hybrid before recommending hybrid.
<!-- SECTION:DESCRIPTION:END -->
