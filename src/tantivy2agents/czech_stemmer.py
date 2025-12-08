"""
Czech Stemming Support for Tantivy Agent.

Lightweight Czech stemmer for morphological normalization.
Removes common Czech suffixes to enable search across different word forms.
"""

import re


def czech_stem(word):
    """
    Simple Czech stemmer - removes common suffixes for better search.

    Handles:
    - Adjective endings: -y/-a/-e/-i, -eho/-emu/-ym/-em, -ou/-ymi
    - Noun endings: -a/-y/-e/-u/-em/-um/-ech/-ami/-ach
    - Verb endings: -it/-at/-et, -il/-al/-el, -im/-am/-em, -ime/-ame/-eme

    Examples:
        dokoncit -> dokonc
        dokoncil -> dokonc
        dokonceny -> dokonc
        dokonceno -> dokonc
        ukol -> ukol
        ukoly -> ukol
    """
    word = word.lower().strip()

    # Don't stem very short words
    if len(word) < 4:
        return word

    # Suffixes ordered by length (longest first) to avoid partial matches
    suffixes = [
        # Adjective forms (7+ chars)
        "ejsiho",
        "ejsimu",
        "ejsim",
        "ejsich",
        # Adjective forms (6 chars)
        "ejsim",
        "ejsi",
        # Verb forms (5+ chars)
        "ovat",
        "ovala",
        "ovalo",
        "ovali",
        "ovaly",
        # Adjective forms (4+ chars)
        "eho",
        "emu",
        "ymi",
        "ych",
        "ymi",
        # Noun plurals (4 chars)
        "ech",
        "ami",
        "ach",
        "um",
        # Verb passive/neuter (3 chars)
        "eno",
        "ano",
        # Verb past tense (3 chars)
        "ila",
        "ilo",
        "ili",
        "ily",
        # Adjective forms (3 chars)
        "ym",
        "em",
        "ou",
        # Noun forms (2-3 chars)
        "um",
        "ich",
        "um",
        # Common verb infinitives (2 chars)
        "it",
        "at",
        "et",
        # Past tense singular (2 chars)
        "il",
        "al",
        "el",
        # Present tense (3 chars)
        "ime",
        "ame",
        "eme",
        # Present tense singular (2 chars)
        "im",
        "am",
        "em",
        "is",
        "as",
        "es",
        # Adjectives (2 chars)
        "y",
        "a",
        "e",
        "i",
        # Nouns (1-2 char, only if stem will be 3+ chars)
        "u",
        "a",
        "y",
        "e",
        "u",
    ]

    for suffix in suffixes:
        if word.endswith(suffix):
            stem = word[: -len(suffix)]
            # Keep minimum stem length of 3 characters
            if len(stem) >= 3:
                return stem

    return word


def normalize_czech_text(text):
    """
    Normalize Czech text for indexing/searching.
    Applies stemming to all words while preserving structure.

    Args:
        text: Input text in Czech

    Returns:
        Normalized text with stemmed words
    """
    # Split by non-word characters, preserve structure
    words = re.findall(r"\w+|\W+", text)
    normalized = []

    for part in words:
        if re.match(r"\w+", part):
            # It's a word - stem it
            normalized.append(czech_stem(part))
        else:
            # It's punctuation/whitespace - keep as is
            normalized.append(part)

    return "".join(normalized)
