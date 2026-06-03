"""Search result formatting and export."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from typing import Any

from .exceptions import ValidationError


def export_results(
    results: list[tuple[float, Any, Any]],
    query: str,
    format_output: str,
    output_file: str | None,
    config: dict[str, Any],
    show_snippets: bool = False,
) -> None:
    """Export results in specified format."""
    fmt = format_output.lower()
    if fmt == "json":
        export_json(results, query, output_file, config, show_snippets=show_snippets)
    elif fmt == "csv":
        export_csv(results, query, output_file, config, show_snippets=show_snippets)
    elif fmt in {"text", "txt"}:
        export_text(results, query, output_file, config, show_snippets=show_snippets)
    else:
        raise ValidationError(
            message="Unsupported output format",
            parameter="format",
            expected="json, csv, text",
            got=format_output,
        )


def export_json(
    results: list[tuple[float, Any, Any]],
    query: str,
    output_file: str | None,
    config: dict[str, Any],
    show_snippets: bool = False,
) -> None:
    """Export results as JSON."""
    export_data = {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "total_results": len(results),
        "results": [],
    }

    show_description = config.get("search", {}).get("show_description", False)

    for score, doc_address, doc in results:
        fields = extract_document_fields(doc, include_description=show_description)
        if show_snippets:
            fields["snippet"] = extract_snippet(doc, query)
        result_item = {"score": round(score, 4), **fields}
        export_data["results"].append(result_item)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        print(f"Results exported to {output_file}")
    else:
        print(json.dumps(export_data, indent=2, ensure_ascii=False))


def export_csv(
    results: list[tuple[float, Any, Any]],
    query: str,
    output_file: str | None,
    config: dict[str, Any],
    show_snippets: bool = False,
) -> None:
    """Export results as CSV."""
    if output_file:
        file_handle = open(output_file, "w", newline="", encoding="utf-8")
    else:
        file_handle = sys.stdout

    show_description = config.get("search", {}).get("show_description", False)

    try:
        writer = csv.writer(file_handle)

        header = ["Score", "Path", "Title"]
        if show_description:
            header.append("Description")
        header.extend(["Tags", "Servers"])
        if show_snippets:
            header.append("Snippet")
        writer.writerow(header)

        for score, doc_address, doc in results:
            fields = extract_document_fields(doc, include_description=show_description)
            row = [f"{score:.4f}", fields["path"], fields["title"]]
            if show_description:
                row.append(fields["description"])
            row.extend([fields["tags"], fields["servers"]])
            if show_snippets:
                row.append(extract_snippet(doc, query))
            writer.writerow(row)

        if output_file:
            print(f"Results exported to {output_file}")
        else:
            print()

    finally:
        if output_file:
            file_handle.close()


def export_text(
    results: list[tuple[float, Any, Any]],
    query: str,
    output_file: str | None,
    config: dict[str, Any],
    show_snippets: bool = False,
) -> None:
    """Export results as structured text for easy parsing."""
    if output_file:
        file_handle = open(output_file, "w", encoding="utf-8")
    else:
        file_handle = sys.stdout

    show_description = config.get("search", {}).get("show_description", False)

    try:
        for score, doc_address, doc in results:
            fields = extract_document_fields(doc, include_description=show_description)

            file_handle.write(f"### FILE: {fields['path']}\n")
            if fields["title"]:
                file_handle.write(f"TITLE: {fields['title']}\n")
            if show_description and fields.get("description"):
                file_handle.write(f"DESCRIPTION: {fields['description']}\n")
            file_handle.write(f"SCORE: {score:.4f}\n")
            if fields["tags"]:
                file_handle.write(f"TAGS: {fields['tags']}\n")
            if fields["servers"]:
                file_handle.write(f"SERVERS: {fields['servers']}\n")
            if show_snippets:
                snippet = extract_snippet(doc, query)
                if snippet:
                    file_handle.write(f"SNIPPET: {snippet}\n")
            file_handle.write("---\n")

        if output_file:
            print(f"Results exported to {output_file}")

    finally:
        if output_file:
            file_handle.close()


def extract_document_fields(
    doc: Any, include_description: bool = True
) -> dict[str, str]:
    """Extract display fields from a Tantivy document."""
    fields = {
        "path": doc["path"][0] if doc["path"] else "",
        "title": doc["title"][0] if doc["title"] else "",
        "tags": doc["tags"][0] if doc["tags"] else "",
        "servers": doc["servers"][0] if doc["servers"] else "",
    }

    if include_description:
        fields["description"] = doc["description"][0] if doc["description"] else ""

    return fields


def extract_snippet(doc: Any, query: str, max_chars: int = 240) -> str:
    """Return a compact one-line snippet from the stored original body."""
    try:
        body_values = doc["snippet"] if doc["snippet"] else []
    except (KeyError, TypeError):
        body_values = []
    if not body_values:
        return ""

    body = str(body_values[0])
    query_terms = [term.lower() for term in query.split() if term.strip()]
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines:
        return ""

    selected = lines[0]
    for line in lines:
        lower_line = line.lower()
        if any(term in lower_line for term in query_terms):
            selected = line
            break

    selected = " ".join(selected.split())
    if len(selected) <= max_chars:
        return selected
    return selected[: max_chars - 3].rstrip() + "..."
