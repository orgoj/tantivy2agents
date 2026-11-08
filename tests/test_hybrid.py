#!/usr/bin/env python3
"""Hybrid search: external embeddings, the vector store and RRF fusion."""

import json
import logging
import os
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from tantivy2agents import TantivyAgent  # noqa: E402
from tantivy2agents import vectors as vectors_module  # noqa: E402

SCHEMA_FIELDS = {
    "title": {"weight": 2.0, "tokenizer": "en_stem"},
    "body": {"weight": 1.0, "tokenizer": "en_stem"},
    "path": {"weight": 0.5, "tokenizer": "raw"},
}

# Words of one concept share a dimension, across languages, so a Czech
# document and an English query land close together.
CONCEPTS = {
    "cat": 0,
    "cats": 0,
    "kočka": 0,
    "kočky": 0,
    "dog": 1,
    "dogs": 1,
    "pes": 1,
    "car": 2,
    "auto": 2,
}
SERVER_DIMS = 8  # more than configured, to exercise client-side truncation


def fake_vector(text):
    vector = [0.0] * SERVER_DIMS
    for word in text.lower().replace("|", " ").split():
        vector[CONCEPTS.get(word.strip(".,:#"), 3)] += 1.0
    vector[3] = 0.1  # template words are noise, keep them small
    return vector


class FakeServer:
    """OpenAI-compatible /v1/embeddings that records every input."""

    def __init__(self):
        self.inputs = []
        self.failing = False
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if fake.failing:
                    self.send_response(503)
                    self.end_headers()
                    return
                fake.inputs.extend(body["input"])
                data = [
                    {"index": i, "embedding": fake_vector(text)}
                    for i, text in enumerate(body["input"])
                ]
                payload = json.dumps({"data": data}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}/v1/embeddings"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def documents(self):
        return [t for t in self.inputs if t.startswith("title:")]

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def server():
    fake = FakeServer()
    yield fake
    fake.stop()


def write_config(root, embeddings=None):
    config = {
        "version": "1.0",
        "index_dir": ".tantivy-data",
        "global_patterns": {"include": ["*.md"], "exclude": []},
        "index_dirs": ["docs"],
        "schema_fields": SCHEMA_FIELDS,
        "search": {"default_limit": 20, "filters": []},
        "usage": {"enabled": False},
        "auto_hook": False,
    }
    if embeddings is not None:
        config["embeddings"] = embeddings
    with open(os.path.join(root, ".tantivy2agents.json"), "w", encoding="utf-8") as f:
        json.dump(config, f)


def embeddings_config(server, **overrides):
    return {
        "url": server.url,
        "model": "fake",
        "dimensions": 4,
        "batch_size": 2,
        **overrides,
    }


def write(root, rel_path, text):
    path = os.path.join(root, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    st = os.stat(path)
    # Same-second rewrites must still count as a change.
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 10 * 10**9))
    return path


@pytest.fixture
def project(tmp_path, monkeypatch, server):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, ".git"))
    write_config(root, embeddings_config(server))
    write(root, "docs/kocky.md", "# Kočky\n\nKočka spí.\n\n## Krmení\n\nKočky jedí.\n")
    write(root, "docs/dogs.md", "# Dogs\n\nThe dog barks.\n")
    write(root, "docs/cars.md", "# Garage\n\nAuto stojí v garáži.\n")
    monkeypatch.chdir(root)
    return root


def store_path(root):
    return os.path.join(root, ".tantivy-data", "idx", vectors_module.VECTORS_FILENAME)


def store_rows(root):
    conn = sqlite3.connect(store_path(root))
    try:
        return conn.execute(
            "SELECT path, section, embedding IS NOT NULL FROM chunks ORDER BY path, id"
        ).fetchall()
    finally:
        conn.close()


def search(query, capsys, mode="hybrid"):
    capsys.readouterr()
    TantivyAgent(quiet=True).search_command(query, format_output="json", mode=mode)
    out = capsys.readouterr().out
    if out.startswith("No results"):
        return []
    return [item["path"] for item in json.loads(out)["results"]]


def test_without_embeddings_no_store_and_no_sqlite_vec(project, capsys, monkeypatch):
    write_config(project)

    def forbidden(_conn):
        raise AssertionError("sqlite-vec must not be loaded without embeddings")

    monkeypatch.setattr(vectors_module, "_load_sqlite_vec", forbidden)
    TantivyAgent(quiet=True).index_command()
    assert search("barks", capsys, mode="bm25") == ["docs/dogs.md"]
    assert not os.path.exists(store_path(project))


def test_index_stores_one_vector_per_section(project, server):
    TantivyAgent(quiet=True).index_command()
    assert store_rows(project) == [
        ("docs/cars.md", "garage", True),
        ("docs/dogs.md", "dogs", True),
        ("docs/kocky.md", "kočky", True),
        ("docs/kocky.md", "krmení", True),
    ]
    assert "title: Kočky / Krmení | text: ## Krmení\n\nKočky jedí." in server.inputs


def test_hybrid_finds_a_document_bm25_misses(project, capsys):
    TantivyAgent(quiet=True).index_command()
    assert search("cat", capsys, mode="bm25") == []
    assert search("cat", capsys)[0] == "docs/kocky.md"


def test_hybrid_fuses_both_rankings(project, capsys):
    TantivyAgent(quiet=True).index_command()
    # BM25 alone finds the dog page; vectors add the car page for "auto".
    results = search("dog auto", capsys)
    assert set(results[:2]) == {"docs/dogs.md", "docs/cars.md"}


def test_refresh_reembeds_only_changed_files(project, server, capsys):
    TantivyAgent(quiet=True).index_command()
    server.inputs.clear()
    write(project, "docs/dogs.md", "# Dogs\n\nThe dog sleeps.\n")
    search("dog", capsys)
    assert server.documents() == ["title: Dogs | text: # Dogs\n\nThe dog sleeps."]


def test_unchanged_chunks_keep_vectors_on_full_rebuild(project, server):
    TantivyAgent(quiet=True).index_command()
    server.inputs.clear()
    TantivyAgent(quiet=True).index_command(force=True)
    assert server.documents() == []
    assert all(row[2] for row in store_rows(project))


def test_server_down_keeps_bm25_working_and_retries_later(
    project, server, capsys, caplog
):
    server.failing = True
    TantivyAgent(quiet=True).index_command()
    assert store_rows(project) and not any(row[2] for row in store_rows(project))

    with caplog.at_level(logging.WARNING):
        capsys.readouterr()
        TantivyAgent(quiet=True).search_command(
            "barks", format_output="json", mode="hybrid"
        )
        out = capsys.readouterr().out
    assert [r["path"] for r in json.loads(out)["results"]] == ["docs/dogs.md"]
    assert "using BM25 only" in caplog.text

    server.failing = False
    assert search("cat", capsys)[0] == "docs/kocky.md"
    assert all(row[2] for row in store_rows(project))


def test_bm25_search_never_calls_the_server(project, server, capsys):
    TantivyAgent(quiet=True).index_command()
    server.inputs.clear()
    write(project, "docs/dogs.md", "# Dogs\n\nThe dog sleeps.\n")
    assert search("sleeps", capsys, mode="bm25") == ["docs/dogs.md"]
    assert server.inputs == []
    # The new chunk waits for the next online refresh.
    assert ("docs/dogs.md", "dogs", False) in store_rows(project)


def test_model_change_reembeds_without_bm25_rebuild(project, server, capsys):
    TantivyAgent(quiet=True).index_command()
    write_config(project, embeddings_config(server, model="other"))
    server.inputs.clear()

    agent = TantivyAgent(quiet=True)
    actions = []
    original = agent._refresh_index_locked

    def recording(*args, **kwargs):
        result = original(*args, **kwargs)
        actions.append((result.action, result.changed))
        return result

    agent._refresh_index_locked = recording
    capsys.readouterr()
    agent.search_command("cat", format_output="json", mode="hybrid")
    assert actions == [("updated", 0)]
    assert len(server.documents()) == 4
    assert json.loads(capsys.readouterr().out)["results"][0]["path"] == (
        "docs/kocky.md"
    )


def test_removed_file_drops_its_vectors(project, capsys):
    TantivyAgent(quiet=True).index_command()
    os.remove(os.path.join(project, "docs/cars.md"))
    assert "docs/cars.md" not in search("auto", capsys)
    assert "docs/cars.md" not in {row[0] for row in store_rows(project)}


def test_hybrid_without_embeddings_section_is_a_clean_error(project):
    write_config(project)
    with pytest.raises(vectors_module.CLIError, match="embeddings"):
        TantivyAgent(quiet=True).search_command("cat", mode="hybrid")


def test_missing_sqlite_vec_gives_install_hint(project, monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "sqlite_vec", None)
    # Storing chunks needs no extension, so indexing and BM25 keep working.
    TantivyAgent(quiet=True).index_command()
    assert search("barks", capsys, mode="bm25") == ["docs/dogs.md"]
    with pytest.raises(vectors_module.HybridUnavailableError) as info:
        TantivyAgent(quiet=True).search_command("cat", mode="hybrid")
    assert "tantivy2agents[hybrid]" in info.value.hint


def test_corrupt_store_is_replaced_on_refresh_and_search_falls_back(
    project, capsys, caplog
):
    TantivyAgent(quiet=True).index_command()
    with open(store_path(project), "wb") as f:
        f.write(b"not a database" * 100)
    with caplog.at_level(logging.WARNING):
        capsys.readouterr()
        TantivyAgent(quiet=True).search_command(
            "barks", format_output="json", mode="hybrid"
        )
        out = capsys.readouterr().out
    assert json.loads(out)["results"][0]["path"] == "docs/dogs.md"
    # The refresh noticed the broken store and published a rebuilt one.
    assert all(row[2] for row in store_rows(project))


def test_server_with_too_few_dimensions_is_rejected(server):
    cfg = vectors_module.embedding_config(
        {"embeddings": embeddings_config(server, dimensions=SERVER_DIMS + 1)}
    )
    with pytest.raises(vectors_module.EmbeddingError, match="dimensions"):
        vectors_module.embed_query(cfg, "cat")


def test_rrf_rewards_agreement():
    fused = vectors_module.rrf_fuse([["a", "b"], ["b", "c"]], 60)
    assert [path for path, _score in fused] == ["b", "a", "c"]


def test_long_section_is_split_at_line_ends(server):
    cfg = vectors_module.embedding_config(
        {"embeddings": embeddings_config(server, max_chunk_chars=20)}
    )
    body = "# T\n\n" + "\n".join(["word " * 3] * 4)
    chunks = vectors_module.chunk_document(cfg, "T", body)
    assert len(chunks) > 1
    assert all(c.section == "t" for c in chunks)
