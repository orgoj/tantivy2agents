#!/usr/bin/env python3
"""
Basic tests for Tantivy Agent functionality
"""

import os
import sys
import json
import tempfile
import shutil
import subprocess
from pathlib import Path

def run_test(test_name, test_func):
    """Run a test function and report results"""
    try:
        test_func()
        print(f"✅ {test_name}")
        return True
    except Exception as e:
        print(f"❌ {test_name}: {e}")
        return False

def test_basic_functionality():
    """Test basic agent functionality"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Copy agent script
            agent_path = os.path.join(original_cwd, "tantivy-agent.py")
            shutil.copy(agent_path, "./tantivy-agent.py")
            os.chmod("./tantivy-agent.py", 0o755)

            # Create test config
            config = {
                "version": "1.0",
                "index_dir": ".tantivy-data",
                "global_patterns": {
                    "include": ["*.md", "*.txt"],
                    "exclude": ["*.tmp"]
                },
                "index_dirs": ["docs/"],
                "schema_fields": {
                    "title": {"weight": 2.0, "tokenizer": "en_stem"},
                    "body": {"weight": 1.0, "tokenizer": "en_stem"},
                    "tags": {"weight": 1.5, "tokenizer": "default"},
                    "servers": {"weight": 1.5, "tokenizer": "default"},
                    "path": {"weight": 0.5, "tokenizer": "raw"}
                },
                "search": {"default_limit": 10, "hide_incidents": True},
                "auto_hook": False  # Disable hooks for testing
            }

            with open(".tantivi2agents.json", "w") as f:
                json.dump(config, f)

            # Create test documents
            os.makedirs("docs", exist_ok=True)

            with open("docs/test1.md", "w") as f:
                f.write("""# Test Document One

This is a test document about server configuration.

Tags: [test, server]
""")

            with open("docs/test2.md", "w") as f:
                f.write("""# Guide for Testing

Complete guide for testing functionality.
""")

            # Test help command
            result = subprocess.run(["python", "./tantivy-agent.py", "--help"],
                                  capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception("Help command failed")

            # Test install command
            result = subprocess.run(["python", "./tantivy-agent.py", "install"],
                                  capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception("Install command failed")

            # Test index command
            result = subprocess.run(["python", "./tantivy-agent.py", "index"],
                                  capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception("Index command failed")

            if "Successfully indexed" not in result.stdout:
                raise Exception("Indexing did not succeed")

            # Test search command
            result = subprocess.run(["python", "./tantivy-agent.py", "search", "server"],
                                  capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception("Search command failed")

            if "Found" not in result.stdout:
                raise Exception("Search did not find results")

            # Test clear command
            result = subprocess.run(["python", "./tantivy-agent.py", "clear"],
                                  capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception("Clear command failed")

            # Check that data directory structure exists (even if cleared)
            if not os.path.exists(".gitignore"):
                raise Exception("Gitignore was not updated")

        finally:
            os.chdir(original_cwd)

def test_config_loading():
    """Test configuration loading with defaults"""
    # Import the main class from the script
    original_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tantivy-agent.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("tantivy_agent", original_script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    TantivyAgent = module.TantivyAgent

    # Test with non-existent config (should use defaults)
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        try:
            agent = TantivyAgent()

            # Check default values
            assert agent.config["version"] == "1.0"
            assert agent.config["index_dir"] == ".tantivy-data"
            assert "docs/" in agent.config["index_dirs"]
            assert "title" in agent.config["schema_fields"]

        finally:
            os.chdir(os.path.dirname(temp_dir))

def test_file_parsing():
    """Test markdown file parsing"""
    # Get the original script path
    original_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tantivy-agent.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("tantivy_agent", original_script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    TantivyAgent = module.TantivyAgent

    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        try:
            agent = TantivyAgent()

            # Create test markdown file
            with open("test.md", "w") as f:
                f.write("""---
title: Custom Title
tags: [test, markdown]
servers: [web, api]

---

# Custom Title

This is the body content.
""")

            doc = agent._parse_markdown("test.md")

            assert doc is not None
            assert doc["title"] == "Custom Title"
            assert "test markdown" in doc["tags"]
            assert "web api" in doc["servers"]
            assert "body content" in doc["body"]

        finally:
            os.chdir(os.path.dirname(temp_dir))

def test_patterns():
    """Test file pattern matching"""
    # Get the original script path
    original_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tantivy-agent.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("tantivy_agent", original_script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    TantivyAgent = module.TantivyAgent

    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        try:
            agent = TantivyAgent()

            # Test pattern matching
            assert agent._match_pattern("test.md", "*.md") == True
            assert agent._match_pattern("test.txt", "*.md") == False
            assert agent._match_pattern("docs/test.md", "docs/*.md") == True
            assert agent._match_pattern("test.tmp", "*.md") == False
            assert agent._match_pattern("test.md", "*.md") == True

        finally:
            os.chdir(os.path.dirname(temp_dir))

def test_export_functionality():
    """Test result export functionality"""
    original_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tantivy-agent.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("tantivy_agent", original_script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    TantivyAgent = module.TantivyAgent

    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        try:
            agent = TantivyAgent()

            # Create mock results
            import sys
            from types import SimpleNamespace

            # Create mock document object
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
            with open(csv_file, 'r') as f:
                content = f.read()
                assert "Score,Path,Title" in content
                assert "0.8500" in content

            # Test text export to file
            txt_file = "test_export.txt"
            agent._export_txt(results, "test query", txt_file)

            assert os.path.exists(txt_file)
            with open(txt_file, 'r') as f:
                content = f.read()
                assert "Search Results for: 'test query'" in content
                assert "Total Results: 2" in content
                assert "1. mock_value_title" in content

        finally:
            os.chdir(os.path.dirname(temp_dir))

def main():
    """Run all tests"""
    print("🧪 Running Tantivy Agent Tests...")
    print()

    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Config Loading", test_config_loading),
        ("File Parsing", test_file_parsing),
        ("Pattern Matching", test_patterns),
        ("Export Functionality", test_export_functionality)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        if run_test(test_name, test_func):
            passed += 1

    print()
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())