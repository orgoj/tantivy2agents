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
) -> None:
    """Export results in specified format."""
    fmt = format_output.lower()
    if fmt == "json":
        export_json(results, query, output_file, config)
    elif fmt == "csv":
        export_csv(results, query, output_file, config)
    elif fmt in {"text", "txt"}:
        export_text(results, query, output_file, config)
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
) -> None:
    """Export results as JSON."""
    export_data = {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "total_results": len(results),
        "results": [],
    }

    show_description = config.get("search", {}).get("show_description", True)

    for score, doc_address, doc in results:
        fields = extract_document_fields(doc, include_description=show_description)
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
) -> None:
    """Export results as CSV."""
    if output_file:
        file_handle = open(output_file, "w", newline="", encoding="utf-8")
    else:
        file_handle = sys.stdout

    show_description = config.get("search", {}).get("show_description", True)

    try:
        writer = csv.writer(file_handle)

        if show_description:
            writer.writerow(
                ["Score", "Path", "Title", "Description", "Tags", "Servers"]
            )
        else:
            writer.writerow(["Score", "Path", "Title", "Tags", "Servers"])

        for score, doc_address, doc in results:
            fields = extract_document_fields(doc, include_description=show_description)
            row = [f"{score:.4f}", fields["path"], fields["title"]]
            if show_description:
                row.append(fields["description"])
            row.extend([fields["tags"], fields["servers"]])
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
) -> None:
    """Export results as structured text for easy parsing."""
    if output_file:
        file_handle = open(output_file, "w", encoding="utf-8")
    else:
        file_handle = sys.stdout

    show_description = config.get("search", {}).get("show_description", True)

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
