"""Usage log: which searches ran and which documents agents then read.

The log is append-only JSON Lines in the index data directory. It is the only
store for search refs (``<search_id>:<rank>``), so a ref stays valid while its
search record is in the current or the rotated log file.

Appends, rotation and reads take ``usage.lock``, not the index lock: the index
lock is held for a whole rebuild, and reading a document must not wait for one.
A failed write is a warning and never fails the command that triggered it.
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

from .exceptions import ConfigError, ValidationError
from .locking import IndexLock

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
LOG_FILENAME = "usage.jsonl"
ROTATED_FILENAME = "usage.1.jsonl"
USAGE_LOCK_FILENAME = "usage.lock"
USAGE_FILENAMES = (LOG_FILENAME, ROTATED_FILENAME, USAGE_LOCK_FILENAME)
DEFAULT_MAX_BYTES = 5_000_000
USAGE_ENV = "TANTIVY2AGENTS_USAGE"
AGENT_ENV = "TANTIVY2AGENTS_AGENT"
USAGE_LOCK_TIMEOUT = 10.0

REF_RE = re.compile(r"^([0-9a-f]{6}):([1-9][0-9]*)$")
_DURATION_RE = re.compile(r"^([1-9][0-9]*)([mhd])$")
_DURATION_UNITS = {"m": "minutes", "h": "hours", "d": "days"}

# Report heuristics, in seconds. Without session ids they are approximations.
WEAK_MATCH_WINDOW = 1800
REFORMULATION_WINDOW = 120
OUTLINE_FOLLOWUP_WINDOW = 600

READS_NOTE = (
    "Reads count only 'tantivy2agents read/outline'; "
    "reads with native file tools are invisible to this report."
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def format_ts(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_ts(value: Any) -> Optional[datetime]:
    try:
        moment = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def parse_duration(value: str, parameter: str) -> timedelta:
    """Parse ``30m``, ``12h`` or ``30d``."""
    match = _DURATION_RE.match(value.strip())
    if not match:
        raise ValidationError(
            message=f"Invalid duration: {value}",
            parameter=parameter,
            expected="<number><m|h|d>, e.g. 30m, 12h, 30d",
            got=value,
        )
    return timedelta(**{_DURATION_UNITS[match.group(2)]: int(match.group(1))})


def parse_ref(value: str) -> Optional[tuple[str, int]]:
    """Return ``(search_id, rank)`` when ``value`` is a ref, else None."""
    match = REF_RE.match(value.strip())
    if not match:
        return None
    return match.group(1), int(match.group(2))


def new_search_id() -> str:
    return secrets.token_hex(3)


class UsageLog:
    """Append-only usage log in one project's index data directory."""

    def __init__(self, data_dir: str, config: dict[str, Any]) -> None:
        self.data_dir = data_dir
        self.path = os.path.join(data_dir, LOG_FILENAME)
        self.rotated_path = os.path.join(data_dir, ROTATED_FILENAME)
        self._lock = IndexLock(os.path.join(data_dir, USAGE_LOCK_FILENAME))

        usage_config = config.get("usage", {})
        if not isinstance(usage_config, dict):
            raise ConfigError("Config key 'usage' must be an object")
        enabled = usage_config.get("enabled", True)
        max_bytes = usage_config.get("max_bytes", DEFAULT_MAX_BYTES)
        if not isinstance(enabled, bool):
            raise ConfigError("Config key 'usage.enabled' must be true or false")
        if (
            not isinstance(max_bytes, int)
            or isinstance(max_bytes, bool)
            or max_bytes <= 0
        ):
            raise ConfigError("Config key 'usage.max_bytes' must be a positive integer")

        env = os.getenv(USAGE_ENV, "").strip().lower()
        self.enabled = enabled and env not in {"0", "false", "no", "off"}
        self.max_bytes = max_bytes

    def append(self, record: dict[str, Any]) -> bool:
        """Write one record; return False (with a warning) when that failed."""
        if not self.enabled:
            return False
        record = {"v": SCHEMA_VERSION, "ts": format_ts(now_utc()), **record}
        agent = os.getenv(AGENT_ENV)
        if agent:
            record["agent"] = agent
        line = json.dumps(record, ensure_ascii=False) + "\n"
        encoded = line.encode("utf-8")
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with self._lock.acquire(timeout=USAGE_LOCK_TIMEOUT):
                self._rotate_if_needed(len(encoded))
                with open(self.path, "ab") as f:
                    f.write(encoded)
        except Exception as e:  # never fail the user's search or read
            logger.warning("Could not write usage log %s: %s", self.path, e)
            return False
        return True

    def _rotate_if_needed(self, incoming: int) -> None:
        try:
            size = os.path.getsize(self.path)
        except OSError:
            return
        if size and size + incoming > self.max_bytes:
            os.replace(self.path, self.rotated_path)

    def records(self) -> list[dict[str, Any]]:
        """Return all records, oldest first; malformed lines are skipped."""
        chunks = []
        if not os.path.isdir(self.data_dir):
            return []
        with self._lock.acquire(timeout=USAGE_LOCK_TIMEOUT):
            for path in (self.rotated_path, self.path):
                try:
                    with open(path, "rb") as f:
                        chunks.append(f.read())
                except FileNotFoundError:
                    continue
        records = []
        for chunk in chunks:
            for raw in chunk.decode("utf-8", "replace").splitlines():
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(record, dict) and parse_ts(record.get("ts")):
                    records.append(record)
        return records

    def find_search(self, search_id: str) -> Optional[dict[str, Any]]:
        """Return the newest search record with this id."""
        for record in reversed(self.records()):
            if record.get("type") == "search" and record.get("id") == search_id:
                return record
        return None

    def recent_read(
        self, path: str, within: timedelta, current_sha256: str
    ) -> tuple[bool, str]:
        """Check for a read of ``path`` inside ``within`` with unchanged content."""
        cutoff = now_utc() - within
        stale = False
        for record in reversed(self.records()):
            if record.get("type") != "read" or record.get("path") != path:
                continue
            if record.get("mode") == "outline":
                continue
            moment = parse_ts(record.get("ts"))
            if moment is None or moment < cutoff:
                break
            if record.get("sha256") == current_sha256:
                return True, f"read at {record['ts']} ({record.get('mode')})"
            stale = True
        if stale:
            return False, "file changed since it was last read"
        return False, "no read of this file in the window"


def _shown_paths(search: dict[str, Any]) -> dict[int, str]:
    shown = {}
    for result in search.get("results") or []:
        if isinstance(result, dict) and isinstance(result.get("rank"), int):
            shown[result["rank"]] = result.get("path", "")
    return shown


def _normalize_query(query: Any) -> str:
    return " ".join(str(query or "").split()).lower()


def build_report(
    records: Iterable[dict[str, Any]],
    since: timedelta,
    indexed_paths: Iterable[str],
    until: Optional[datetime] = None,
) -> dict[str, Any]:
    """Aggregate usage records into the stable ``usage --format json`` shape."""
    until = until or now_utc()
    start = until - since

    searches: list[dict[str, Any]] = []
    reads: list[dict[str, Any]] = []
    for record in records:
        moment = parse_ts(record.get("ts"))
        if moment is None or moment < start or moment > until:
            continue
        record = {**record, "_ts": moment}
        if record.get("type") == "search":
            searches.append(record)
        elif record.get("type") == "read":
            reads.append(record)
    searches.sort(key=lambda r: r["_ts"])
    reads.sort(key=lambda r: r["_ts"])
    search_by_id = {s.get("id"): s for s in searches}

    # (search_id, rank) pairs that were followed by a read
    read_pairs: set[tuple[str, int]] = set()
    reads_via_ref = reads_weak = 0
    without_search: dict[str, int] = {}
    for read in reads:
        if read.get("mode") == "outline":
            continue
        search_id, rank = read.get("search_id"), read.get("rank")
        if search_id in search_by_id and isinstance(rank, int):
            read_pairs.add((search_id, rank))
            reads_via_ref += 1
            continue
        match = None
        for search in reversed(searches):
            delta = (read["_ts"] - search["_ts"]).total_seconds()
            if delta < 0:
                continue
            if delta > WEAK_MATCH_WINDOW:
                break
            for shown_rank, shown_path in _shown_paths(search).items():
                if shown_path == read.get("path"):
                    match = (search.get("id"), shown_rank)
                    break
            if match:
                break
        if match:
            read_pairs.add(match)
            reads_weak += 1
        else:
            path = read.get("path", "")
            without_search[path] = without_search.get(path, 0) + 1

    rank_stats: dict[int, list[int]] = {}
    path_stats: dict[str, list[int]] = {}
    query_stats: dict[str, dict[str, int]] = {}
    zero_result: dict[str, int] = {}
    returned_paths: set[str] = set()
    searches_without_read = []
    for index, search in enumerate(searches):
        shown = _shown_paths(search)
        query = _normalize_query(search.get("query"))
        stats = query_stats.setdefault(
            query, {"searches": 0, "zero_result": 0, "with_read": 0}
        )
        stats["searches"] += 1
        if not shown:
            stats["zero_result"] += 1
            zero_result[query] = zero_result.get(query, 0) + 1
            continue
        any_read = False
        for rank, path in shown.items():
            was_read = (search.get("id"), rank) in read_pairs
            any_read = any_read or was_read
            rank_stats.setdefault(rank, [0, 0])
            rank_stats[rank][0] += 1
            rank_stats[rank][1] += int(was_read)
            if path:
                returned_paths.add(path)
                path_stats.setdefault(path, [0, 0])
                path_stats[path][0] += 1
                path_stats[path][1] += int(was_read)
        if any_read:
            stats["with_read"] += 1
            continue
        next_query = None
        if index + 1 < len(searches):
            following = searches[index + 1]
            gap = (following["_ts"] - search["_ts"]).total_seconds()
            reads_between = any(
                search["_ts"] <= r["_ts"] <= following["_ts"] for r in reads
            )
            if (
                gap <= REFORMULATION_WINDOW
                and not reads_between
                and _normalize_query(following.get("query")) != query
            ):
                next_query = following.get("query")
        searches_without_read.append(
            {
                "search_id": search.get("id"),
                "ts": search.get("ts"),
                "query": search.get("query"),
                "results": len(shown),
                "reformulated_as": next_query,
            }
        )

    outline_without_read: dict[str, int] = {}
    for index, read in enumerate(reads):
        if read.get("mode") != "outline":
            continue
        followed = any(
            other.get("path") == read.get("path")
            and other.get("mode") != "outline"
            and (other["_ts"] - read["_ts"]).total_seconds() <= OUTLINE_FOLLOWUP_WINDOW
            for other in reads[index + 1 :]
        )
        if not followed:
            path = read.get("path", "")
            outline_without_read[path] = outline_without_read.get(path, 0) + 1

    section_reads: dict[str, dict[str, int]] = {}
    for read in reads:
        if read.get("mode") == "section" and read.get("section"):
            per_doc = section_reads.setdefault(read.get("path", ""), {})
            per_doc[read["section"]] = per_doc.get(read["section"], 0) + 1

    def counted(mapping: dict[str, int], key: str) -> list[dict[str, Any]]:
        return [
            {key: name, "count": count}
            for name, count in sorted(mapping.items(), key=lambda i: (-i[1], i[0]))
        ]

    return {
        "schema_version": SCHEMA_VERSION,
        "since": format_ts(start),
        "until": format_ts(until),
        "totals": {
            "searches": len(searches),
            "zero_result_searches": sum(zero_result.values()),
            "reads": sum(1 for r in reads if r.get("mode") != "outline"),
            "outlines": sum(1 for r in reads if r.get("mode") == "outline"),
            "reads_via_ref": reads_via_ref,
            "reads_weak_match": reads_weak,
            "reads_without_search": sum(without_search.values()),
        },
        "rank_ctr": [
            {
                "rank": rank,
                "shown": shown,
                "read": read,
                "rate": round(read / shown, 4),
            }
            for rank, (shown, read) in sorted(rank_stats.items())
        ],
        "queries": [
            {"query": query, **stats}
            for query, stats in sorted(
                query_stats.items(), key=lambda i: (-i[1]["searches"], i[0])
            )
        ],
        "zero_result_queries": counted(zero_result, "query"),
        "searches_without_t2a_read": searches_without_read,
        "returned_not_read_via_t2a": [
            {"path": path, "returned": returned}
            for path, (returned, read) in sorted(
                path_stats.items(), key=lambda i: (-i[1][0], i[0])
            )
            if read == 0
        ],
        "outline_without_t2a_read": counted(outline_without_read, "path"),
        "reads_without_search": counted(without_search, "path"),
        "sections": [
            {"path": path, "sections": counted(per_doc, "section")}
            for path, per_doc in sorted(section_reads.items())
        ],
        "never_returned": sorted(set(indexed_paths) - returned_paths),
        "note": READS_NOTE,
        "heuristics": {
            "weak_match_window_s": WEAK_MATCH_WINDOW,
            "reformulation_window_s": REFORMULATION_WINDOW,
            "outline_followup_window_s": OUTLINE_FOLLOWUP_WINDOW,
        },
    }


def format_report_text(report: dict[str, Any], top: int = 10) -> str:
    """Render the report compactly for people and agents."""
    totals = report["totals"]
    out = [
        f"Usage {report['since']} .. {report['until']}",
        (
            f"Searches: {totals['searches']} "
            f"(zero results: {totals['zero_result_searches']})"
        ),
        (
            f"Reads: {totals['reads']} (via ref {totals['reads_via_ref']}, "
            f"weak match {totals['reads_weak_match']}, "
            f"without search {totals['reads_without_search']}), "
            f"outlines: {totals['outlines']}"
        ),
        f"Note: {report['note']}",
    ]

    def section(title: str, rows: list[str]) -> None:
        out.append("")
        out.append(f"## {title}")
        out.extend(rows[:top] if rows else ["(none)"])
        if len(rows) > top:
            out.append(f"... {len(rows) - top} more (use --format json)")

    section(
        "Read-through by rank",
        [
            f"{r['rank']}: {r['read']}/{r['shown']} ({r['rate']:.0%})"
            for r in report["rank_ctr"]
        ],
    )
    section(
        "Queries",
        [
            f"{q['searches']}x {q['query']} (read {q['with_read']}, "
            f"zero {q['zero_result']})"
            for q in report["queries"]
        ],
    )
    section(
        "Zero-result queries",
        [f"{q['count']}x {q['query']}" for q in report["zero_result_queries"]],
    )
    section(
        "Searches without a t2a read",
        [
            f"{s['ts']} {s['query']}"
            + (
                f" -> reformulated: {s['reformulated_as']}"
                if s["reformulated_as"]
                else ""
            )
            for s in report["searches_without_t2a_read"]
        ],
    )
    section(
        "Returned but not read via t2a",
        [f"{p['returned']}x {p['path']}" for p in report["returned_not_read_via_t2a"]],
    )
    section(
        "Outline without a follow-up t2a read",
        [f"{p['count']}x {p['path']}" for p in report["outline_without_t2a_read"]],
    )
    section(
        "Most-read sections",
        [
            f"{doc['path']}: "
            + ", ".join(f"{s['section']} ({s['count']})" for s in doc["sections"])
            for doc in report["sections"]
        ],
    )
    section(
        "Reads without a search",
        [f"{p['count']}x {p['path']}" for p in report["reads_without_search"]],
    )
    section("Never returned", list(report["never_returned"]))
    return "\n".join(out)
