#!/usr/bin/env python3
"""
Comprehensive test runner for Tantivy Agent
"""

import os
import sys
import subprocess


def run_test_suite(test_file, suite_name):
    """Run a single test suite"""
    print(f"🧪 {suite_name}")
    print("=" * len(suite_name))

    result = subprocess.run([sys.executable, test_file], capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)

    print()
    return result.returncode == 0


def main():
    """Run all test suites"""
    print("🧪 Tantivy Agent - Comprehensive Test Suite")
    print("=" * 50)
    print()

    test_suites = [
        ("tests/test_basic.py", "Basic Functionality"),
        ("tests/test_install.py", "Install Functionality"),
        ("tests/test_encoding.py", "Encoding Detection"),
        ("tests/test_concurrency.py", "Parallel Index and Search"),
        ("tests/test_portability.py", "Cross-Platform Paths"),
        ("tests/test_read_gateway.py", "Read Gateway and Usage Log"),
    ]

    all_passed = True

    for test_file, suite_name in test_suites:
        if os.path.exists(test_file):
            passed = run_test_suite(test_file, suite_name)
            if not passed:
                all_passed = False
        else:
            print(f"⚠️  Test file not found: {test_file}")
            print()
            all_passed = False

    # Summary
    if all_passed:
        print("🎉 All test suites passed!")
        return 0
    else:
        print("❌ Some test suites failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
