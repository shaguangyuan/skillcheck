from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from datetime import timezone
import sqlite3
from pathlib import Path


SAMPLE_SOURCE = "sample_data"
DEMO_ANCHOR = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)


def _utc_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _serialize(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def build_demo_events(now: datetime | None = None) -> list[dict[str, object]]:
    current = _utc_now(now)

    def event(
        *,
        event_id: str,
        occurred_at: datetime,
        skill_id: str,
        skill_name: str,
        session_id: str,
        activation_reason: str,
        tool_depth: int,
        failure_proxy: bool,
    ) -> dict[str, object]:
        return {
            "event_id": event_id,
            "occurred_at": occurred_at,
            "ingested_at": current,
            "skill_id": skill_id,
            "skill_name": skill_name,
            "skill_version": "1.0.0",
            "session_id": session_id,
            "source": SAMPLE_SOURCE,
            "activation_reason": activation_reason,
            "tool_depth": tool_depth,
            "failure_proxy": failure_proxy,
            "raw_event_ref": None,
        }

    research_lookup_times = [current - timedelta(hours=2 * offset) for offset in range(5)]
    broad_writer_times = [current - timedelta(days=3 + offset * 4) for offset in range(3)]
    old_formatter_times = [current - timedelta(days=120 + offset * 60) for offset in range(2)]

    events = [
        event(
            event_id=f"research-lookup-{index}",
            occurred_at=occurred_at,
            skill_id="research-lookup",
            skill_name="research-lookup",
            session_id=f"session-research-{index % 2}",
            activation_reason="repeat-use",
            tool_depth=4 + (index % 2),
            failure_proxy=False,
        )
        for index, occurred_at in enumerate(research_lookup_times, start=1)
    ]
    events.extend(
        event(
            event_id=f"broad-writer-{index}",
            occurred_at=occurred_at,
            skill_id="broad-writer",
            skill_name="broad-writer",
            session_id=f"session-writer-{index}",
            activation_reason="drafting",
            tool_depth=1 + (index % 2),
            failure_proxy=index != 1,
        )
        for index, occurred_at in enumerate(broad_writer_times, start=1)
    )
    events.extend(
        event(
            event_id=f"old-formatter-{index}",
            occurred_at=occurred_at,
            skill_id="old-formatter",
            skill_name="old-formatter",
            session_id="session-formatter-0",
            activation_reason="legacy-maintenance",
            tool_depth=0,
            failure_proxy=True,
        )
        for index, occurred_at in enumerate(old_formatter_times, start=1)
    )

    return events


def load_demo_data(db_path: str | Path, now: datetime | None = None) -> int:
    rows = build_demo_events(now=now)
    columns = [
        "event_id",
        "occurred_at",
        "ingested_at",
        "skill_id",
        "skill_name",
        "skill_version",
        "session_id",
        "source",
        "activation_reason",
        "tool_depth",
        "failure_proxy",
        "raw_event_ref",
    ]

    with sqlite3.connect(Path(db_path)) as connection:
        before = connection.total_changes
        connection.executemany(
            f"""
            insert or ignore into skill_activation_events ({", ".join(columns)})
            values ({", ".join(["?"] * len(columns))})
            """,
            [
                tuple(
                    _serialize(value) if isinstance(value, datetime) else value
                    for value in (row[column] for column in columns)
                )
                for row in rows
            ],
        )
        return connection.total_changes - before


def clear_demo_data(db_path: str | Path) -> int:
    with sqlite3.connect(Path(db_path)) as connection:
        cursor = connection.execute(
            "delete from skill_activation_events where source = ?",
            (SAMPLE_SOURCE,),
        )
        return cursor.rowcount
