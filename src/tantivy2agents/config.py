"""Configuration defaults, loading, and validation."""

from __future__ import annotations

import copy
import json
import os
from typing import Any

from .exceptions import ConfigError, ValidationError

DEFAULT_ENCODING_CONFIDENCE_THRESHOLD = 0.7


def default_config() -> dict[str, Any]:
    """Return the default runtime configuration."""
    return {
        "version": "1.0",
        "index_dir": ".tantivy-data",
        "global_patterns": {
            "include": ["*.*"],
            "exclude": [
                "*.tmp",
                "*~",
                "*.bak",
                "*.log",
                "*.swp",
                "*.swo",
                ".DS_Store",
                "Thumbs.db",
                "*.exe",
                "*.dll",
                "*.so",
                "*.dylib",
                "*.jpg",
                "*.jpeg",
                "*.png",
                "*.gif",
                "*.bmp",
                "*.svg",
                "*.pdf",
                "*.zip",
                "*.tar",
                "*.gz",
                "*.rar",
                "*.7z",
                "*.mp3",
                "*.mp4",
                "*.avi",
                "*.mov",
                "*.wav",
                "*.flac",
                "*.ogg",
            ],
        },
        "index_dirs": [
            ".",
            {"path": ".git", "exclude": True},
            {"path": "node_modules", "exclude": True},
            {"path": ".venv", "exclude": True},
            {"path": "target", "exclude": True},
            {"path": "dist", "exclude": True},
            {"path": "build", "exclude": True},
        ],
        "schema_fields": {
            "title": {"weight": 2.0, "tokenizer": "en_stem"},
            "description": {"weight": 1.5, "tokenizer": "en_stem"},
            "body": {"weight": 1.0, "tokenizer": "en_stem"},
            "tags": {"weight": 1.5, "tokenizer": "default"},
            "servers": {"weight": 1.5, "tokenizer": "default"},
            "path": {"weight": 0.5, "tokenizer": "raw"},
        },
        "search": {"default_limit": 5, "show_description": False, "filters": []},
        "encoding": {
            "default_encoding": "utf-8",
            "auto_detect": True,
            "fallback_encodings": [
                "utf-8",
                "cp1252",
                "iso-8859-1",
                "cp1250",
                "cp1251",
            ],
            "file_specific_encodings": {"*.txt": "utf-8", "*.md": "utf-8"},
            "binary_extensions": [
                "*.jpg",
                "*.jpeg",
                "*.png",
                "*.gif",
                "*.bmp",
                "*.svg",
                "*.pdf",
                "*.zip",
                "*.tar",
                "*.gz",
                "*.rar",
                "*.exe",
                "*.dll",
                "*.so",
                "*.dylib",
            ],
            "detection_confidence_threshold": DEFAULT_ENCODING_CONFIDENCE_THRESHOLD,
        },
        "auto_hook": True,
    }


def _base_project_config() -> dict[str, Any]:
    return {
        "version": "1.0",
        "index_dir": ".tantivy-data",
        "global_patterns": {
            "include": ["*.md", "*.txt", "*.rst"],
            "exclude": ["*.tmp", "*~", "*.bak", "*.log"],
        },
        "schema_fields": {
            "title": {"weight": 2.0, "tokenizer": "en_stem"},
            "description": {"weight": 1.5, "tokenizer": "en_stem"},
            "body": {"weight": 1.0, "tokenizer": "en_stem"},
            "tags": {"weight": 1.5, "tokenizer": "default"},
            "servers": {"weight": 1.5, "tokenizer": "default"},
            "path": {"weight": 0.5, "tokenizer": "raw"},
        },
        "search": {"default_limit": 5, "show_description": False, "filters": []},
        "auto_hook": True,
    }


def get_default_config_for_project_type(project_type: str) -> dict[str, Any]:
    """Return default configuration for a detected project type."""
    project_configs = {
        "python": {
            "index_dirs": [
                "docs/**",
                "src/**/*.md",
                "tests/**/*.md",
                "*.md",
                {"path": ".venv", "exclude": True},
                {"path": "__pycache__", "exclude": True},
                {"path": "**/.*", "exclude": True},
            ]
        },
        "nodejs": {
            "index_dirs": [
                "docs/**",
                "src/**/*.md",
                "*.md",
                {"path": "node_modules", "exclude": True},
                {"path": "dist", "exclude": True},
                {"path": "build", "exclude": True},
                {"path": "**/.*", "exclude": True},
            ]
        },
        "java": {
            "index_dirs": [
                "docs/**",
                "src/**/*.md",
                "*.md",
                {"path": "target", "exclude": True},
                {"path": ".idea", "exclude": True},
                {"path": "**/.*", "exclude": True},
            ]
        },
        "rust": {
            "index_dirs": [
                "docs/**",
                "src/**/*.md",
                "*.md",
                {"path": "target", "exclude": True},
                {"path": "**/.*", "exclude": True},
            ]
        },
        "generic": {
            "index_dirs": [
                "docs/**",
                "*.md",
                "*.txt",
                "*.rst",
                {"path": "**/.*", "exclude": True},
                {"path": "node_modules", "exclude": True},
                {"path": "target", "exclude": True},
                {"path": "dist", "exclude": True},
                {"path": "build", "exclude": True},
            ]
        },
    }

    config = _base_project_config()
    config.update(
        copy.deepcopy(project_configs.get(project_type, project_configs["generic"]))
    )
    return config


def validate_search_filters(config: dict[str, Any]) -> None:
    """Validate search filter configuration."""
    search_config = config.get("search", {})
    filters = search_config.get("filters")

    if filters is None:
        return

    if not isinstance(filters, list):
        raise ValidationError(
            message="search.filters must be a list",
            parameter="search.filters",
            expected="list",
            got=type(filters).__name__,
        )

    for i, filter_config in enumerate(filters):
        if not isinstance(filter_config, dict):
            raise ValidationError(
                message=f"search.filters[{i}] must be a dict",
                parameter=f"search.filters[{i}]",
                expected="dict",
                got=type(filter_config).__name__,
            )

        if "paths" not in filter_config:
            raise ValidationError(
                message=f"search.filters[{i}] missing required 'paths' field",
                parameter=f"search.filters[{i}].paths",
                expected="non-empty list",
                got="missing",
            )

        paths = filter_config["paths"]
        if not isinstance(paths, list) or not paths:
            raise ValidationError(
                message=f"search.filters[{i}].paths must be a non-empty list",
                parameter=f"search.filters[{i}].paths",
                expected="non-empty list",
                got=f"list with {len(paths)} items"
                if isinstance(paths, list)
                else type(paths).__name__,
            )

        keywords = filter_config.get("show_on_keywords")
        if keywords is not None and not isinstance(keywords, list):
            raise ValidationError(
                message=f"search.filters[{i}].show_on_keywords must be a list",
                parameter=f"search.filters[{i}].show_on_keywords",
                expected="list",
                got=type(keywords).__name__,
            )


def validate_index_paths(config: dict[str, Any]) -> None:
    """Validate index storage and discovery paths stay project-relative."""
    index_dir = config.get("index_dir")
    if not isinstance(index_dir, str) or not index_dir:
        raise ValidationError(
            message="index_dir must be a non-empty relative path",
            parameter="index_dir",
            expected="relative path",
            got=type(index_dir).__name__,
        )
    _validate_project_relative_path(index_dir, "index_dir")

    index_dirs = config.get("index_dirs")
    if not isinstance(index_dirs, list):
        raise ValidationError(
            message="index_dirs must be a list",
            parameter="index_dirs",
            expected="list",
            got=type(index_dirs).__name__,
        )

    for i, item in enumerate(index_dirs):
        if isinstance(item, str):
            _validate_project_relative_path(item, f"index_dirs[{i}]")
        elif isinstance(item, dict):
            path = item.get("path", "")
            if not isinstance(path, str) or not path:
                raise ValidationError(
                    message=f"index_dirs[{i}].path must be a non-empty relative path",
                    parameter=f"index_dirs[{i}].path",
                    expected="relative path",
                    got=type(path).__name__,
                )
            _validate_project_relative_path(path, f"index_dirs[{i}].path")
        else:
            raise ValidationError(
                message=f"index_dirs[{i}] must be a path or object",
                parameter=f"index_dirs[{i}]",
                expected="string or object",
                got=type(item).__name__,
            )


def _validate_project_relative_path(path: str, parameter: str) -> None:
    if os.path.isabs(path):
        raise ValidationError(
            message=f"{parameter} must be relative to the project root",
            parameter=parameter,
            expected="relative path",
            got=path,
        )

    if ".." in path.split(os.sep) or ".." in path.split("/"):
        raise ValidationError(
            message=f"{parameter} must not contain parent traversal",
            parameter=parameter,
            expected="path without '..'",
            got=path,
        )


def load_config(config_path: str) -> dict[str, Any]:
    """Load configuration from JSON file with defaults."""
    defaults = default_config()

    if not os.path.exists(config_path):
        return defaults

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ConfigError(
            message=f"Error loading config: {e}",
            config_path=config_path,
        ) from e

    config = {**defaults, **user_config}
    validate_index_paths(config)
    validate_search_filters(config)
    return config


def config_example_text() -> str:
    """Return example configuration text with explanations."""
    return """{
  // Configuration file: .tantivy2agents.json
  // Place in project root directory

  "version": "1.0",

  // Where to store the index (relative to project root)
  "index_dir": ".tantivy-data",

  // Global patterns applied to all files
  "global_patterns": {
    "include": ["*.md", "*.txt", "*.rst"],  // File types to index
    "exclude": [                             // Files to skip
      "*.tmp", "*~", "*.bak", "*.log",
      "*.exe", "*.dll", "*.so",
      "*.jpg", "*.png", "*.pdf"
    ]
  },

  // Directories to index (relative to project root)
  // Use glob patterns like "src/**/*.md" for recursive matching
  "index_dirs": [
    ".",                                    // Current directory
    "docs/**/*.md",                         // All .md files in docs/
    {"path": ".git", "exclude": true},      // Exclude .git directory
    {"path": "node_modules", "exclude": true},
    {"path": ".venv", "exclude": true},
    {"path": "target", "exclude": true}
  ],

  // Search field configuration with weights
  "schema_fields": {
    "title": {"weight": 2.0, "tokenizer": "en_stem"},   // Higher weight = more important
    "description": {"weight": 1.5, "tokenizer": "en_stem"},  // From YAML frontmatter
    "body": {"weight": 1.0, "tokenizer": "en_stem"},
    "tags": {"weight": 1.5, "tokenizer": "default"},
    "servers": {"weight": 1.5, "tokenizer": "default"},
    "path": {"weight": 0.5, "tokenizer": "raw"}
  },

  // Search settings
  "search": {
    "default_limit": 5,          // Default number of results
    "show_description": false,    // Keep text output compact by default
    "filters": [                  // Path-based result filters
      {
        "name": "incidents",      // Filter name (for debugging)
        "paths": ["incidents/"],  // Paths to filter
        "hidden": true,           // Hide by default
        "show_on_keywords": ["incident", "emergency"]  // Keywords that show results
      }
    ]
  },

  // Encoding detection settings
  "encoding": {
    "default_encoding": "utf-8",
    "auto_detect": true,
    "fallback_encodings": ["utf-8", "cp1252", "iso-8859-1", "cp1250"],
    "detection_confidence_threshold": 0.7
  },

  // Automatically install Claude Code hooks
  "auto_hook": true
}

QUICK START:
  1. Run 'tantivy2agents install' in your project - auto-detects project type
  2. Or create .tantivy2agents.json manually with above template
  3. Run 'tantivy2agents index' to build the index
  4. Run 'tantivy2agents search "your query"' to search

PROJECT TYPE AUTO-DETECTION:
  - Python: indexes docs/, src/**/*.md, *.md (excludes .venv, __pycache__)
  - Node.js: indexes docs/, src/**/*.md (excludes node_modules)
  - Java/Rust/Go: indexes docs/, src/**/*.md (excludes target/, build/)
  - Generic: indexes docs/, *.md, *.txt

MARKDOWN FRONTMATTER:
  Files with YAML frontmatter are parsed for metadata:
  ---
  title: Document Title
  description: Brief summary of the document content
  tags: [api, guide]
  servers: [prod, staging]
  ---
  Document content here...

  The description field is shown in search results when show_description is true.
"""
