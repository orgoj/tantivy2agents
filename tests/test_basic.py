#!/usr/bin/env python3
"""
Basic tests for Tantivy Agent functionality
"""

import os
import sys
import json
import tempfile
import subprocess

# Add src to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from tantivy2agents import TantivyAgent
from tantivy2agents.exceptions import ValidationError


def run_test(test_name, test_func):
    """Run a test function and report results"""
    try:
        test_func()
        print(f"  {test_name}")
        return True
    except Exception as e:
        import traceback

        print(f"  {test_name}: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def run_cli_command(args, cwd=None):
    """Run tantivy2agents CLI command using python -m"""
    cmd = [sys.executable, "-m", "tantivy2agents"] + args
    env = os.environ.copy()
    # Add src to PYTHONPATH for subprocess
    src_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=env)


def test_basic_functionality():
    """Test basic agent functionality"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test config
        config = {
            "version": "1.0",
            "index_dir": ".tantivy-data",
            "global_patterns": {"include": ["*.md", "*.txt"], "exclude": ["*.tmp"]},
            "index_dirs": ["docs/"],
            "schema_fields": {
                "title": {"weight": 2.0, "tokenizer": "en_stem"},
                "description": {"weight": 1.5, "tokenizer": "en_stem"},
                "body": {"weight": 1.0, "tokenizer": "en_stem"},
                "tags": {"weight": 1.5, "tokenizer": "default"},
                "servers": {"weight": 1.5, "tokenizer": "default"},
                "path": {"weight": 0.5, "tokenizer": "raw"},
            },
            "search": {"default_limit": 10, "show_description": True, "filters": []},
            "auto_hook": False,  # Disable hooks for testing
        }

        config_path = os.path.join(temp_dir, ".tantivy2agents.json")
        with open(config_path, "w") as f:
            json.dump(config, f)

        # Create test documents
        docs_dir = os.path.join(temp_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)

        with open(os.path.join(docs_dir, "test1.md"), "w") as f:
            f.write("""# Test Document One

This is a test document about server configuration.

Tags: [test, server]
""")

        with open(os.path.join(docs_dir, "test2.md"), "w") as f:
            f.write("""# Guide for Testing

Complete guide for testing functionality.
""")

        # Test help command
        result = run_cli_command(["--help"], cwd=temp_dir)
        if result.returncode != 0:
            raise Exception("Help command failed")

        # Test install command
        result = run_cli_command(["install"], cwd=temp_dir)
        if result.returncode != 0:
            raise Exception(f"Install command failed: {result.stderr}")

        # Test index command
        result = run_cli_command(["index"], cwd=temp_dir)
        if result.returncode != 0:
            raise Exception(f"Index command failed: {result.stderr}")

        if "Successfully indexed" not in result.stdout:
            raise Exception("Indexing did not succeed")

        # Test search command (default output is structured text)
        result = run_cli_command(["search", "server"], cwd=temp_dir)
        if result.returncode != 0:
            raise Exception(f"Search command failed: {result.stderr}")

        if "### FILE:" not in result.stdout:
            raise Exception("Search did not return structured text results")

        # Test clear command
        result = run_cli_command(["clear"], cwd=temp_dir)
        if result.returncode != 0:
            raise Exception("Clear command failed")

        # Check that gitignore was updated
        gitignore_path = os.path.join(temp_dir, ".gitignore")
        if not os.path.exists(gitignore_path):
            raise Exception("Gitignore was not updated")


def test_config_loading():
    """Test configuration loading with defaults"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            agent = TantivyAgent()

            # Check default values
            assert agent.config["version"] == "1.0"
            assert agent.config["index_dir"] == ".tantivy-data"
            # Default includes current directory and excludes various dirs
            assert "." in agent.config["index_dirs"]
            assert "title" in agent.config["schema_fields"]

        finally:
            os.chdir(original_cwd)


def test_file_parsing():
    """Test markdown file parsing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            agent = TantivyAgent()

            # Create test markdown file with description
            with open("test.md", "w") as f:
                f.write("""---
title: Custom Title
description: Brief summary of document content
tags: [test, markdown]
servers: [web, api]

---

# Custom Title

This is the body content.
""")

            doc = agent._parse_markdown("test.md")

            assert doc is not None
            # Title is Czech-normalized, so check for stemmed version
            assert "custom" in doc["title"].lower()
            # Check description is parsed
            assert doc["description"] == "Brief summary of document content"
            assert "test markdown" in doc["tags"]
            assert "web api" in doc["servers"]
            # Body is also normalized ("body" -> "bod", "content" -> "content")
            assert "bod" in doc["body"] and "content" in doc["body"]

        finally:
            os.chdir(original_cwd)


def test_patterns():
    """Test file pattern matching"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            agent = TantivyAgent()

            # Test pattern matching
            assert agent._match_pattern("test.md", "*.md")
            assert not agent._match_pattern("test.txt", "*.md")
            assert agent._match_pattern("docs/test.md", "docs/*.md")
            assert not agent._match_pattern("test.tmp", "*.md")
            assert agent._match_pattern("test.md", "*.md")

        finally:
            os.chdir(original_cwd)


def test_export_functionality():
    """Test result export functionality"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            agent = TantivyAgent()

            # Create mock document object that simulates Tantivy doc
            # Tantivy doc[key] returns [] for missing fields, not KeyError
            class MockDoc:
                def __getitem__(self, key):
                    return [f"mock_value_{key}", f"second_value_{key}"]

            mock_doc = MockDoc()

            results = [(0.85, "addr1", mock_doc), (0.75, "addr2", mock_doc)]

            # Test JSON export to string
            import io
            from contextlib import redirect_stdout

            captured_output = io.StringIO()
            with redirect_stdout(captured_output):
                agent._export_json(results, "test query", None)

            output = captured_output.getvalue()
            assert '"query": "test query"' in output
            assert '"total_results": 2' in output
            assert '"score": 0.85' in output

            # Test CSV export to file
            csv_file = "test_export.csv"
            agent._export_csv(results, "test query", csv_file)

            assert os.path.exists(csv_file)
            with open(csv_file, "r") as f:
                content = f.read()
                assert "Score,Path,Title" in content
                assert "0.8500" in content

            # Test text export to file (structured format)
            txt_file = "test_export.txt"
            agent._export_text(results, "test query", txt_file)

            assert os.path.exists(txt_file)
            with open(txt_file, "r") as f:
                content = f.read()
                assert "### FILE:" in content
                assert "SCORE:" in content
                assert "---" in content

        finally:
            os.chdir(original_cwd)


def test_project_detection():
    """Test project type detection"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        try:
            # Test Python project detection
            python_dir = os.path.join(temp_dir, "python-project")
            os.makedirs(python_dir)
            os.chdir(python_dir)
            with open("requirements.txt", "w") as f:
                f.write("flask==2.0\n")
            os.makedirs("src", exist_ok=True)

            agent = TantivyAgent()
            agent.project_root = python_dir
            project_type = agent._detect_project_type()
            assert project_type == "python"

            # Test Node.js project detection
            nodejs_dir = os.path.join(temp_dir, "nodejs-project")
            os.makedirs(nodejs_dir)
            os.chdir(nodejs_dir)
            with open("package.json", "w") as f:
                f.write('{"name": "test", "version": "1.0.0"}\n')
            os.makedirs("node_modules", exist_ok=True)

            agent = TantivyAgent()
            agent.project_root = nodejs_dir
            project_type = agent._detect_project_type()
            assert project_type == "nodejs"

            # Test generic project
            generic_dir = os.path.join(temp_dir, "generic-project")
            os.makedirs(generic_dir)
            os.chdir(generic_dir)
            with open("README.md", "w") as f:
                f.write("# Generic Project\n")

            agent = TantivyAgent()
            agent.project_root = generic_dir
            project_type = agent._detect_project_type()
            assert project_type == "generic"

        finally:
            os.chdir(original_cwd)


def test_glob_patterns():
    """Test glob pattern expansion"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            # Create test directory structure
            os.makedirs("docs/subdir", exist_ok=True)
            os.makedirs("src/components", exist_ok=True)
            os.makedirs("target", exist_ok=True)

            with open("docs/guide.md", "w") as f:
                f.write("# Guide\n")
            with open("docs/subdir/api.md", "w") as f:
                f.write("# API\n")
            with open("src/component.md", "w") as f:
                f.write("# Component\n")
            with open("target/build.md", "w") as f:
                f.write("# Build\n")

            agent = TantivyAgent()

            # Test simple glob pattern
            patterns = ["*.md"]
            expanded = agent._expand_glob_patterns(patterns)
            file_names = [item["path"] for item in expanded]
            assert "docs/guide.md" not in file_names  # Not in root
            assert len([f for f in file_names if f.endswith(".md")]) >= 0

            # Test recursive glob pattern
            patterns = ["docs/**"]
            expanded = agent._expand_glob_patterns(patterns)
            expanded_paths = [item["path"] for item in expanded]
            assert any("docs/guide.md" in path for path in expanded_paths)
            assert any("docs/subdir/api.md" in path for path in expanded_paths)

            # Test exclude pattern
            patterns = [
                {"path": "docs/**", "exclude": False},
                {"path": "target", "exclude": True},
            ]
            expanded = agent._expand_glob_patterns(patterns)
            expanded_paths = [
                item for item in expanded if not item.get("exclude", False)
            ]
            excluded_paths = [item for item in expanded if item.get("exclude", False)]

            # Should have docs, exclude target
            assert any("docs" in item["path"] for item in expanded_paths)
            assert any("target" in item["path"] for item in excluded_paths)

        finally:
            os.chdir(original_cwd)


def test_default_configs():
    """Test default configurations for different project types"""
    agent = TantivyAgent()

    # Test Python project config
    python_config = agent._get_default_config_for_project_type("python")
    assert "index_dirs" in python_config
    assert any("docs/**" in str(item) for item in python_config["index_dirs"])
    assert any(
        ".venv" in str(item) and item.get("exclude", False)
        for item in python_config["index_dirs"]
    )

    # Test Node.js project config
    nodejs_config = agent._get_default_config_for_project_type("nodejs")
    assert "index_dirs" in nodejs_config
    assert any(
        "node_modules" in str(item) and item.get("exclude", False)
        for item in nodejs_config["index_dirs"]
    )

    # Test Generic project config
    generic_config = agent._get_default_config_for_project_type("generic")
    assert "index_dirs" in generic_config
    assert any(
        "**/.*" in str(item) and item.get("exclude", False)
        for item in generic_config["index_dirs"]
    )


def test_install_functionality():
    """Test install functionality"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            # Create target project directory
            target_project = os.path.join(temp_dir, "test-project")
            os.makedirs(target_project)

            # Create some project files for detection
            with open(os.path.join(target_project, "requirements.txt"), "w") as f:
                f.write("flask==2.0\n")

            agent = TantivyAgent()

            # Test default config creation
            agent._create_default_config(target_project)
            config_path = os.path.join(target_project, ".tantivy2agents.json")
            assert os.path.exists(config_path)

            with open(config_path, "r") as f:
                config = json.load(f)
                assert "index_dirs" in config
                assert "version" in config
                assert config["version"] == "1.0"

            # Test gitignore setup
            agent._setup_gitignore(target_project)
            gitignore_path = os.path.join(target_project, ".gitignore")
            assert os.path.exists(gitignore_path)

            with open(gitignore_path, "r") as f:
                content = f.read()
                assert ".tantivy-data/" in content

        finally:
            os.chdir(original_cwd)


def test_status_command():
    """Test status command with valid index and index_info"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test config
        config = {
            "version": "1.0",
            "index_dir": ".tantivy-data",
            "global_patterns": {"include": ["*.md", "*.txt"], "exclude": ["*.tmp"]},
            "index_dirs": ["docs/"],
            "schema_fields": {
                "title": {"weight": 2.0, "tokenizer": "en_stem"},
                "description": {"weight": 1.5, "tokenizer": "en_stem"},
                "body": {"weight": 1.0, "tokenizer": "en_stem"},
                "tags": {"weight": 1.5, "tokenizer": "default"},
                "servers": {"weight": 1.5, "tokenizer": "default"},
                "path": {"weight": 0.5, "tokenizer": "raw"},
            },
            "search": {"default_limit": 10, "show_description": True, "filters": []},
            "auto_hook": False,  # Disable hooks for testing
        }

        config_path = os.path.join(temp_dir, ".tantivy2agents.json")
        with open(config_path, "w") as f:
            json.dump(config, f)

        # Create test documents
        docs_dir = os.path.join(temp_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)

        with open(os.path.join(docs_dir, "test1.md"), "w") as f:
            f.write("# Test Document One\n\nContent about server configuration.")

        with open(os.path.join(docs_dir, "test2.md"), "w") as f:
            f.write("# Test Document Two\n\nMore test content.")

        # Test index command first
        result = run_cli_command(["index"], cwd=temp_dir)
        if result.returncode != 0:
            raise Exception(f"Index command failed: {result.stderr}")

        # Now test status command
        result = run_cli_command(["status"], cwd=temp_dir)

        if result.returncode != 0:
            raise Exception(
                f"Status command failed with return code {result.returncode}: {result.stderr}"
            )

        # Check that status output contains expected information
        output = result.stdout

        # Should contain project info
        assert "Tantivy Agent Status" in output, "Missing status header"

        # Should contain index directory info
        assert "Index:" in output, "Missing index info"

        # Should contain statistics section
        assert "Index Statistics" in output, "Missing statistics section"

        # Should report document count from index_info.json
        assert "Documents:" in output, "Missing document count"

        # Should show file information section
        assert "File Information" in output, "Missing file information section"

        # Should show system section
        assert "System" in output, "Missing system section"


def test_hook_clear_command():
    """Test hook-clear command"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create minimal config
        config = {
            "version": "1.0",
            "index_dir": ".tantivy-data",
            "global_patterns": {"include": ["*.md"], "exclude": []},
            "index_dirs": ["docs/"],
            "schema_fields": {
                "title": {"weight": 2.0, "tokenizer": "en_stem"},
                "body": {"weight": 1.0, "tokenizer": "en_stem"},
                "path": {"weight": 0.5, "tokenizer": "raw"},
            },
            "search": {"default_limit": 10},
            "auto_hook": False,
        }

        config_path = os.path.join(temp_dir, ".tantivy2agents.json")
        with open(config_path, "w") as f:
            json.dump(config, f)

        # Create test document and index
        docs_dir = os.path.join(temp_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        with open(os.path.join(docs_dir, "test.md"), "w") as f:
            f.write("# Test\nContent")

        # Create index first
        result = run_cli_command(["index"], cwd=temp_dir)
        assert result.returncode == 0, f"Index failed: {result.stderr}"

        # Test hook-clear command (marks index as outdated)
        result = run_cli_command(["hook-clear"], cwd=temp_dir)

        # hook-clear should succeed
        assert result.returncode == 0, f"hook-clear failed: {result.stderr}"

        # Verify index was marked as outdated
        index_info_path = os.path.join(temp_dir, ".tantivy-data", "index_info.json")
        assert os.path.exists(index_info_path), "index_info.json should exist"
        with open(index_info_path) as f:
            index_info = json.load(f)
        assert index_info.get("outdated") is True, "Index should be marked as outdated"


def test_setup_command():
    """Test setup command"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create minimal config
        config = {
            "version": "1.0",
            "index_dir": ".tantivy-data",
            "global_patterns": {"include": ["*.md"], "exclude": []},
            "index_dirs": ["."],
            "schema_fields": {
                "title": {"weight": 2.0, "tokenizer": "en_stem"},
                "body": {"weight": 1.0, "tokenizer": "en_stem"},
                "path": {"weight": 0.5, "tokenizer": "raw"},
            },
            "search": {"default_limit": 10},
            "auto_hook": False,
        }

        config_path = os.path.join(temp_dir, ".tantivy2agents.json")
        with open(config_path, "w") as f:
            json.dump(config, f)

        # Test skill-setup command (renamed from setup)
        result = run_cli_command(["skill-setup"], cwd=temp_dir)

        # skill-setup should succeed (shows help about uvx/uv)
        assert result.returncode == 0, f"skill-setup failed: {result.stderr}"

        # Should contain info about uv/uvx
        assert (
            "uv" in result.stdout.lower() or "uvx" in result.stdout.lower()
        ), f"Expected uv/uvx instructions, got: {result.stdout}"


def test_cli_validation():
    """Test CLI input validation"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create minimal config
        config = {
            "version": "1.0",
            "index_dir": ".tantivy-data",
            "global_patterns": {"include": ["*.md"], "exclude": []},
            "index_dirs": ["."],
            "schema_fields": {
                "title": {"weight": 2.0, "tokenizer": "en_stem"},
                "body": {"weight": 1.0, "tokenizer": "en_stem"},
                "path": {"weight": 0.5, "tokenizer": "raw"},
            },
            "search": {"default_limit": 10},
            "auto_hook": False,
        }

        config_path = os.path.join(temp_dir, ".tantivy2agents.json")
        with open(config_path, "w") as f:
            json.dump(config, f)

        # Test empty search query - Typer now validates this as "Missing argument"
        result = run_cli_command(["search"], cwd=temp_dir)
        assert result.returncode != 0, "Empty search should fail"
        assert (
            "missing" in result.stderr.lower() or "required" in result.stderr.lower()
        ), f"Expected 'missing/required' error, got: {result.stderr}"

        # Test invalid limit (negative)
        result = run_cli_command(["search", "test", "--limit", "-1"], cwd=temp_dir)
        assert result.returncode != 0, "Negative limit should fail"

        # Test invalid limit (too large)
        result = run_cli_command(["search", "test", "--limit", "99999"], cwd=temp_dir)
        assert result.returncode != 0, "Too large limit should fail"


def test_search_filters():
    """Test search filter functionality"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create config with filters
        config = {
            "version": "1.0",
            "index_dir": ".tantivy-data",
            "global_patterns": {"include": ["*.md"], "exclude": []},
            "index_dirs": ["docs/", "incidents/"],
            "schema_fields": {
                "title": {"weight": 2.0, "tokenizer": "en_stem"},
                "description": {"weight": 1.5, "tokenizer": "en_stem"},
                "body": {"weight": 1.0, "tokenizer": "en_stem"},
                "tags": {"weight": 1.5, "tokenizer": "default"},
                "servers": {"weight": 1.5, "tokenizer": "default"},
                "path": {"weight": 0.5, "tokenizer": "raw"},
            },
            "search": {
                "default_limit": 10,
                "show_description": True,
                "filters": [
                    {
                        "name": "incidents",
                        "paths": ["incidents/"],
                        "hidden": True,
                        "show_on_keywords": ["incident", "emergency"],
                    }
                ],
            },
            "auto_hook": False,
        }

        config_path = os.path.join(temp_dir, ".tantivy2agents.json")
        with open(config_path, "w") as f:
            json.dump(config, f)

        # Initialize git repo (required for TantivyAgent)
        subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)

        # Create test documents
        docs_dir = os.path.join(temp_dir, "docs")
        incidents_dir = os.path.join(temp_dir, "incidents")
        os.makedirs(docs_dir, exist_ok=True)
        os.makedirs(incidents_dir, exist_ok=True)

        with open(os.path.join(docs_dir, "guide.md"), "w") as f:
            f.write("# Guide\n\nThis is a test guide.")

        with open(os.path.join(incidents_dir, "outage.md"), "w") as f:
            f.write("# Server Outage\n\nIncident report for server outage.")

        # Test _get_search_filters
        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            agent = TantivyAgent()
            filters = agent._get_search_filters()
            assert len(filters) == 1, "Should have one filter"
            assert filters[0]["name"] == "incidents", "Filter name should be incidents"
            assert filters[0]["paths"] == ["incidents/"], "Filter paths should match"

            # Test _should_include_result - file in filtered path, no keyword
            query_words = {"server", "configuration"}
            result = agent._should_include_result(
                "incidents/outage.md", query_words, filters
            )
            assert result is False, "Should hide incident without keyword"

            # Test _should_include_result - file in filtered path, with keyword
            query_words = {"incident", "server"}
            result = agent._should_include_result(
                "incidents/outage.md", query_words, filters
            )
            assert result is True, "Should show incident with keyword"

            # Test _should_include_result - file not in filtered path
            query_words = {"server"}
            result = agent._should_include_result("docs/guide.md", query_words, filters)
            assert result is True, "Should show non-filtered file"
        finally:
            os.chdir(old_cwd)


def test_search_filters_validation():
    """Test search filter configuration validation"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)

        config_path = os.path.join(temp_dir, ".tantivy2agents.json")
        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            # Test invalid filters type (not a list)
            config = {
                "version": "1.0",
                "index_dir": ".tantivy-data",
                "search": {"filters": "not a list"},
            }
            with open(config_path, "w") as f:
                json.dump(config, f)

            try:
                TantivyAgent()
                assert False, "Should raise ValidationError for non-list filters"
            except ValidationError as e:
                assert "must be a list" in str(e)

            # Test missing paths field
            config = {
                "version": "1.0",
                "index_dir": ".tantivy-data",
                "search": {"filters": [{"name": "test"}]},
            }
            with open(config_path, "w") as f:
                json.dump(config, f)

            try:
                TantivyAgent()
                assert False, "Should raise ValidationError for missing paths"
            except ValidationError as e:
                assert "missing required 'paths'" in str(e)

            # Test paths not a list
            config = {
                "version": "1.0",
                "index_dir": ".tantivy-data",
                "search": {"filters": [{"paths": "not a list"}]},
            }
            with open(config_path, "w") as f:
                json.dump(config, f)

            try:
                TantivyAgent()
                assert False, "Should raise ValidationError for non-list paths"
            except ValidationError as e:
                assert "paths must be a non-empty list" in str(e)

            # Test empty paths list
            config = {
                "version": "1.0",
                "index_dir": ".tantivy-data",
                "search": {"filters": [{"paths": []}]},
            }
            with open(config_path, "w") as f:
                json.dump(config, f)

            try:
                TantivyAgent()
                assert False, "Should raise ValidationError for empty paths"
            except ValidationError as e:
                assert "paths must be a non-empty list" in str(e)
        finally:
            os.chdir(old_cwd)


def test_output_formats():
    """Test CLI output format arguments (-j, -T, -c)"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test config
        config = {
            "version": "1.0",
            "index_dir": ".tantivy-data",
            "global_patterns": {"include": ["*.md"], "exclude": []},
            "index_dirs": ["docs/"],
            "schema_fields": {
                "title": {"weight": 2.0, "tokenizer": "en_stem"},
                "description": {"weight": 1.5, "tokenizer": "en_stem"},
                "body": {"weight": 1.0, "tokenizer": "en_stem"},
                "tags": {"weight": 1.5, "tokenizer": "default"},
                "servers": {"weight": 1.5, "tokenizer": "default"},
                "path": {"weight": 0.5, "tokenizer": "raw"},
            },
            "search": {"default_limit": 10, "show_description": True, "filters": []},
            "auto_hook": False,
        }

        config_path = os.path.join(temp_dir, ".tantivy2agents.json")
        with open(config_path, "w") as f:
            json.dump(config, f)

        # Create test document
        docs_dir = os.path.join(temp_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        with open(os.path.join(docs_dir, "guide.md"), "w") as f:
            f.write("# Complete Guide to Testing\n\nThis is test content.")

        # Build index
        result = run_cli_command(["index"], cwd=temp_dir)
        assert result.returncode == 0, f"Index failed: {result.stderr}"

        # Test default output (structured text)
        result = run_cli_command(["search", "test"], cwd=temp_dir)
        assert result.returncode == 0, f"Search failed: {result.stderr}"
        assert "### FILE:" in result.stdout, "Default output should be structured text"
        assert "SCORE:" in result.stdout, "Should have SCORE"
        assert "---" in result.stdout, "Should have separator"

        # Test --format json
        result = run_cli_command(["search", "test", "--format", "json"], cwd=temp_dir)
        assert result.returncode == 0, f"Search --format json failed: {result.stderr}"
        assert '"query":' in result.stdout, "JSON output should have query"
        assert '"results":' in result.stdout, "JSON should have results array"

        # Test --format text (explicit structured text)
        result = run_cli_command(["search", "test", "--format", "text"], cwd=temp_dir)
        assert result.returncode == 0, f"Search --format text failed: {result.stderr}"
        assert "### FILE:" in result.stdout, "Text output should have FILE marker"

        # Test --format csv
        result = run_cli_command(["search", "test", "--format", "csv"], cwd=temp_dir)
        assert result.returncode == 0, f"Search --format csv failed: {result.stderr}"
        assert "Score,Path,Title" in result.stdout, "CSV output should have headers"


def test_json_empty_title():
    """Test that JSON output doesn't use filename as fallback title"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test config
        config = {
            "version": "1.0",
            "index_dir": ".tantivy-data",
            "global_patterns": {"include": ["*.md"], "exclude": []},
            "index_dirs": ["docs/"],
            "schema_fields": {
                "title": {"weight": 2.0, "tokenizer": "en_stem"},
                "description": {"weight": 1.5, "tokenizer": "en_stem"},
                "body": {"weight": 1.0, "tokenizer": "en_stem"},
                "tags": {"weight": 1.5, "tokenizer": "default"},
                "servers": {"weight": 1.5, "tokenizer": "default"},
                "path": {"weight": 0.5, "tokenizer": "raw"},
            },
            "search": {"default_limit": 10, "show_description": True, "filters": []},
            "auto_hook": False,
        }

        config_path = os.path.join(temp_dir, ".tantivy2agents.json")
        with open(config_path, "w") as f:
            json.dump(config, f)

        # Create test document WITHOUT a title heading
        docs_dir = os.path.join(temp_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        with open(os.path.join(docs_dir, "notitle.md"), "w") as f:
            f.write("This document has no title heading, just content.")

        # Build index
        result = run_cli_command(["index"], cwd=temp_dir)
        assert result.returncode == 0, f"Index failed: {result.stderr}"

        # Search with JSON output and verify title is empty, not "No title"
        result = run_cli_command(
            ["search", "content", "--format", "json"], cwd=temp_dir
        )
        assert result.returncode == 0, f"Search failed: {result.stderr}"
        assert '"No title"' not in result.stdout, "Should not have 'No title' fallback"
        # Parse JSON to verify empty title
        output_data = json.loads(result.stdout)
        if output_data["results"]:
            # Title should be empty or contain actual content (not "No title")
            title = output_data["results"][0]["title"]
            assert title != "No title", f"Title should not be 'No title', got: {title}"


def test_description_output():
    """Test description field in search results"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test config with show_description=True
        config = {
            "version": "1.0",
            "index_dir": ".tantivy-data",
            "global_patterns": {"include": ["*.md"], "exclude": []},
            "index_dirs": ["docs/"],
            "schema_fields": {
                "title": {"weight": 2.0, "tokenizer": "en_stem"},
                "description": {"weight": 1.5, "tokenizer": "en_stem"},
                "body": {"weight": 1.0, "tokenizer": "en_stem"},
                "tags": {"weight": 1.5, "tokenizer": "default"},
                "servers": {"weight": 1.5, "tokenizer": "default"},
                "path": {"weight": 0.5, "tokenizer": "raw"},
            },
            "search": {"default_limit": 10, "show_description": True, "filters": []},
            "auto_hook": False,
        }

        config_path = os.path.join(temp_dir, ".tantivy2agents.json")
        with open(config_path, "w") as f:
            json.dump(config, f)

        # Create test document with description
        docs_dir = os.path.join(temp_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        with open(os.path.join(docs_dir, "guide.md"), "w") as f:
            f.write("""---
title: Complete Guide
description: A comprehensive guide for testing functionality
tags: [guide, test]
---

# Complete Guide

This is test content about testing.
""")

        # Build index
        result = run_cli_command(["index"], cwd=temp_dir)
        assert result.returncode == 0, f"Index failed: {result.stderr}"

        # Test text output contains DESCRIPTION
        result = run_cli_command(["search", "test", "--format", "text"], cwd=temp_dir)
        assert result.returncode == 0, f"Search failed: {result.stderr}"
        assert "DESCRIPTION:" in result.stdout, "Text output should have DESCRIPTION"
        assert "comprehensive guide" in result.stdout, "Should contain description text"

        # Test JSON output contains description
        result = run_cli_command(["search", "test", "--format", "json"], cwd=temp_dir)
        assert result.returncode == 0, f"Search --format json failed: {result.stderr}"
        output_data = json.loads(result.stdout)
        assert (
            "description" in output_data["results"][0]
        ), "JSON should have description field"
        assert (
            "comprehensive guide" in output_data["results"][0]["description"]
        ), "JSON should contain description"

        # Test CSV output contains Description header
        result = run_cli_command(["search", "test", "--format", "csv"], cwd=temp_dir)
        assert result.returncode == 0, f"Search --format csv failed: {result.stderr}"
        assert "Description" in result.stdout, "CSV header should have Description"


def test_description_hidden():
    """Test description field hidden when show_description=False"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test config with show_description=False
        config = {
            "version": "1.0",
            "index_dir": ".tantivy-data",
            "global_patterns": {"include": ["*.md"], "exclude": []},
            "index_dirs": ["docs/"],
            "schema_fields": {
                "title": {"weight": 2.0, "tokenizer": "en_stem"},
                "description": {"weight": 1.5, "tokenizer": "en_stem"},
                "body": {"weight": 1.0, "tokenizer": "en_stem"},
                "tags": {"weight": 1.5, "tokenizer": "default"},
                "servers": {"weight": 1.5, "tokenizer": "default"},
                "path": {"weight": 0.5, "tokenizer": "raw"},
            },
            "search": {"default_limit": 10, "show_description": False, "filters": []},
            "auto_hook": False,
        }

        config_path = os.path.join(temp_dir, ".tantivy2agents.json")
        with open(config_path, "w") as f:
            json.dump(config, f)

        # Create test document with description
        docs_dir = os.path.join(temp_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        with open(os.path.join(docs_dir, "guide.md"), "w") as f:
            f.write("""---
title: Complete Guide
description: A comprehensive guide for testing functionality
tags: [guide, test]
---

# Complete Guide

This is test content about testing.
""")

        # Build index
        result = run_cli_command(["index"], cwd=temp_dir)
        assert result.returncode == 0, f"Index failed: {result.stderr}"

        # Test text output does NOT contain DESCRIPTION
        result = run_cli_command(["search", "test", "--format", "text"], cwd=temp_dir)
        assert result.returncode == 0, f"Search failed: {result.stderr}"
        assert (
            "DESCRIPTION:" not in result.stdout
        ), "Text output should NOT have DESCRIPTION when hidden"

        # Test JSON output does NOT contain description field
        result = run_cli_command(["search", "test", "--format", "json"], cwd=temp_dir)
        assert result.returncode == 0, f"Search --format json failed: {result.stderr}"
        output_data = json.loads(result.stdout)
        assert (
            "description" not in output_data["results"][0]
        ), "JSON should NOT have description when hidden"

        # Test CSV output does NOT contain Description header
        result = run_cli_command(["search", "test", "--format", "csv"], cwd=temp_dir)
        assert result.returncode == 0, f"Search --format csv failed: {result.stderr}"
        assert (
            ",Description," not in result.stdout
        ), "CSV header should NOT have Description when hidden"


def test_search_filters_empty():
    """Test that empty filters list allows all results"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = {
            "version": "1.0",
            "index_dir": ".tantivy-data",
            "search": {"default_limit": 10, "filters": []},
            "auto_hook": False,
        }

        config_path = os.path.join(temp_dir, ".tantivy2agents.json")
        with open(config_path, "w") as f:
            json.dump(config, f)

        subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            agent = TantivyAgent()
            filters = agent._get_search_filters()
            assert filters == [], "Should return empty list"

            # With no filters, _should_include_result should always return True
            result = agent._should_include_result("any/path.md", {"query"}, filters)
            assert result is True, "Should include all results with no filters"
        finally:
            os.chdir(old_cwd)


def test_extract_document_fields_backward_compat():
    """Test backward compatibility - missing description field in old index"""
    with tempfile.TemporaryDirectory() as temp_dir:
        subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)

        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            agent = TantivyAgent()

            # Mock a Tantivy document from old index without description field
            # Note: Tantivy doc[key] returns [] for missing fields, not KeyError
            class MockDoc:
                def __getitem__(self, key):
                    data = {
                        "path": ["test.md"],
                        "title": ["Test Title"],
                        "tags": ["tag1"],
                        "servers": ["server1"],
                        # description missing - simulates old index
                    }
                    return data.get(key, [])  # Tantivy returns [] for missing

            doc = MockDoc()

            # Test with description requested - should return empty string, not error
            fields = agent._extract_document_fields(doc, include_description=True)
            assert (
                fields["description"] == ""
            ), "Missing description should be empty string"
            assert fields["path"] == "test.md"
            assert fields["title"] == "Test Title"
            assert fields["tags"] == "tag1"
            assert fields["servers"] == "server1"

            # Test without description - should not include description key
            fields_no_desc = agent._extract_document_fields(
                doc, include_description=False
            )
            assert (
                "description" not in fields_no_desc
            ), "Should not include description when disabled"
            assert fields_no_desc["path"] == "test.md"
        finally:
            os.chdir(old_cwd)


def test_excluded_directories():
    """Test that excluded directories (.git, .venv, etc.) are not indexed"""
    with tempfile.TemporaryDirectory() as temp_dir:
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            # Create .git directory with a file
            os.makedirs(".git/objects")
            with open(".git/config", "w") as f:
                f.write("[core]\n    repositoryformatversion = 0\n")
            with open(".git/objects/testfile", "w") as f:
                f.write("some git object content")

            # Create .venv directory with Python files
            os.makedirs(".venv/lib/python3.13/site-packages")
            with open(".venv/lib/python3.13/site-packages/test.py", "w") as f:
                f.write("# Python package file\nprint('hello')")

            # Create node_modules directory
            os.makedirs("node_modules/some-package")
            with open("node_modules/some-package/index.js", "w") as f:
                f.write("// JavaScript file\nconsole.log('test');")

            # Create legitimate files that should be indexed
            with open("README.md", "w") as f:
                f.write("# README\nThis should be indexed")
            with open("script.py", "w") as f:
                f.write("# Script\nprint('this should be indexed')")

            # Create config with default excluded directories
            config = {
                "version": "1.0",
                "index_dir": ".tantivy-data",
                "global_patterns": {"include": ["*.*"], "exclude": []},
                "index_dirs": [
                    ".",
                    {"path": ".git", "exclude": True},
                    {"path": ".venv", "exclude": True},
                    {"path": "node_modules", "exclude": True},
                ],
                "auto_hook": False,
            }

            config_path = os.path.join(temp_dir, ".tantivy2agents.json")
            with open(config_path, "w") as f:
                json.dump(config, f)

            # Create agent and get files for indexing
            agent = TantivyAgent(config_path=config_path)
            files, _ = agent._get_files_for_indexing()

            # Convert to relative paths for easier checking
            rel_files = [os.path.relpath(f, temp_dir) for f in files]

            # Check that legitimate files are included
            assert "README.md" in rel_files, "README.md should be indexed"
            assert "script.py" in rel_files, "script.py should be indexed"

            # Check that excluded directory files are NOT included
            git_files = [f for f in rel_files if f.startswith(".git/")]
            venv_files = [f for f in rel_files if f.startswith(".venv/")]
            node_files = [f for f in rel_files if f.startswith("node_modules/")]

            assert len(git_files) == 0, f"Found files in .git/: {git_files}"
            assert len(venv_files) == 0, f"Found files in .venv/: {venv_files}"
            assert len(node_files) == 0, f"Found files in node_modules/: {node_files}"

        finally:
            os.chdir(old_cwd)


def main():
    """Run all tests"""
    print("Running Tantivy Agent Tests...")
    print()

    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Config Loading", test_config_loading),
        ("File Parsing", test_file_parsing),
        ("Pattern Matching", test_patterns),
        ("Export Functionality", test_export_functionality),
        ("Project Detection", test_project_detection),
        ("Glob Patterns", test_glob_patterns),
        ("Default Configs", test_default_configs),
        ("Install Functionality", test_install_functionality),
        ("Status Command", test_status_command),
        ("Hook Clear Command", test_hook_clear_command),
        ("Setup Command", test_setup_command),
        ("CLI Validation", test_cli_validation),
        ("Search Filters", test_search_filters),
        ("Search Filters Validation", test_search_filters_validation),
        ("Search Filters Empty", test_search_filters_empty),
        (
            "Extract Document Fields Backward Compat",
            test_extract_document_fields_backward_compat,
        ),
        ("Output Formats", test_output_formats),
        ("JSON Empty Title", test_json_empty_title),
        ("Description Output", test_description_output),
        ("Description Hidden", test_description_hidden),
        ("Excluded Directories", test_excluded_directories),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        if run_test(test_name, test_func):
            passed += 1

    print()
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
