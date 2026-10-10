"""Read gateway: ``outline``, ``read`` and ``usage`` over indexed documents.

Agents read indexed documents through these commands so the usage log can
join each read to the search that surfaced it. Only files the current
configuration would index are readable; the index itself is never opened.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import TYPE_CHECKING, Any, Optional

from .exceptions import DocumentAccessError, ValidationError
from .files import collect_files_for_indexing, is_binary_file, is_indexed_path
from .paths import is_inside, to_index_path
from .sections import Outline, Section, find_section, parse_outline, split_lines
from .usage import (
    UsageLog,
    build_report,
    format_report_text,
    parse_duration,
    parse_ref,
)

if TYPE_CHECKING:
    from .agent import TantivyAgent

MARKDOWN_EXTENSIONS = (".md", ".markdown")


class Document:
    """A resolved, readable indexed file."""

    def __init__(
        self,
        abs_path: str,
        path: str,
        ref: Optional[str] = None,
        search_id: Optional[str] = None,
        rank: Optional[int] = None,
    ) -> None:
        self.abs_path = abs_path
        self.path = path
        self.ref = ref
        self.search_id = search_id
        self.rank = rank

    @property
    def is_markdown(self) -> bool:
        return self.path.lower().endswith(MARKDOWN_EXTENSIONS)

    def origin(self) -> dict[str, Any]:
        return {"ref": self.ref, "search_id": self.search_id, "rank": self.rank}


def parse_line_range(value: str, line_count: int) -> tuple[int, int]:
    """Parse ``A-B``, ``A-`` or ``A`` (1-based, inclusive) and clamp to the file."""
    raw = value.strip()
    start_text, sep, end_text = raw.partition("-")
    try:
        start = int(start_text)
        end = int(end_text) if end_text else (line_count if sep else start)
    except ValueError:
        start = end = 0
    if start < 1 or end < start:
        raise ValidationError(
            message=f"Invalid line range: {value}",
            parameter="--lines",
            expected="A-B, A- or A with 1 <= A <= B",
            got=value,
        )
    if start > line_count:
        raise ValidationError(
            message=f"Line {start} is past the end of the file ({line_count} lines)",
            parameter="--lines",
            got=value,
        )
    return start, min(end, line_count)


class ReadGateway:
    def __init__(self, agent: "TantivyAgent") -> None:
        self.agent = agent
        self.project_root = agent.project_root
        self.config = agent.config
        self.data_dir = os.path.join(self.project_root, self.config["index_dir"])
        self.usage = UsageLog(self.data_dir, self.config)

    # -- resolution -------------------------------------------------------

    def resolve(self, target: str) -> Document:
        """Turn a ref or a project-relative/absolute path into a Document."""
        ref = parse_ref(target)
        if ref:
            return self._resolve_ref(target.strip(), *ref)

        if os.path.isabs(target):
            abs_path = os.path.normpath(target)
        else:
            abs_path = os.path.normpath(os.path.join(self.project_root, target))
        return self._document(abs_path, target)

    def _resolve_ref(self, ref: str, search_id: str, rank: int) -> Document:
        if not self.usage.enabled:
            raise DocumentAccessError(
                "Refs need the usage log, which is disabled",
                ref,
                hint="Pass the file path instead",
            )
        search = self.usage.find_search(search_id)
        path = None
        if search:
            for result in search.get("results") or []:
                if isinstance(result, dict) and result.get("rank") == rank:
                    path = result.get("path")
        if not path:
            raise DocumentAccessError(
                f"Unknown or expired ref: {ref}",
                ref,
                hint="Run the search again or pass the file path",
            )
        abs_path = os.path.normpath(os.path.join(self.project_root, path))
        document = self._document(abs_path, ref)
        document.ref, document.search_id, document.rank = ref, search_id, rank
        return document

    def _document(self, abs_path: str, target: str) -> Document:
        root = os.path.realpath(self.project_root)
        if is_inside(root, os.path.realpath(abs_path)) is not True:
            raise DocumentAccessError(
                "Path is outside the project", target, hint="Read indexed files only"
            )
        if not os.path.isfile(abs_path):
            raise DocumentAccessError(f"File not found: {target}", target)
        if not is_indexed_path(self.config, self.project_root, abs_path):
            raise DocumentAccessError(
                f"Not an indexed file: {target}",
                target,
                hint="Only files matched by .tantivy2agents.json can be read; "
                "see 'tantivy2agents list'",
            )
        path = to_index_path(os.path.relpath(abs_path, self.project_root))
        return Document(abs_path, path)

    def _load(self, document: Document) -> tuple[str, str]:
        """Return (text, sha256 of the raw bytes)."""
        try:
            with open(document.abs_path, "rb") as f:
                raw = f.read()
        except OSError as e:
            raise DocumentAccessError(f"Cannot read file: {e}", document.path) from e
        if is_binary_file(document.abs_path, raw, self.config.get("encoding", {})):
            raise DocumentAccessError("Binary file", document.path)
        text, encoding = self.agent._read_file_with_encoding_detection(
            document.abs_path
        )
        if text is None:
            raise DocumentAccessError(f"Cannot decode file ({encoding})", document.path)
        return text, hashlib.sha256(raw).hexdigest()

    def current_sha256(self, document: Document) -> str:
        with open(document.abs_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def _outline(self, document: Document, text: str) -> Outline:
        if document.is_markdown:
            return parse_outline(text)
        return Outline(len(split_lines(text)), None, None, [])

    def _log_read(
        self,
        document: Document,
        mode: str,
        sha256: str,
        size: int,
        section: Optional[str] = None,
        lines: Optional[list[int]] = None,
    ) -> None:
        self.usage.append(
            {
                "type": "read",
                "path": document.path,
                "mode": mode,
                "section": section,
                "lines": lines,
                "bytes": size,
                "sha256": sha256,
                **document.origin(),
            }
        )

    # -- commands ---------------------------------------------------------

    def outline_command(self, target: str, format_output: str = "text") -> None:
        document = self.resolve(target)
        text, sha256 = self._load(document)
        outline = self._outline(document, text)

        if format_output == "json":
            body = json.dumps(
                {
                    "path": document.path,
                    "ref": document.ref,
                    "line_count": outline.line_count,
                    "frontmatter": _range(outline.frontmatter),
                    "preamble": _range(outline.preamble),
                    "sections": [s.to_dict() for s in outline.sections],
                },
                indent=2,
                ensure_ascii=False,
            )
        else:
            rows = [f"### FILE: {document.path}"]
            if document.ref:
                rows.append(f"REF: {document.ref}")
            rows.append(f"LINES: {outline.line_count}")
            for pseudo in (outline.frontmatter, outline.preamble):
                if pseudo:
                    rows.append(f"{pseudo.start}-{pseudo.end} {pseudo.slug}")
            for s in outline.sections:
                rows.append(
                    f"{s.start}-{s.end} {'#' * s.level} {s.title} {{#{s.slug}}}"
                )
            if not outline.sections:
                rows.append(
                    "(no headings)"
                    if document.is_markdown
                    else "(not Markdown; use read or read --lines)"
                )
            body = "\n".join(rows)

        print(body)
        self._log_read(document, "outline", sha256, len(body.encode("utf-8")))

    def read_command(
        self,
        target: str,
        section: Optional[str] = None,
        lines: Optional[str] = None,
        numbers: bool = False,
    ) -> None:
        if section and lines:
            raise ValidationError(
                message="Use either --section or --lines, not both",
                parameter="--section/--lines",
            )
        document = self.resolve(target)
        text, sha256 = self._load(document)
        all_lines = split_lines(text)
        total = len(all_lines)

        mode, found = "full", None
        start, end = (1, total) if total else (0, 0)
        if section:
            if not document.is_markdown:
                raise ValidationError(
                    message="Sections are only available for Markdown files",
                    parameter="--section",
                    got=document.path,
                )
            found = find_section(parse_outline(text), section)
            mode, start, end = "section", found.start, found.end
        elif lines:
            mode = "lines"
            start, end = parse_line_range(lines, total)

        selected = (
            [line.rstrip("\r") for line in all_lines[start - 1 : end]] if end else []
        )
        if numbers:
            width = len(str(end or 1))
            selected = [
                f"{number:>{width}}\t{line}"
                for number, line in enumerate(selected, start=start)
            ]
        content = "".join(f"{line}\n" for line in selected)

        header = [f"### FILE: {document.path}"]
        if document.ref:
            header.append(f"REF: {document.ref}")
        if found:
            header.append(f"SECTION: {found.slug}")
        header.append(f"LINES: {start}-{end} of {total}")
        header.append("---")
        sys.stdout.write("\n".join(header) + "\n" + content)
        sys.stdout.flush()

        self._log_read(
            document,
            mode,
            sha256,
            len(content.encode("utf-8")),
            section=found.slug if found else None,
            lines=[start, end],
        )

    def recent_read_command(self, target: str, within: str) -> int:
        """Exit status 0 when PATH was read inside the window and is unchanged."""
        window = parse_duration(within, "--within")
        if not self.usage.enabled:
            print("usage log is disabled", file=sys.stderr)
            return 1
        document = self.resolve(target)
        ok, reason = self.usage.recent_read(
            document.path, window, self.current_sha256(document)
        )
        print(f"{document.path}: {reason}", file=sys.stderr)
        return 0 if ok else 1

    def usage_command(self, since: str, format_output: str = "text") -> None:
        period = parse_duration(since, "--since")
        files, _ = collect_files_for_indexing(self.config, self.project_root)
        indexed = [to_index_path(os.path.relpath(f, self.project_root)) for f in files]
        report = build_report(self.usage.records(), period, indexed)
        report["usage_log_enabled"] = self.usage.enabled
        if format_output == "json":
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            if not self.usage.enabled:
                print("Note: usage log is disabled; nothing new is recorded.")
            print(format_report_text(report))


def _range(section: Optional[Section]) -> Optional[dict[str, int]]:
    return {"start": section.start, "end": section.end} if section else None
