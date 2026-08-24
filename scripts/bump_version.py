#!/usr/bin/env python3
"""Bump the project version in every place that must stay in sync.

Keeps `pyproject.toml` and `src/tantivy2agents/__init__.py` at the same
version and checks that `CHANGELOG.md` has a section for the new version.

Usage:
    python scripts/bump_version.py patch|minor|major
    python scripts/bump_version.py 1.2.3
    python scripts/bump_version.py --show
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
INIT_FILE = REPO_ROOT / "src" / "tantivy2agents" / "__init__.py"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

PYPROJECT_PATTERN = re.compile(r'(?m)^(version = ")(\d+\.\d+\.\d+)(")$')
INIT_PATTERN = re.compile(r'(?m)^(__version__ = ")(\d+\.\d+\.\d+)(")$')
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def read_version(path: Path, pattern: re.Pattern) -> str:
    match = pattern.search(path.read_text(encoding="utf-8"))
    if not match:
        raise SystemExit(f"No version found in {path}")
    return match.group(2)


def write_version(path: Path, pattern: re.Pattern, new_version: str) -> None:
    text = path.read_text(encoding="utf-8")
    new_text, count = pattern.subn(rf"\g<1>{new_version}\g<3>", text, count=1)
    if count != 1:
        raise SystemExit(f"Failed to update the version in {path}")
    path.write_text(new_text, encoding="utf-8")


def current_version() -> str:
    pyproject_version = read_version(PYPROJECT, PYPROJECT_PATTERN)
    init_version = read_version(INIT_FILE, INIT_PATTERN)
    if pyproject_version != init_version:
        raise SystemExit(
            "Version mismatch: "
            f"pyproject.toml={pyproject_version} __init__.py={init_version}"
        )
    return pyproject_version


def next_version(version: str, part: str) -> str:
    major, minor, patch = (int(piece) for piece in version.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target",
        nargs="?",
        help="patch, minor, major, or an explicit X.Y.Z version",
    )
    parser.add_argument(
        "--show", action="store_true", help="print the current version and exit"
    )
    args = parser.parse_args()

    version = current_version()

    if args.show or not args.target:
        print(version)
        return 0

    if args.target in {"patch", "minor", "major"}:
        new_version = next_version(version, args.target)
    elif VERSION_PATTERN.match(args.target):
        new_version = args.target
    else:
        raise SystemExit(f"Invalid target: {args.target}")

    if new_version == version:
        raise SystemExit(f"Version is already {version}")

    write_version(PYPROJECT, PYPROJECT_PATTERN, new_version)
    write_version(INIT_FILE, INIT_PATTERN, new_version)

    print(f"{version} -> {new_version}")

    changelog = CHANGELOG.read_text(encoding="utf-8")
    if f"## [{new_version}]" not in changelog:
        print(
            f"Warning: CHANGELOG.md has no '## [{new_version}]' section yet",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
