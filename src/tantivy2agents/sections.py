"""Markdown outline: headings, section slugs and line ranges.

Line numbers count the raw file, frontmatter included, 1-based and inclusive,
so they match what a native editor shows. Only ``\\n`` separates lines; a
trailing ``\\r`` is part of the line (CRLF files keep their line endings).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Optional

from .exceptions import ValidationError

FRONTMATTER = "frontmatter"
PREAMBLE = "preamble"

_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
_CLOSING_HASHES_RE = re.compile(r"(?:^|[ \t]+)#+$")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_SLUG_DROP_RE = re.compile(r"[^\w\- ]", re.UNICODE)


@dataclass
class Section:
    """One addressable part of a document."""

    slug: str
    title: str
    level: int  # 1-6 for headings, 0 for frontmatter/preamble
    start: int
    end: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Outline:
    line_count: int
    frontmatter: Optional[Section]
    preamble: Optional[Section]
    sections: list[Section]


def split_lines(text: str) -> list[str]:
    """Split on ``\\n`` only, the way editors number lines."""
    if not text:
        return []
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    return lines


def slugify(title: str) -> str:
    """GitHub-style anchor: lowercase, drop punctuation, spaces to hyphens."""
    slug = _SLUG_DROP_RE.sub("", title.strip().lower())
    return slug.replace(" ", "-")


def strip_diacritics(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _frontmatter_end(lines: list[str]) -> int:
    """Return the closing ``---`` line number, or 0 when there is none."""
    if not lines or lines[0].rstrip("\r") != "---":
        return 0
    for number, line in enumerate(lines[1:], start=2):
        if line.rstrip("\r") == "---":
            return number
    return 0


def _parse_heading(line: str) -> Optional[tuple[int, str]]:
    match = _HEADING_RE.match(line.rstrip("\r"))
    if not match:
        return None
    title = _CLOSING_HASHES_RE.sub("", match.group(2) or "").strip()
    return len(match.group(1)), title


def parse_outline(text: str) -> Outline:
    """Parse ATX headings outside fenced code blocks into sections."""
    lines = split_lines(text)
    total = len(lines)

    fm_end = _frontmatter_end(lines)
    frontmatter = Section(FRONTMATTER, FRONTMATTER, 0, 1, fm_end) if fm_end else None

    headings: list[tuple[int, int, str]] = []
    fence: Optional[str] = None
    for number in range(fm_end + 1, total + 1):
        line = lines[number - 1].rstrip("\r")
        fence_match = _FENCE_RE.match(line)
        if fence:
            if (
                fence_match
                and fence_match.group(1)[0] == fence[0]
                and len(fence_match.group(1)) >= len(fence)
                and not line.strip().lstrip(fence[0])
            ):
                fence = None
            continue
        if fence_match:
            fence = fence_match.group(1)
            continue
        heading = _parse_heading(line)
        if heading:
            headings.append((number, heading[0], heading[1]))

    sections: list[Section] = []
    used: set[str] = set()
    counts: dict[str, int] = {}
    for index, (start, level, title) in enumerate(headings):
        end = total
        for next_start, next_level, _ in headings[index + 1 :]:
            if next_level <= level:
                end = next_start - 1
                break
        base = slugify(title) or "section"
        slug = base
        while slug in used:
            counts[base] = counts.get(base, 0) + 1
            slug = f"{base}-{counts[base]}"
        used.add(slug)
        sections.append(Section(slug, title, level, start, end))

    preamble = None
    preamble_end = headings[0][0] - 1 if headings else total
    if preamble_end > fm_end and any(
        lines[n].strip() for n in range(fm_end, preamble_end)
    ):
        preamble = Section(PREAMBLE, PREAMBLE, 0, fm_end + 1, preamble_end)

    # A real heading with the same slug wins over the pseudo-section.
    if frontmatter and FRONTMATTER in used:
        frontmatter = None
    if preamble and PREAMBLE in used:
        preamble = None

    return Outline(total, frontmatter, preamble, sections)


def find_section(outline: Outline, name: str) -> Section:
    """Resolve ``--section``: slug, then heading text, then ASCII slug."""
    candidates = [s for s in (outline.frontmatter, outline.preamble) if s]
    candidates += outline.sections

    wanted = name.strip()
    for section in candidates:
        if section.slug == wanted:
            return section

    folded = " ".join(wanted.split()).casefold()
    by_title = [
        s for s in outline.sections if " ".join(s.title.split()).casefold() == folded
    ]
    if len(by_title) == 1:
        return by_title[0]

    ascii_wanted = strip_diacritics(wanted.lower())
    by_ascii = [s for s in candidates if strip_diacritics(s.slug) == ascii_wanted]
    if len(by_ascii) == 1:
        return by_ascii[0]

    available = ", ".join(s.slug for s in candidates) or "(none)"
    ambiguous = len(by_title) > 1 or len(by_ascii) > 1
    raise ValidationError(
        message=(
            f"Section '{name}' is ambiguous"
            if ambiguous
            else f"Section '{name}' not found"
        ),
        parameter="--section",
        got=name,
        expected=f"one of: {available}",
    )
