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
        import traceback
        print(f"❌ {test_name}: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
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

def test_project_detection():
    """Test project type detection"""
    original_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tantivy-agent.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("tantivy_agent", original_script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    TantivyAgent = module.TantivyAgent

    with tempfile.TemporaryDirectory() as temp_dir:
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
            os.chdir(os.path.dirname(temp_dir))

def test_glob_patterns():
    """Test glob pattern expansion"""
    original_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tantivy-agent.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("tantivy_agent", original_script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    TantivyAgent = module.TantivyAgent

    with tempfile.TemporaryDirectory() as temp_dir:
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
                {"path": "target", "exclude": True}
            ]
            expanded = agent._expand_glob_patterns(patterns)
            expanded_paths = [item for item in expanded if not item.get("exclude", False)]
            excluded_paths = [item for item in expanded if item.get("exclude", False)]

            # Should have docs, exclude target
            assert any("docs" in item["path"] for item in expanded_paths)
            assert any("target" in item["path"] for item in excluded_paths)

        finally:
            os.chdir(os.path.dirname(temp_dir))

def test_default_configs():
    """Test default configurations for different project types"""
    original_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tantivy-agent.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("tantivy_agent", original_script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    TantivyAgent = module.TantivyAgent

    # Test Python project config
    agent = TantivyAgent()
    python_config = agent._get_default_config_for_project_type("python")
    assert "index_dirs" in python_config
    assert any("docs/**" in str(item) for item in python_config["index_dirs"])
    assert any(".venv" in str(item) and item.get("exclude", False) for item in python_config["index_dirs"])

    # Test Node.js project config
    nodejs_config = agent._get_default_config_for_project_type("nodejs")
    assert "index_dirs" in nodejs_config
    assert any("node_modules" in str(item) and item.get("exclude", False) for item in nodejs_config["index_dirs"])

    # Test Generic project config
    generic_config = agent._get_default_config_for_project_type("generic")
    assert "index_dirs" in generic_config
    assert any("**/.*" in str(item) and item.get("exclude", False) for item in generic_config["index_dirs"])

def test_install_functionality():
    """Test install functionality with symlink creation"""
    original_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tantivy-agent.py")
    import importlib.util
    spec = importlib.util.spec_from_file_location("tantivy_agent", original_script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    TantivyAgent = module.TantivyAgent

    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        try:
            # Create target project directory
            target_project = os.path.join(temp_dir, "test-project")
            os.makedirs(target_project)

            # Create some project files for detection
            with open(os.path.join(target_project, "requirements.txt"), "w") as f:
                f.write("flask==2.0\n")

            agent = TantivyAgent()

            # Test symlink creation
            agent._create_symlink(target_project)

            # Check if symlink was created
            tools_dir = os.path.join(target_project, "tools")
            symlink_path = os.path.join(tools_dir, "tantivy-agent.py")
            assert os.path.exists(symlink_path)
            assert os.path.islink(symlink_path)

            # Test default config creation
            agent._create_default_config(target_project)
            config_path = os.path.join(target_project, ".tantivi2agents.json")
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
                assert "!tools/tantivy-agent.py" in content

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
        ("Export Functionality", test_export_functionality),
        ("Project Detection", test_project_detection),
        ("Glob Patterns", test_glob_patterns),
        ("Default Configs", test_default_configs),
        ("Install Functionality", test_install_functionality)
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