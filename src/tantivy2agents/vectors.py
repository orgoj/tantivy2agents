"""Dense vectors for hybrid search: external embeddings and their store.

Embeddings come from an OpenAI-compatible ``/v1/embeddings`` server; this
module only chunks documents, asks the server for vectors and keeps them in a
SQLite file inside ``idx/``. The file is built in the build directory with the
Tantivy index and published by the same rename, under the same exclusive index
lock, so no other process reads it while it is written.

Similarity uses the ``vec_distance_cosine`` function of the ``sqlite-vec``
extension over every stored vector (a flat scan), which is fast enough for
the repository sizes this tool indexes.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import sqlite3
import struct
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from .exceptions import CLIError, ConfigError
from .sections import parse_outline, split_lines

logger = logging.getLogger(__name__)

VECTORS_FILENAME = "vectors.sqlite"
STORE_FORMAT = 1
INSTALL_HINT = 'Install the hybrid extra: uv tool install "tantivy2agents[hybrid]"'

DEFAULTS = {
    "query_template": "task: search result | query: {query}",
    "document_template": "title: {title} | text: {content}",
    "timeout": 30.0,
    "search_timeout": 15.0,
    "batch_size": 32,
    "max_chunk_chars": 4000,
    "rrf_k": 60,
    "api_key_env": None,
}


class EmbeddingError(Exception):
    """The embedding server could not produce vectors right now."""


class HybridUnavailableError(CLIError):
    """Hybrid search was requested but cannot run in this installation."""

    def __init__(self, message: str, hint: Optional[str] = None):
        super().__init__(message=message, hint=hint)


@dataclass(frozen=True)
class EmbeddingConfig:
    url: str
    model: str
    dimensions: int
    query_template: str
    document_template: str
    timeout: float
    search_timeout: float
    batch_size: int
    max_chunk_chars: int
    rrf_k: int
    api_key_env: Optional[str]

    @property
    def key(self) -> str:
        """Settings that change the vectors; the URL does not."""
        relevant = {
            "model": self.model,
            "dimensions": self.dimensions,
            "document_template": self.document_template,
            "query_template": self.query_template,
            "max_chunk_chars": self.max_chunk_chars,
            "format": STORE_FORMAT,
        }
        return hashlib.sha256(
            json.dumps(relevant, sort_keys=True).encode("utf-8")
        ).hexdigest()


def embedding_config(config: dict[str, Any]) -> Optional[EmbeddingConfig]:
    """Return the validated ``embeddings`` section, or None when it is absent."""
    section = config.get("embeddings")
    if section is None:
        return None
    if not isinstance(section, dict):
        raise ConfigError("'embeddings' must be an object")
    values = {**DEFAULTS, **section}
    for key in ("url", "model"):
        if not isinstance(values.get(key), str) or not values[key]:
            raise ConfigError(f"'embeddings.{key}' must be a non-empty string")
    dims = values.get("dimensions")
    if type(dims) is not int or dims <= 0:
        raise ConfigError("'embeddings.dimensions' must be a positive integer")
    for key in ("batch_size", "max_chunk_chars", "rrf_k"):
        if type(values[key]) is not int or values[key] <= 0:
            raise ConfigError(f"'embeddings.{key}' must be a positive integer")
    for key in ("timeout", "search_timeout"):
        if not isinstance(values[key], (int, float)) or values[key] <= 0:
            raise ConfigError(f"'embeddings.{key}' must be a positive number")
    if "{query}" not in values["query_template"]:
        raise ConfigError("'embeddings.query_template' must contain {query}")
    if "{content}" not in values["document_template"]:
        raise ConfigError("'embeddings.document_template' must contain {content}")
    return EmbeddingConfig(
        url=values["url"],
        model=values["model"],
        dimensions=dims,
        query_template=values["query_template"],
        document_template=values["document_template"],
        timeout=float(values["timeout"]),
        search_timeout=float(values["search_timeout"]),
        batch_size=values["batch_size"],
        max_chunk_chars=values["max_chunk_chars"],
        rrf_k=values["rrf_k"],
        api_key_env=values["api_key_env"],
    )


# --- embedding client -------------------------------------------------------


def _normalize(vector: list[float], dims: int) -> list[float]:
    """Truncate to ``dims`` (Matryoshka) and scale to unit length."""
    if len(vector) < dims:
        raise EmbeddingError(
            f"server returned {len(vector)} dimensions, {dims} are configured"
        )
    vector = [float(v) for v in vector[:dims]]
    norm = math.sqrt(sum(v * v for v in vector))
    if not norm or not math.isfinite(norm):
        raise EmbeddingError("server returned a zero or invalid vector")
    return [v / norm for v in vector]


def embed_texts(
    cfg: EmbeddingConfig, texts: list[str], timeout: float
) -> list[list[float]]:
    """Ask the server for one vector per text, in order."""
    payload = json.dumps({"model": cfg.model, "input": texts}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if cfg.api_key_env and os.environ.get(cfg.api_key_env):
        headers["Authorization"] = f"Bearer {os.environ[cfg.api_key_env]}"
    request = urllib.request.Request(cfg.url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise EmbeddingError(f"embedding server {cfg.url}: {e}") from e
    try:
        items = sorted(body["data"], key=lambda item: item.get("index", 0))
        vectors = [item["embedding"] for item in items]
    except (KeyError, TypeError, AttributeError) as e:
        raise EmbeddingError("unexpected response from the embedding server") from e
    if len(vectors) != len(texts):
        raise EmbeddingError(
            f"server returned {len(vectors)} vectors for {len(texts)} inputs"
        )
    return [_normalize(v, cfg.dimensions) for v in vectors]


def embed_query(cfg: EmbeddingConfig, query: str) -> list[float]:
    text = cfg.query_template.replace("{query}", query)
    return embed_texts(cfg, [text], cfg.search_timeout)[0]


# --- chunking ---------------------------------------------------------------


@dataclass(frozen=True)
class Chunk:
    section: str  # section slug, "" for the whole document
    text: str  # text sent to the server, template applied


def _split_long(text: str, limit: int) -> list[str]:
    """Cut text into pieces of at most ``limit`` characters at line ends."""
    pieces, current = [], ""
    for line in text.split("\n"):
        while len(line) > limit:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            pieces.append(current)
            current = line
        else:
            current = candidate
    if current.strip():
        pieces.append(current)
    return [p for p in pieces if p.strip()]


def chunk_document(cfg: EmbeddingConfig, doc_title: str, body: str) -> list[Chunk]:
    """One chunk per Markdown section (heading to next heading).

    ``body`` is the document text without frontmatter. Section slugs match
    the ones ``outline`` and ``read --section`` use.
    """
    lines = split_lines(body)
    outline = parse_outline(body)
    starts = [(s.start, s.slug, s.title) for s in outline.sections]
    parts: list[tuple[str, str, str]] = []  # slug, title, text
    first = starts[0][0] if starts else len(lines) + 1
    preamble = "\n".join(lines[: first - 1])
    if preamble.strip():
        parts.append(("", doc_title, preamble))
    for index, (start, slug, title) in enumerate(starts):
        end = starts[index + 1][0] - 1 if index + 1 < len(starts) else len(lines)
        text = "\n".join(lines[start - 1 : end])
        if text.strip():
            heading = f"{doc_title} / {title}" if title != doc_title else doc_title
            parts.append((slug, heading, text))

    chunks = []
    for slug, title, text in parts:
        for piece in _split_long(text, cfg.max_chunk_chars):
            rendered = cfg.document_template.replace("{title}", title or "none")
            chunks.append(Chunk(slug, rendered.replace("{content}", piece)))
    return chunks


# --- store ------------------------------------------------------------------


def require_sqlite_vec():
    """Import sqlite-vec or fail with the install hint."""
    try:
        import sqlite_vec
    except ImportError as e:
        raise HybridUnavailableError(
            "Hybrid search needs the sqlite-vec package", hint=INSTALL_HINT
        ) from e
    return sqlite_vec


def _load_sqlite_vec(conn: sqlite3.Connection) -> None:
    sqlite_vec = require_sqlite_vec()
    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except (AttributeError, sqlite3.Error) as e:
        raise HybridUnavailableError(
            f"This Python cannot load SQLite extensions: {e}",
            hint="Use a Python build with SQLite extension loading enabled",
        ) from e


def _pack(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


class VectorStore:
    """Chunks, their text and their vectors in one SQLite file.

    Opened only under the index lock; close it before the lock is released
    (Windows cannot rename a directory with an open file).
    """

    def __init__(self, path: str, cfg: EmbeddingConfig, readonly: bool = False):
        self.cfg = cfg
        self._vec_loaded = False
        if readonly:
            # The live idx/ is never written; only build directories are.
            uri = Path(os.path.abspath(path)).as_uri() + "?mode=ro"
            self.conn = sqlite3.connect(uri, uri=True)
        else:
            self.conn = sqlite3.connect(path)
        try:
            self._open(readonly)
        except Exception:
            # Windows cannot delete or rename a file that is still open.
            self.conn.close()
            raise

    def _open(self, readonly: bool) -> None:
        cfg = self.cfg
        if readonly:
            try:
                row = self.conn.execute(
                    "SELECT value FROM meta WHERE key = 'embedding_key'"
                ).fetchone()
            except sqlite3.Error:
                row = None
            self.current = row is not None and row[0] == cfg.key
            return
        self.current = True
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL,
                section TEXT NOT NULL,
                text_hash TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding BLOB
            );
            CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY);
            CREATE INDEX IF NOT EXISTS chunks_path ON chunks(path);
            CREATE INDEX IF NOT EXISTS chunks_hash ON chunks(text_hash);
            """
        )
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key = 'embedding_key'"
        ).fetchone()
        if row is None or row[0] != cfg.key:
            # Other model or settings: the stored text is re-embedded.
            self.conn.execute("UPDATE chunks SET embedding = NULL")
            self.conn.execute(
                "INSERT OR REPLACE INTO meta VALUES ('embedding_key', ?)", (cfg.key,)
            )
            self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "VectorStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def paths(self) -> set[str]:
        """Files the store has chunked, including ones without any chunk."""
        return {row[0] for row in self.conn.execute("SELECT path FROM files")}

    def remove(self, paths: Iterable[str]) -> None:
        params = [(p,) for p in paths]
        self.conn.executemany("DELETE FROM chunks WHERE path = ?", params)
        self.conn.executemany("DELETE FROM files WHERE path = ?", params)

    def replace(self, path: str, chunks: list[Chunk]) -> None:
        """Store a file's chunks, reusing vectors of unchanged chunk text."""
        rows = []
        for chunk in chunks:
            digest = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
            found = self.conn.execute(
                "SELECT embedding FROM chunks WHERE text_hash = ? "
                "AND embedding IS NOT NULL LIMIT 1",
                (digest,),
            ).fetchone()
            rows.append((path, chunk.section, digest, chunk.text, found and found[0]))
        self.conn.execute("DELETE FROM chunks WHERE path = ?", (path,))
        self.conn.execute("INSERT OR IGNORE INTO files VALUES (?)", (path,))
        self.conn.executemany(
            "INSERT INTO chunks (path, section, text_hash, text, embedding) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )

    def pending(self) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE embedding IS NULL"
        ).fetchone()[0]

    def texts(self) -> dict[str, str]:
        """Text of every chunk, by text hash."""
        return dict(self.conn.execute("SELECT text_hash, text FROM chunks").fetchall())

    def pending_texts(self) -> dict[str, str]:
        """Text of every chunk still without a vector, by text hash."""
        return dict(
            self.conn.execute(
                "SELECT text_hash, text FROM chunks WHERE embedding IS NULL"
            ).fetchall()
        )

    def apply(self, vectors: dict[str, bytes]) -> int:
        """Store vectors for pending chunks by text hash; return pending left.

        Never calls the server: vectors are computed beforehand without the
        index lock (``embed_pending``).
        """
        self.conn.executemany(
            "UPDATE chunks SET embedding = ? WHERE text_hash = ? AND embedding IS NULL",
            [(blob, h) for h, blob in vectors.items()],
        )
        self.conn.commit()
        return self.pending()

    def commit(self) -> None:
        self.conn.commit()

    def search(self, vector: list[float], limit: int) -> list[tuple[str, str, float]]:
        """Best chunks as (path, section, cosine distance), closest first."""
        if not self._vec_loaded:
            # Only similarity needs the extension; storing chunks does not.
            _load_sqlite_vec(self.conn)
            self._vec_loaded = True
        return self.conn.execute(
            "SELECT path, section, vec_distance_cosine(embedding, ?) AS d "
            "FROM chunks WHERE embedding IS NOT NULL ORDER BY d LIMIT ?",
            (_pack(vector), limit),
        ).fetchall()


# Written by 0.12.0, which staged vectors there; a refresh deletes it.
LEGACY_CACHE_FILENAME = "vectors-cache.sqlite"


def embed_pending(cfg: EmbeddingConfig, texts: dict[str, str]) -> dict[str, bytes]:
    """Embed texts by hash, in batches; stop at the first server error.

    Called without the index lock. Returns the vectors computed so far;
    the rest stays pending for the next refresh.
    """
    hashes = list(texts)
    vectors: dict[str, bytes] = {}
    for start in range(0, len(hashes), cfg.batch_size):
        batch = hashes[start : start + cfg.batch_size]
        try:
            result = embed_texts(cfg, [texts[h] for h in batch], cfg.timeout)
        except EmbeddingError as e:
            logger.debug("Vectors not complete, will retry: %s", e)
            break
        vectors.update((h, _pack(v)) for h, v in zip(batch, result))
    return vectors


def rrf_fuse(rankings: list[list[str]], k: int) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion of path rankings, best first."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, path in enumerate(ranking, start=1):
            scores[path] = scores.get(path, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def best_by_path(hits: list[tuple[str, str, float]]) -> list[tuple[str, str]]:
    """Collapse chunk hits to (path, best section), closest path first."""
    seen: dict[str, str] = {}
    for path, section, _distance in hits:
        seen.setdefault(path, section)
    return list(seen.items())
