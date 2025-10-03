#!/usr/bin/env python3
"""
Simple test runner for Tantivy Agent
"""

import os
import sys
import subprocess

def main():
    """Run all tests"""
    print("🧪 Tantivy Agent Test Runner")
    print("=" * 30)

    # Run basic tests
    result = subprocess.run([sys.executable, "tests/test_basic.py"],
                          capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)

    return result.returncode

if __name__ == "__main__":
    sys.exit(main())