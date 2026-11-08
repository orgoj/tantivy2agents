import os

import pytest


@pytest.fixture(autouse=True)
def _no_user_config(tmp_path_factory, monkeypatch):
    """Keep the developer's own user config out of every test."""
    missing = tmp_path_factory.mktemp("user-config") / "config.json"
    monkeypatch.setenv("TANTIVY2AGENTS_USER_CONFIG", os.fspath(missing))
