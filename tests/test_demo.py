from __future__ import annotations

import sqlite3
from datetime import timedelta

from skill_health.demo import DEMO_ANCHOR
from skill_health.demo import clear_demo_data
from skill_health.demo import build_demo_events
from skill_health.demo import load_demo_data
from skill_health.storage import initialize_database


def _event_rows(db_path):
    with sqlite3.connect(db_path) as connection:
        return connection.execute(
            """
            select skill_id, skill_name, occurred_at, tool_depth, failure_proxy
            from skill_activation_events
            order by skill_id, occurred_at
            """
        ).fetchall()


def _event_count(db_path):
    with sqlite3.connect(db_path) as connection:
        return connection.execute(
            "select count(*) from skill_activation_events"
        ).fetchone()[0]


def _distinct_skill_ids(db_path):
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "select distinct skill_id from skill_activation_events order by skill_id"
        ).fetchall()
    return [row[0] for row in rows]


def test_build_demo_events_uses_fixed_default_anchor():
    rows = build_demo_events(now=DEMO_ANCHOR)

    assert rows[0]["occurred_at"] <= DEMO_ANCHOR
    assert rows[0]["ingested_at"] == DEMO_ANCHOR
    assert rows[0]["occurred_at"].tzinfo is not None
    assert rows[0]["ingested_at"].tzinfo is not None


def test_load_and_clear_demo_data(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"
    initialize_database(db_path)

    inserted = load_demo_data(db_path, now=DEMO_ANCHOR)
    first_rows = _event_rows(db_path)

    assert inserted > 0
    assert _event_count(db_path) == inserted
    assert _distinct_skill_ids(db_path) == [
        "broad-writer",
        "old-formatter",
        "research-lookup",
    ]
    assert inserted == len(first_rows)

    research_rows = [row for row in first_rows if row[0] == "research-lookup"]
    broad_rows = [row for row in first_rows if row[0] == "broad-writer"]
    old_rows = [row for row in first_rows if row[0] == "old-formatter"]

    assert len(research_rows) == 5
    assert all(row[4] == 0 for row in research_rows)
    assert max(row[3] for row in research_rows) >= 4
    assert max(row[2] for row in research_rows) == DEMO_ANCHOR.isoformat()
    assert min(row[2] for row in research_rows) >= (
        DEMO_ANCHOR - timedelta(hours=8)
    ).isoformat()
    assert len(broad_rows) == 3
    assert any(row[4] == 1 for row in broad_rows)
    assert max(row[3] for row in broad_rows) <= 2
    assert len(old_rows) == 2
    assert all(row[3] == 0 for row in old_rows)
    assert all(row[4] == 1 for row in old_rows)
    assert max(row[2] for row in old_rows) <= (
        DEMO_ANCHOR - timedelta(days=120)
    ).isoformat()

    second_inserted = load_demo_data(db_path, now=DEMO_ANCHOR)

    assert second_inserted == 0
    assert _event_count(db_path) == inserted

    removed = clear_demo_data(db_path)
    second_removed = clear_demo_data(db_path)

    assert removed > 0
    assert second_removed == 0
    assert _event_count(db_path) == 0
