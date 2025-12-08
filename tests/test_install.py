#!/usr/bin/env python3
"""
Comprehensive tests for Tantivy Agent install functionality
"""

import os
import sys
import json
import shutil

# Add src to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from tantivy2agents import TantivyAgent


def test_project_detection():
    """Test project type detection for various project types"""
    test_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp")
    os.makedirs(test_dir, exist_ok=True)

    results = []

    # Test Python project
    python_dir = os.path.join(test_dir, "python-test")
    os.makedirs(python_dir, exist_ok=True)

    with open(os.path.join(python_dir, "requirements.txt"), "w") as f:
        f.write("flask==2.0\n")
    os.makedirs(os.path.join(python_dir, "src"), exist_ok=True)

    agent = TantivyAgent()
    agent.project_root = python_dir
    detected = agent._detect_project_type()
    results.append(("Python project detection", detected == "python"))

    # Test Node.js project
    nodejs_dir = os.path.join(test_dir, "nodejs-test")
    os.makedirs(nodejs_dir, exist_ok=True)

    with open(os.path.join(nodejs_dir, "package.json"), "w") as f:
        f.write('{"name": "test", "version": "1.0.0"}\n')
    os.makedirs(os.path.join(nodejs_dir, "node_modules"), exist_ok=True)

    agent = TantivyAgent()
    agent.project_root = nodejs_dir
    detected = agent._detect_project_type()
    results.append(("Node.js project detection", detected == "nodejs"))

    # Test Java project
    java_dir = os.path.join(test_dir, "java-test")
    os.makedirs(java_dir, exist_ok=True)

    with open(os.path.join(java_dir, "pom.xml"), "w") as f:
        f.write("<project><modelVersion>4.0.0</modelVersion></project>\n")
    os.makedirs(os.path.join(java_dir, "src/main/java"), exist_ok=True)

    agent = TantivyAgent()
    agent.project_root = java_dir
    detected = agent._detect_project_type()
    results.append(("Java project detection", detected == "java"))

    # Test Generic project
    generic_dir = os.path.join(test_dir, "generic-test")
    os.makedirs(generic_dir, exist_ok=True)

    with open(os.path.join(generic_dir, "README.md"), "w") as f:
        f.write("# Generic Project\n")

    agent = TantivyAgent()
    agent.project_root = generic_dir
    detected = agent._detect_project_type()
    results.append(("Generic project detection", detected == "generic"))

    return results


def test_default_configurations():
    """Test default configurations for different project types"""
    results = []

    agent = TantivyAgent()

    # Test Python config
    python_config = agent._get_default_config_for_project_type("python")
    has_index_dirs = "index_dirs" in python_config
    has_docs_recursive = any(
        "docs/**" in str(item) for item in python_config["index_dirs"]
    )
    has_exclude_venv = any(
        isinstance(item, dict) and item.get("path") == ".venv" and item.get("exclude")
        for item in python_config["index_dirs"]
    )
    results.append(
        (
            "Python config structure",
            has_index_dirs and has_docs_recursive and has_exclude_venv,
        )
    )

    # Test Node.js config
    nodejs_config = agent._get_default_config_for_project_type("nodejs")
    has_exclude_node_modules = any(
        isinstance(item, dict) and "node_modules" in str(item) and item.get("exclude")
        for item in nodejs_config["index_dirs"]
    )
    results.append(("Node.js config excludes node_modules", has_exclude_node_modules))

    # Test Generic config
    generic_config = agent._get_default_config_for_project_type("generic")
    has_exclude_hidden = any(
        isinstance(item, dict) and "**/.*" in str(item) and item.get("exclude")
        for item in generic_config["index_dirs"]
    )
    results.append(("Generic config excludes hidden files", has_exclude_hidden))

    return results


def test_glob_patterns():
    """Test glob pattern expansion"""
    test_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp")
    os.makedirs(test_dir, exist_ok=True)
    results = []

    # Create test structure
    test_project_dir = os.path.join(test_dir, "glob-test")
    os.makedirs(os.path.join(test_project_dir, "docs/subdir"), exist_ok=True)
    os.makedirs(os.path.join(test_project_dir, "src/components"), exist_ok=True)
    os.makedirs(os.path.join(test_project_dir, "target"), exist_ok=True)

    with open(os.path.join(test_project_dir, "docs/guide.md"), "w") as f:
        f.write("# Guide\n")
    with open(os.path.join(test_project_dir, "docs/subdir/api.md"), "w") as f:
        f.write("# API\n")
    with open(os.path.join(test_project_dir, "src/component.md"), "w") as f:
        f.write("# Component\n")
    with open(os.path.join(test_project_dir, "target/build.md"), "w") as f:
        f.write("# Build\n")

    agent = TantivyAgent()
    agent.project_root = test_project_dir

    # Test recursive glob
    patterns = ["docs/**"]
    expanded = agent._expand_glob_patterns(patterns)
    expanded_paths = [item["path"] for item in expanded]
    has_docs_guide = any("docs/guide.md" in path for path in expanded_paths)
    has_docs_api = any("docs/subdir/api.md" in path for path in expanded_paths)
    results.append(("Recursive glob expansion", has_docs_guide and has_docs_api))

    # Test exclude pattern
    patterns = [
        {"path": "docs/**", "exclude": False},
        {"path": "target", "exclude": True},
    ]
    expanded = agent._expand_glob_patterns(patterns)
    included = [item for item in expanded if not item.get("exclude", False)]
    excluded = [item for item in expanded if item.get("exclude", False)]
    has_docs = any("docs" in item["path"] for item in included)
    has_target_excluded = any("target" in item["path"] for item in excluded)
    results.append(("Exclude pattern handling", has_docs and has_target_excluded))

    return results


def test_install_workflow():
    """Test complete install workflow"""
    test_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp")
    os.makedirs(test_dir, exist_ok=True)
    results = []

    # Create target project
    target_project = os.path.join(test_dir, "install-test-project")
    if os.path.exists(target_project):
        shutil.rmtree(target_project)
    os.makedirs(target_project)

    # Add Python project indicators
    with open(os.path.join(target_project, "requirements.txt"), "w") as f:
        f.write("flask==2.0\n")
    os.makedirs(os.path.join(target_project, "src"), exist_ok=True)

    agent = TantivyAgent()

    # Test config creation
    agent._create_default_config(target_project)
    config_path = os.path.join(target_project, ".tantivi2agents.json")
    config_exists = os.path.exists(config_path)
    results.append(("Config file creation", config_exists))

    if config_exists:
        with open(config_path, "r") as f:
            config = json.load(f)
            has_version = "version" in config
            has_index_dirs = "index_dirs" in config
            results.append(
                ("Config content validation", has_version and has_index_dirs)
            )

    # Test gitignore setup
    agent._setup_gitignore(target_project)
    gitignore_path = os.path.join(target_project, ".gitignore")
    gitignore_exists = os.path.exists(gitignore_path)
    results.append(("Gitignore creation", gitignore_exists))

    if gitignore_exists:
        with open(gitignore_path, "r") as f:
            content = f.read()
            has_tantivy_data = ".tantivy-data/" in content
            results.append(("Gitignore content", has_tantivy_data))

    # Test Claude hooks installation
    agent._install_claude_hooks(target_root=target_project)
    claude_config_path = os.path.join(target_project, ".claude", "settings.json")
    claude_hooks_exist = os.path.exists(claude_config_path)
    results.append(("Claude hooks installation", claude_hooks_exist))

    if claude_hooks_exist:
        with open(claude_config_path, "r") as f:
            content = f.read()
            has_hooks = "PostToolUse" in content and "tantivy2agents" in content
            results.append(("Claude hooks content", has_hooks))

    return results


def run_all_tests():
    """Run all install-related tests"""
    print("Running Tantivy Agent Install Tests...")
    print()

    all_results = []

    # Run test suites
    test_suites = [
        ("Project Detection", test_project_detection),
        ("Default Configurations", test_default_configurations),
        ("Glob Patterns", test_glob_patterns),
        ("Install Workflow", test_install_workflow),
    ]

    for suite_name, test_func in test_suites:
        print(f"  {suite_name}:")
        try:
            results = test_func()
            suite_passed = True
            for test_name, passed in results:
                status = "  " if passed else "  "
                print(f"  {status} {test_name}")
                if not passed:
                    suite_passed = False
                all_results.append((test_name, passed))

            if suite_passed:
                print(f"  {suite_name} - PASSED")
            else:
                print(f"  {suite_name} - FAILED")
        except Exception as e:
            print(f"  {suite_name} - ERROR: {e}")
            import traceback

            traceback.print_exc()
            all_results.append((f"{suite_name} - Error", False))
        print()

    # Summary
    total = len(all_results)
    passed = sum(1 for _, result in all_results if result)
    failed = total - passed

    print(f"Test Results: {passed}/{total} tests passed")

    if failed == 0:
        print("All install tests passed!")
        return 0
    else:
        print(f"{failed} tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
