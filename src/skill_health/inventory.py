from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from pathlib import Path
import sqlite3

from skill_health.storage import initialize_database

SCAN_SOURCE = "local_skill_scan"


@dataclass(frozen=True)
class ScanResult:
    scanned_files: int
    upserted_skills: int


def default_skill_roots() -> list[Path]:
    home = Path.home()
    return [
        home / ".codex" / "skills",
        home / ".codex" / "superpowers" / "skills",
        home / ".codex" / "plugins" / "cache",
        home / ".agents" / "skills",
    ]


def _to_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _serialize_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


def _parse_frontmatter(text: str) -> dict[str, str]:
    stripped = text.lstrip()
    if not stripped.startswith("---"):
        return {}

    lines = stripped.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    frontmatter: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        frontmatter[key] = value
    return frontmatter


def _skill_from_file(skill_file: Path, scanned_at: datetime) -> dict[str, str | None]:
    text = skill_file.read_text(encoding="utf-8")
    frontmatter = _parse_frontmatter(text)

    declared_name = frontmatter.get("name")
    skill_id = declared_name or skill_file.parent.name
    skill_name = declared_name or skill_id
    description = frontmatter.get("description")
    modified_at = datetime.fromtimestamp(skill_file.stat().st_mtime, tz=timezone.utc)

    return {
        "skill_id": skill_id,
        "skill_name": skill_name,
        "description": description,
        "source": SCAN_SOURCE,
        "path": str(skill_file),
        "modified_at": _serialize_dt(modified_at),
        "scanned_at": _serialize_dt(scanned_at),
    }


def scan_skill_roots(
    db_path: str | Path,
    roots: list[Path] | None = None,
    now: datetime | None = None,
) -> ScanResult:
    scanned_at = _to_utc(now)
    database_path = initialize_database(db_path)
    search_roots = roots or default_skill_roots()
    skill_files: list[Path] = []
    seen_paths: set[Path] = set()
    for root in search_roots:
        expanded_root = Path(root).expanduser()
        if not expanded_root.exists():
            continue
        for skill_file in expanded_root.rglob("SKILL.md"):
            resolved = skill_file.resolve()
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            skill_files.append(resolved)

    rows = [_skill_from_file(skill_file, scanned_at) for skill_file in skill_files]
    if not rows:
        return ScanResult(scanned_files=0, upserted_skills=0)

    with sqlite3.connect(database_path) as connection:
        before = connection.total_changes
        connection.executemany(
            """
            insert into skill_inventory (
                skill_id,
                skill_name,
                description,
                source,
                path,
                modified_at,
                scanned_at
            ) values (?, ?, ?, ?, ?, ?, ?)
            on conflict(skill_id) do update set
                skill_name=excluded.skill_name,
                description=excluded.description,
                source=excluded.source,
                path=excluded.path,
                modified_at=excluded.modified_at,
                scanned_at=excluded.scanned_at
            """,
            [
                (
                    row["skill_id"],
                    row["skill_name"],
                    row["description"],
                    row["source"],
                    row["path"],
                    row["modified_at"],
                    row["scanned_at"],
                )
                for row in rows
            ],
        )
        changed = connection.total_changes - before

    return ScanResult(scanned_files=len(skill_files), upserted_skills=changed)
