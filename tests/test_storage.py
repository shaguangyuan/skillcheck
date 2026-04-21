import sqlite3

from skill_health.storage import initialize_database


EXPECTED_TABLE_COLUMNS = {
    "skill_inventory": [
        "skill_id",
        "skill_name",
        "description",
        "source",
        "path",
        "modified_at",
        "scanned_at",
    ],
    "skill_activation_events": [
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
    ],
    "skill_daily_stats": [
        "stat_id",
        "stat_date",
        "skill_id",
        "skill_name",
        "activation_count",
        "unique_sessions",
        "avg_tool_depth",
        "failure_proxy_count",
        "failure_proxy_rate",
        "first_seen_at",
        "last_seen_at",
        "updated_at",
    ],
    "skill_health_scores": [
        "score_id",
        "calculated_at",
        "window",
        "window_start",
        "window_end",
        "skill_id",
        "skill_name",
        "activation_count",
        "unique_sessions",
        "last_seen",
        "days_since_last_seen",
        "avg_tool_depth",
        "failure_proxy_rate",
        "health_score",
        "status",
        "diagnostic_reasons",
        "security_score",
        "clarity_score",
        "overlap_score",
        "stability_score",
        "efficiency_score",
        "confidence_score",
        "v2_health_score",
        "v2_status",
        "v2_reasons",
        "risk_flags",
    ],
}


def _table_names(db_path):
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "select name from sqlite_master where type='table' order by name"
        ).fetchall()
    return [row[0] for row in rows]


def _table_columns(db_path, table_name):
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(f"pragma table_info({table_name})").fetchall()
    return [row[1] for row in rows]


def _table_column_types(db_path, table_name):
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(f"pragma table_info({table_name})").fetchall()
    return [row[2].lower() for row in rows]


def _table_indexes(db_path, table_name):
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(f"pragma index_list({table_name})").fetchall()
    return rows


def _index_columns(db_path, index_name):
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(f"pragma index_info({index_name})").fetchall()
    return [row[2] for row in rows]


def test_initialize_database_creates_expected_tables(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"

    initialize_database(db_path)

    assert _table_names(db_path) == [
        "skill_activation_events",
        "skill_daily_stats",
        "skill_health_scores",
        "skill_inventory",
    ]


def test_initialize_database_is_idempotent(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"

    initialize_database(db_path)
    initialize_database(db_path)

    assert _table_names(db_path) == [
        "skill_activation_events",
        "skill_daily_stats",
        "skill_health_scores",
        "skill_inventory",
    ]


def test_initialize_database_creates_expected_columns_and_constraints(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"

    initialize_database(db_path)

    for table_name, expected_columns in EXPECTED_TABLE_COLUMNS.items():
        assert _table_columns(db_path, table_name) == expected_columns

    daily_indexes = _table_indexes(db_path, "skill_daily_stats")
    score_indexes = _table_indexes(db_path, "skill_health_scores")

    daily_unique_indexes = [
        index[1] for index in daily_indexes if index[2] == 1 and index[3] == "u"
    ]
    score_unique_indexes = [
        index[1] for index in score_indexes if index[2] == 1 and index[3] == "u"
    ]

    assert any(
        _index_columns(db_path, index_name) == ["stat_date", "skill_id"]
        for index_name in daily_unique_indexes
    )
    assert any(
        _index_columns(db_path, index_name) == ["window", "skill_id"]
        for index_name in score_unique_indexes
    )


def test_initialize_database_uses_expected_declared_types(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"

    initialize_database(db_path)

    assert _table_column_types(db_path, "skill_activation_events") == [
        "text",
        "text",
        "text",
        "text",
        "text",
        "text",
        "text",
        "text",
        "text",
        "integer",
        "boolean",
        "text",
    ]
    assert _table_column_types(db_path, "skill_health_scores")[-1] == "json"


def test_initialize_database_migrates_legacy_daily_stats_nullable_failure_rate(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"

    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            create table skill_daily_stats (
                stat_id text primary key,
                stat_date text not null,
                skill_id text not null,
                skill_name text not null,
                activation_count integer not null,
                unique_sessions integer not null,
                avg_tool_depth real,
                failure_proxy_count integer not null,
                failure_proxy_rate real not null,
                first_seen_at text,
                last_seen_at text,
                updated_at text not null,
                unique(stat_date, skill_id)
            );
            """
        )

    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        daily_columns = {
            row[1]: row for row in connection.execute("pragma table_info(skill_daily_stats)")
        }
        connection.execute(
            """
            insert into skill_daily_stats (
                stat_id,
                stat_date,
                skill_id,
                skill_name,
                activation_count,
                unique_sessions,
                failure_proxy_count,
                failure_proxy_rate,
                updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-daily-null-check",
                "2025-01-01",
                "legacy-skill",
                "legacy-skill",
                0,
                0,
                0,
                None,
                "2025-01-01T00:00:00+00:00",
            ),
        )

    assert daily_columns["failure_proxy_rate"][3] == 0


def test_initialize_database_migrates_legacy_health_scores_nullable_failure_rate(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"

    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            create table skill_activation_events (
                event_id text primary key,
                occurred_at text not null,
                ingested_at text not null,
                skill_id text not null,
                skill_name text not null,
                skill_version text,
                session_id text,
                source text,
                activation_reason text,
                tool_depth integer,
                failure_proxy boolean,
                raw_event_ref text
            );

            create table skill_daily_stats (
                stat_id text primary key,
                stat_date text not null,
                skill_id text not null,
                skill_name text not null,
                activation_count integer not null,
                unique_sessions integer not null,
                avg_tool_depth real,
                failure_proxy_count integer not null,
                failure_proxy_rate real,
                first_seen_at text,
                last_seen_at text,
                updated_at text not null,
                unique(stat_date, skill_id)
            );

            create table skill_health_scores (
                score_id text primary key,
                calculated_at text not null,
                window text not null,
                window_start text not null,
                window_end text not null,
                skill_id text not null,
                skill_name text not null,
                activation_count integer not null,
                unique_sessions integer not null,
                last_seen text,
                days_since_last_seen integer,
                avg_tool_depth real,
                failure_proxy_rate real not null,
                health_score integer not null,
                status text not null,
                diagnostic_reasons text not null,
                unique(window, skill_id)
            );
            """
        )

    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        health_columns = {
            row[1]: row for row in connection.execute(
                "pragma table_info(skill_health_scores)"
            )
        }
        connection.execute(
            """
            insert into skill_health_scores (
                score_id,
                calculated_at,
                window,
                window_start,
                window_end,
                skill_id,
                skill_name,
                activation_count,
                unique_sessions,
                failure_proxy_rate,
                health_score,
                status,
                diagnostic_reasons
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-null-check",
                "2025-01-01T00:00:00+00:00",
                "30d",
                "2024-12-02T00:00:00+00:00",
                "2025-01-01T00:00:00+00:00",
                "legacy-skill",
                "legacy-skill",
                0,
                0,
                None,
                16,
                "Candidate to Merge/Retire",
                "[]",
            ),
        )

    assert health_columns["failure_proxy_rate"][3] == 0


def test_initialize_database_migrates_legacy_health_scores_to_v2_columns(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            create table skill_health_scores (
                score_id text primary key,
                calculated_at text not null,
                window text not null,
                window_start text not null,
                window_end text not null,
                skill_id text not null,
                skill_name text not null,
                activation_count integer not null,
                unique_sessions integer not null,
                last_seen text,
                days_since_last_seen integer,
                avg_tool_depth real,
                failure_proxy_rate real,
                health_score integer not null,
                status text not null,
                diagnostic_reasons json not null,
                unique(window, skill_id)
            );
            insert into skill_health_scores (
                score_id, calculated_at, window, window_start, window_end, skill_id, skill_name,
                activation_count, unique_sessions, health_score, status, diagnostic_reasons
            ) values (
                'legacy-v2', '2025-01-01T00:00:00+00:00', '30d', '2024-12-01T00:00:00+00:00',
                '2025-01-01T00:00:00+00:00', 's1', 's1', 1, 1, 61, 'Needs Review', '[]'
            );
            """
        )

    initialize_database(db_path)
    columns = _table_columns(db_path, "skill_health_scores")
    assert "security_score" in columns
    assert "v2_health_score" in columns

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "select health_score, v2_health_score, status, v2_status from skill_health_scores where score_id = ?",
            ("legacy-v2",),
        ).fetchone()
    assert row == (61, 61, "Needs Review", "Needs Review")
