"""
Tantivy Agent - Tantivy-based document indexing agent for Claude Code.

A fast, lightweight document indexing and search solution using the Tantivy
search engine. Designed for integration with Claude Code via hooks.
"""

__version__ = "0.7.17"

from .agent import TantivyAgent
from .czech_stemmer import czech_stem, normalize_czech_text

__all__ = [
    "__version__",
    "TantivyAgent",
    "czech_stem",
    "normalize_czech_text",
]
