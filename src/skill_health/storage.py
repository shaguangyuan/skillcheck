from __future__ import annotations

import sqlite3
from pathlib import Path


CREATE_SCHEMA_SQL = """
create table if not exists skill_inventory (
    skill_id text primary key,
    skill_name text not null,
    description text,
    source text not null,
    path text not null,
    modified_at text,
    scanned_at text not null
);

create table if not exists skill_activation_events (
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

create table if not exists skill_daily_stats (
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

create table if not exists skill_health_scores (
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
    security_score real,
    clarity_score real,
    overlap_score real,
    stability_score real,
    efficiency_score real,
    confidence_score real,
    v2_health_score integer,
    v2_status text,
    v2_reasons json,
    risk_flags json,
    unique(window, skill_id)
);
"""

DAILY_STATS_COLUMNS = [
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
]

HEALTH_SCORE_COLUMNS = [
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
]

LEGACY_HEALTH_SCORE_COLUMNS = [
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
]


def _table_columns(connection: sqlite3.Connection, table_name: str) -> list[tuple]:
    return connection.execute(f"pragma table_info({table_name})").fetchall()


def _migrate_health_scores_nullable_failure_rate(
    connection: sqlite3.Connection,
) -> None:
    columns = _table_columns(connection, "skill_health_scores")
    if not columns:
        return

    column_by_name = {column[1]: column for column in columns}
    failure_proxy_rate = column_by_name.get("failure_proxy_rate")
    if failure_proxy_rate is None or failure_proxy_rate[3] == 0:
        return

    connection.execute("alter table skill_health_scores rename to skill_health_scores_legacy")
    connection.execute(
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
        )
        """
    )
    column_list = ", ".join(LEGACY_HEALTH_SCORE_COLUMNS)
    connection.execute(
        f"""
        insert into skill_health_scores ({column_list})
        select {column_list}
        from skill_health_scores_legacy
        """
    )
    connection.execute("drop table skill_health_scores_legacy")


def _migrate_health_scores_v2_columns(connection: sqlite3.Connection) -> None:
    columns = _table_columns(connection, "skill_health_scores")
    if not columns:
        return

    existing_column_names = {column[1] for column in columns}
    required_v2_columns = {
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
    }
    if required_v2_columns.issubset(existing_column_names):
        return

    connection.execute("alter table skill_health_scores rename to skill_health_scores_legacy_v2")
    connection.execute(
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
            security_score real,
            clarity_score real,
            overlap_score real,
            stability_score real,
            efficiency_score real,
            confidence_score real,
            v2_health_score integer,
            v2_status text,
            v2_reasons json,
            risk_flags json,
            unique(window, skill_id)
        )
        """
    )
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
            last_seen,
            days_since_last_seen,
            avg_tool_depth,
            failure_proxy_rate,
            health_score,
            status,
            diagnostic_reasons,
            security_score,
            clarity_score,
            overlap_score,
            stability_score,
            efficiency_score,
            confidence_score,
            v2_health_score,
            v2_status,
            v2_reasons,
            risk_flags
        )
        select
            score_id,
            calculated_at,
            window,
            window_start,
            window_end,
            skill_id,
            skill_name,
            activation_count,
            unique_sessions,
            last_seen,
            days_since_last_seen,
            avg_tool_depth,
            failure_proxy_rate,
            health_score,
            status,
            diagnostic_reasons,
            50.0,
            50.0,
            50.0,
            50.0,
            50.0,
            30.0,
            health_score,
            status,
            diagnostic_reasons,
            json('[]')
        from skill_health_scores_legacy_v2
        """
    )
    connection.execute("drop table skill_health_scores_legacy_v2")


def _migrate_daily_stats_nullable_failure_rate(connection: sqlite3.Connection) -> None:
    columns = _table_columns(connection, "skill_daily_stats")
    if not columns:
        return

    column_by_name = {column[1]: column for column in columns}
    failure_proxy_rate = column_by_name.get("failure_proxy_rate")
    if failure_proxy_rate is None or failure_proxy_rate[3] == 0:
        return

    connection.execute("alter table skill_daily_stats rename to skill_daily_stats_legacy")
    connection.execute(
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
            failure_proxy_rate real,
            first_seen_at text,
            last_seen_at text,
            updated_at text not null,
            unique(stat_date, skill_id)
        )
        """
    )
    column_list = ", ".join(DAILY_STATS_COLUMNS)
    connection.execute(
        f"""
        insert into skill_daily_stats ({column_list})
        select {column_list}
        from skill_daily_stats_legacy
        """
    )
    connection.execute("drop table skill_daily_stats_legacy")


def initialize_database(db_path: str | Path) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.executescript(CREATE_SCHEMA_SQL)
        _migrate_daily_stats_nullable_failure_rate(connection)
        _migrate_health_scores_nullable_failure_rate(connection)
        _migrate_health_scores_v2_columns(connection)

    return path
