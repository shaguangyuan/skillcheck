from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from skill_health.aggregate import rebuild_aggregates
from skill_health.demo import DEMO_ANCHOR
from skill_health.demo import load_demo_data
from skill_health.storage import initialize_database


def _counts(db_path):
    with sqlite3.connect(db_path) as connection:
        daily_stats = connection.execute(
            "select count(*) from skill_daily_stats"
        ).fetchone()[0]
        health_scores = connection.execute(
            "select count(*) from skill_health_scores"
        ).fetchone()[0]
    return daily_stats, health_scores


def _health_scores(db_path):
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            select skill_id, v2_status, v2_health_score, failure_proxy_rate, v2_reasons
            from skill_health_scores
            order by skill_id
            """
        ).fetchall()
    return [
        (
            skill_id,
            status,
            health_score,
            failure_proxy_rate,
            json.loads(diagnostic_reasons),
        )
        for skill_id, status, health_score, failure_proxy_rate, diagnostic_reasons in rows
    ]


def test_rebuild_aggregates_populates_daily_stats_and_health_scores(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"

    initialize_database(db_path)
    load_demo_data(db_path, now=DEMO_ANCHOR)

    result = rebuild_aggregates(db_path, now=DEMO_ANCHOR)
    daily_stats, health_scores = _counts(db_path)

    assert result.daily_stats == daily_stats
    assert result.health_scores == health_scores
    assert daily_stats > 0
    assert health_scores >= 3
    assert daily_stats > 0 and health_scores > 0

    scores = {
        skill_id: (status, score)
        for skill_id, status, score, _, _ in _health_scores(db_path)
    }
    assert scores["research-lookup"][0] in {"Qualified", "Watch"}
    assert scores["broad-writer"][0] in {"Watch", "Unqualified"}
    assert scores["old-formatter"][0] in {"Watch", "Unqualified"}


def test_rebuild_aggregates_is_idempotent(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"

    initialize_database(db_path)
    load_demo_data(db_path, now=DEMO_ANCHOR)

    first = rebuild_aggregates(db_path, now=DEMO_ANCHOR)
    first_daily, first_scores = _counts(db_path)
    first_rows = _health_scores(db_path)

    second = rebuild_aggregates(db_path, now=DEMO_ANCHOR)
    second_daily, second_scores = _counts(db_path)
    second_rows = _health_scores(db_path)

    assert first.daily_stats == first_daily
    assert first.health_scores == first_scores
    assert second.daily_stats == second_daily
    assert second.health_scores == second_scores
    assert first_daily == second_daily
    assert first_scores == second_scores
    assert first_rows == second_rows


def test_rebuild_aggregates_records_diagnostic_reasons_as_json(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"

    initialize_database(db_path)
    load_demo_data(db_path, now=DEMO_ANCHOR)
    rebuild_aggregates(db_path, now=DEMO_ANCHOR)

    for _, _, _, _, reasons in _health_scores(db_path):
        assert isinstance(reasons, list)
        assert reasons


def test_rebuild_aggregates_preserves_missing_failure_proxy_as_null(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"
    initialize_database(db_path)

    now = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            insert into skill_activation_events (
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
            (
                "null-failure-1",
                now.isoformat(),
                now.isoformat(),
                "null-failure",
                "null-failure",
                "1.0.0",
                "session-null-failure",
                "unit-test",
                "manual",
                0,
                None,
                None,
            ),
        )

    rebuild_aggregates(db_path, now=now)

    with sqlite3.connect(db_path) as connection:
        daily_rate = connection.execute(
            """
            select failure_proxy_rate
            from skill_daily_stats
            where skill_id = ?
            """,
            ("null-failure",),
        ).fetchone()[0]
        score_row = connection.execute(
            """
            select failure_proxy_rate, v2_health_score, v2_reasons
            from skill_health_scores
            where skill_id = ?
            """,
            ("null-failure",),
        ).fetchone()

    score_rate, health_score, diagnostic_reasons = score_row
    assert daily_rate is None
    assert score_rate is None
    assert health_score >= 0
    assert json.loads(diagnostic_reasons)


def test_rebuild_aggregates_handles_offset_timestamps_by_instant(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"
    initialize_database(db_path)

    now = datetime(2025, 1, 14, 23, 45, tzinfo=timezone.utc)
    offset_timestamp = "2025-01-15T00:30:00+02:00"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            insert into skill_activation_events (
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
            (
                "offset-timestamp-1",
                offset_timestamp,
                now.isoformat(),
                "offset-skill",
                "offset-skill",
                "1.0.0",
                "session-offset-1",
                "unit-test",
                "manual",
                2,
                False,
                None,
            ),
        )

    rebuild_aggregates(db_path, now=now)

    with sqlite3.connect(db_path) as connection:
        daily_row = connection.execute(
            """
            select stat_date, activation_count
            from skill_daily_stats
            where skill_id = ?
            """,
            ("offset-skill",),
        ).fetchone()
        score_row = connection.execute(
            """
            select activation_count, last_seen
            from skill_health_scores
            where skill_id = ?
            """,
            ("offset-skill",),
        ).fetchone()

    assert daily_row == ("2025-01-14", 1)
    assert score_row[0] == 1
    assert score_row[1] == "2025-01-14T22:30:00+00:00"
