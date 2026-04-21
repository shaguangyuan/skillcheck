from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3

from skill_health.inventory import default_skill_roots
from skill_health.storage import initialize_database

CODEX_SOURCE = "codex_session_skill_file"
ACTIVATION_REASON = "skill_file_loaded"

COMMAND_PATTERN = re.compile(
    r"""(?ix)
    (?:
        get-content
        |
        cat
    )
    \s+
    (?:
        ["'](?P<quoted>[^"']*SKILL\.md)["']
        |
        (?P<plain>\S*SKILL\.md)
    )
    """
)


@dataclass(frozen=True)
class CodexImportResult:
    sessions_found: int
    imported_events: int


def _to_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _serialize_dt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _extract_skill_path(text: str) -> Path | None:
    match = COMMAND_PATTERN.search(text)
    if not match:
        return None
    path_text = (match.group("quoted") or match.group("plain") or "").strip()
    if not path_text:
        return None
    return Path(path_text).expanduser()


def _extract_skill_path_from_payload(payload: dict) -> Path | None:
    candidate_fields = ["command", "tool_input", "input", "text", "_raw"]
    for field in candidate_fields:
        value = payload.get(field)
        if isinstance(value, str):
            maybe_path = _extract_skill_path(value)
            if maybe_path is not None:
                return maybe_path
    for value in payload.values():
        if isinstance(value, str):
            maybe_path = _extract_skill_path(value)
            if maybe_path is not None:
                return maybe_path
    return None


def _is_inside_roots(skill_path: Path, roots: list[Path]) -> bool:
    for root in roots:
        try:
            skill_path.resolve().relative_to(root.resolve())
            return True
        except Exception:
            continue
    return False


def _safe_parse_dt(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _skill_name_from_file(skill_file: Path) -> str:
    try:
        content = skill_file.read_text(encoding="utf-8")
    except Exception:
        return skill_file.parent.name

    stripped = content.lstrip()
    if not stripped.startswith("---"):
        return skill_file.parent.name
    lines = stripped.splitlines()
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip() == "name":
            declared = value.strip()
            if declared:
                return declared
    return skill_file.parent.name


def _event_id(
    *,
    session_id: str,
    raw_event_ref: str,
    skill_id: str,
) -> str:
    base = f"{CODEX_SOURCE}|{session_id}|{raw_event_ref}|{skill_id}"
    return sha256(base.encode("utf-8")).hexdigest()


def _extract_candidates_from_jsonl(session_file: Path) -> list[tuple[int, str, dict]]:
    candidates: list[tuple[int, str, dict]] = []
    session_id = session_file.stem
    try:
        lines = session_file.read_text(encoding="utf-8").splitlines()
    except Exception:
        return candidates

    for index, line in enumerate(lines, start=1):
        if "SKILL.md" not in line:
            continue
        payload: dict = {}
        try:
            maybe_json = json.loads(line)
            if isinstance(maybe_json, dict):
                payload = maybe_json
        except json.JSONDecodeError:
            payload = {}
        candidates.append((index, session_id, payload | {"_raw": line}))
    return candidates


def _extract_from_logs_sqlite(logs_path: Path) -> list[tuple[str, int, str]]:
    candidates: list[tuple[str, int, str]] = []
    if not logs_path.exists():
        return candidates

    try:
        connection = sqlite3.connect(logs_path)
    except sqlite3.Error:
        return candidates

    try:
        tables = connection.execute(
            "select name from sqlite_master where type = 'table'"
        ).fetchall()
        for (table_name,) in tables:
            pragma = connection.execute(f'pragma table_info("{table_name}")').fetchall()
            text_columns = [
                row[1]
                for row in pragma
                if str(row[2]).lower() in {"text", "varchar", "json"}
            ]
            for column in text_columns:
                try:
                    rows = connection.execute(
                        f'select rowid, "{column}" from "{table_name}" where lower("{column}") like ?',
                        ("%skill.md%",),
                    ).fetchall()
                except sqlite3.Error:
                    continue
                for rowid, value in rows:
                    if isinstance(value, str):
                        candidates.append((table_name, int(rowid), value))
    finally:
        connection.close()
    return candidates


def import_codex_history(
    db_path: str | Path,
    *,
    now: datetime | None = None,
    codex_home: Path | None = None,
    skill_roots: list[Path] | None = None,
) -> CodexImportResult:
    scanned_at = _to_utc(now)
    database_path = initialize_database(db_path)
    home = (codex_home or (Path.home() / ".codex")).expanduser()
    roots = [root.expanduser().resolve() for root in (skill_roots or default_skill_roots())]

    session_files = sorted((home / "sessions").glob("**/*.jsonl"))
    rows_to_insert: list[tuple] = []

    for session_file in session_files:
        for line_no, session_id, payload in _extract_candidates_from_jsonl(session_file):
            skill_path = _extract_skill_path_from_payload(payload)
            if skill_path is None or not _is_inside_roots(skill_path, roots):
                continue
            occurred_at = (
                _safe_parse_dt(payload.get("occurred_at"))
                or _safe_parse_dt(payload.get("timestamp"))
                or _safe_parse_dt(payload.get("time"))
                or scanned_at
            )
            skill_id = skill_path.parent.name
            skill_name = _skill_name_from_file(skill_path)
            raw_event_ref = f"{session_file}:{line_no}"
            rows_to_insert.append(
                (
                    _event_id(
                        session_id=session_id,
                        raw_event_ref=raw_event_ref,
                        skill_id=skill_id,
                    ),
                    _serialize_dt(occurred_at),
                    _serialize_dt(scanned_at),
                    skill_id,
                    skill_name,
                    None,
                    session_id,
                    CODEX_SOURCE,
                    ACTIVATION_REASON,
                    None,
                    None,
                    raw_event_ref,
                )
            )

    for table_name, rowid, text in _extract_from_logs_sqlite(home / "logs_2.sqlite"):
        skill_path = _extract_skill_path(text)
        if skill_path is None or not _is_inside_roots(skill_path, roots):
            continue
        skill_id = skill_path.parent.name
        raw_event_ref = f"{home / 'logs_2.sqlite'}:{table_name}:{rowid}"
        rows_to_insert.append(
            (
                _event_id(
                    session_id=f"logs_2:{table_name}",
                    raw_event_ref=raw_event_ref,
                    skill_id=skill_id,
                ),
                _serialize_dt(scanned_at),
                _serialize_dt(scanned_at),
                skill_id,
                _skill_name_from_file(skill_path),
                None,
                f"logs_2:{table_name}",
                CODEX_SOURCE,
                ACTIVATION_REASON,
                None,
                None,
                raw_event_ref,
            )
        )

    with sqlite3.connect(database_path) as connection:
        before = connection.total_changes
        if rows_to_insert:
            connection.executemany(
                """
                insert or ignore into skill_activation_events (
                    event_id,
                    occurred_at,
                    ingested_at,
                    skill_id,
                    skill_name,
                    skill_version,
                    session_id,
                    source,
                    activation_reason,
                    tool_depth,
                    failure_proxy,
                    raw_event_ref
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows_to_insert,
            )
        inserted = connection.total_changes - before

    return CodexImportResult(sessions_found=len(session_files), imported_events=inserted)
