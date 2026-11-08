---
id: TASK-1
title: 'Hybrid search: BM25 + dense vectors fused with RRF'
status: Idea
assignee: []
created_date: '2026-11-08T09:34:00Z'
updated_date: '2026-11-08T10:39:00Z'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
User decisions: embeddings come only from an external model server; tantivy2agents gets a generic connector to external embedding models and only stores the vectors, managed like the Tantivy index (built beside, published by rename, incremental).

Proposed design (not yet approved):
- Connector: OpenAI-compatible POST /v1/embeddings (llama.cpp server, Ollama, vLLM, LM Studio, TEI and hosted APIs speak it). Config in .tantivy2agents.json, e.g. embeddings: {url, model, dimensions, query_prefix, document_prefix, api_key_env}. Off by default; a hosted URL sends indexed content to a third party, docs must say so. Server unreachable at search time: fall back to BM25 with a warning.
- Storage: no database. Tantivy has no dense-vector field, and vector databases (LanceDB, Qdrant, Chroma, sqlite-vec) are heavy dependencies for brute-force sizes. Inside idx/: one float16 matrix (N x dims, .npy) plus a row map (chunk -> path, section, content hash). Search is a numpy matrix product (100k chunks x 256 dims = ~50 MB, milliseconds). numpy as optional extra.
- Incremental: rows keyed by chunk content hash; a rebuild copies unchanged rows from the published matrix and embeds only new chunks. Model id, dimensions and prefixes go into the config fingerprint, so a model change re-embeds everything once.
- Revisit with an ANN index (hnswlib/usearch) only past roughly a million chunks.

Review points to settle when specifying:
- Row map must load fast on every search call: not one large JSON; parallel numpy arrays or stored fields, measured at 100k chunks.
- Store L2-normalized vectors so similarity is a plain dot product; load with mmap and close it inside the locked search scope (Windows cannot rename idx/ with open handles).
- Missing numpy with embeddings enabled: clean CLIError with the install hint, no ImportError.
- Connector: stdlib urllib with a short search-time timeout (seconds); batch document requests; respect the model's max input length; truncate Matryoshka dimensions client-side (servers may ignore or reject the dimensions parameter) and reject a vector shorter than configured.
- Fusion granularity: BM25 ranks files; aggregate chunk ranks per path (best chunk), fuse with RRF per path, use the best chunk for section/snippet output.
- Fallback warning goes to stderr only; JSON on stdout stays valid.
- Fingerprint: model, dimensions and prefixes, not the URL (same model on another host must not re-embed). Bump INDEX_STATE_FORMAT if BM25 documents change too.
<!-- SECTION:NOTES:END -->
