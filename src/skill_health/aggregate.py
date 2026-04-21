from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path

from skill_health.features import build_dimension_features
from skill_health.scoring import score_health
from skill_health.storage import initialize_database


@dataclass(frozen=True)
class AggregateResult:
    daily_stats: int
    health_scores: int


def _to_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _serialize_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


def rebuild_aggregates(
    db_path: str | Path,
    now: datetime | None = None,
) -> AggregateResult:
    path = initialize_database(db_path)
    current = _to_utc(now)
    window_start = current - timedelta(days=30)

    with sqlite3.connect(path) as connection:
        inventory_rows = connection.execute(
            """
            select skill_id, skill_name, coalesce(description, '')
            from skill_inventory
            order by skill_id
            """
        ).fetchall()
        raw_rows = connection.execute(
            """
            select
                event_id,
                occurred_at,
                ingested_at,
                skill_id,
                skill_name,
                session_id,
                tool_depth,
                failure_proxy,
                activation_reason,
                raw_event_ref
            from skill_activation_events
            order by occurred_at, event_id
            """
        ).fetchall()

        events: list[dict[str, object]] = []
        for (
            event_id,
            occurred_at,
            ingested_at,
            skill_id,
            skill_name,
            session_id,
            tool_depth,
            failure_proxy,
            activation_reason,
            raw_event_ref,
        ) in raw_rows:
            occurred = _parse_dt(occurred_at)
            ingested = _parse_dt(ingested_at)
            if occurred is None or ingested is None:
                continue
            events.append(
                {
                    "event_id": event_id,
                    "occurred_at": occurred,
                    "ingested_at": ingested,
                    "skill_id": skill_id,
                    "skill_name": skill_name,
                    "session_id": session_id,
                    "tool_depth": tool_depth,
                    "failure_proxy": failure_proxy,
                    "activation_reason": activation_reason,
                    "raw_event_ref": raw_event_ref,
                }
            )

        connection.execute("delete from skill_daily_stats")
        connection.execute("delete from skill_health_scores")

        daily_groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
        skill_groups: dict[str, list[dict[str, object]]] = defaultdict(list)
        skill_names: dict[str, str] = {
            skill_id: skill_name for skill_id, skill_name, _ in inventory_rows
        }
        skill_descriptions: dict[str, str] = {
            skill_id: description for skill_id, _, description in inventory_rows
        }

        for event in events:
            occurred = event["occurred_at"]  # type: ignore[assignment]
            skill_id = event["skill_id"]  # type: ignore[assignment]
            day_key = occurred.astimezone(timezone.utc).date().isoformat()
            daily_groups[(day_key, skill_id)].append(event)
            skill_groups[skill_id].append(event)
            skill_names[skill_id] = str(event["skill_name"])
            skill_descriptions.setdefault(skill_id, "")

        for (stat_date, skill_id), group in sorted(daily_groups.items()):
            skill_name = group[-1]["skill_name"]  # type: ignore[index]
            activation_count = len(group)
            unique_sessions = len(
                {
                    event["session_id"]
                    for event in group
                    if event["session_id"]
                }
            )
            depths = [
                event["tool_depth"]
                for event in group
                if event["tool_depth"] is not None
            ]
            non_null_failure_flags = [
                bool(event["failure_proxy"])
                for event in group
                if event["failure_proxy"] is not None
            ]
            failure_proxy_count = sum(non_null_failure_flags)
            failure_proxy_rate = (
                failure_proxy_count / len(non_null_failure_flags)
                if non_null_failure_flags
                else None
            )
            first_seen_at = min(
                event["occurred_at"] for event in group
            ).astimezone(timezone.utc)
            last_seen_at = max(
                event["occurred_at"] for event in group
            ).astimezone(timezone.utc)

            connection.execute(
                """
                insert into skill_daily_stats (
                    stat_id,
                    stat_date,
                    skill_id,
                    skill_name,
                    activation_count,
                    unique_sessions,
                    avg_tool_depth,
                    failure_proxy_count,
                    failure_proxy_rate,
                    first_seen_at,
                    last_seen_at,
                    updated_at
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{stat_date}:{skill_id}",
                    stat_date,
                    skill_id,
                    skill_name,
                    activation_count,
                    unique_sessions,
                    (sum(depths) / len(depths)) if depths else None,
                    failure_proxy_count,
                    failure_proxy_rate,
                    _serialize_dt(first_seen_at),
                    _serialize_dt(last_seen_at),
                    _serialize_dt(current),
                ),
            )

        all_skill_ids = set(skill_names) | set(skill_groups)
        all_skill_texts = {
            skill_id: f"{skill_names.get(skill_id, skill_id)}\n{skill_descriptions.get(skill_id, '')}"
            for skill_id in all_skill_ids
        }
        for skill_id in sorted(all_skill_ids):
            group = skill_groups.get(skill_id, [])
            skill_name = skill_names.get(skill_id, skill_id)
            skill_description = skill_descriptions.get(skill_id, "")
            window_events = [
                event
                for event in group
                if window_start <= event["occurred_at"] <= current
            ]
            last_seen_at = (
                max(event["occurred_at"] for event in group).astimezone(timezone.utc)
                if group
                else None
            )
            activation_count = len(window_events)
            unique_sessions = len(
                {
                    event["session_id"]
                    for event in window_events
                    if event["session_id"]
                }
            )
            depths = [
                event["tool_depth"]
                for event in window_events
                if event["tool_depth"] is not None
            ]
            non_null_failure_flags = [
                bool(event["failure_proxy"])
                for event in window_events
                if event["failure_proxy"] is not None
            ]
            avg_tool_depth = (sum(depths) / len(depths)) if depths else None
            failure_proxy_rate = (
                sum(non_null_failure_flags) / len(non_null_failure_flags)
                if non_null_failure_flags
                else None
            )
            session_counts: dict[str, int] = defaultdict(int)
            for event in window_events:
                session_id = event["session_id"]
                if session_id:
                    session_counts[str(session_id)] += 1
            event_texts = [
                f"{event['activation_reason'] or ''}\n{event['raw_event_ref'] or ''}"
                for event in window_events
            ]
            features = build_dimension_features(
                skill_id=skill_id,
                skill_name=skill_name,
                description=skill_description,
                activation_count=activation_count,
                unique_sessions=unique_sessions,
                avg_tool_depth=avg_tool_depth,
                failure_proxy_rate=failure_proxy_rate,
                session_activation_counts=list(session_counts.values()),
                event_texts=event_texts,
                all_skill_texts=all_skill_texts,
            )
            result = score_health(
                security_score=features.security_score,
                clarity_score=features.clarity_score,
                overlap_score=features.overlap_score,
                stability_score=features.stability_score,
                efficiency_score=features.efficiency_score,
                confidence_score=features.confidence_score,
                risk_flags=features.risk_flags,
                reasons=features.reasons,
                last_seen=last_seen_at,
                activation_count=activation_count,
                unique_sessions=unique_sessions,
                avg_tool_depth=avg_tool_depth,
                failure_proxy_rate=failure_proxy_rate,
                window_end=current,
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
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"30d:{skill_id}",
                    _serialize_dt(current),
                    "30d",
                    _serialize_dt(window_start),
                    _serialize_dt(current),
                    skill_id,
                    skill_name,
                    activation_count,
                    unique_sessions,
                    _serialize_dt(last_seen_at),
                    max(0, (current - last_seen_at).days) if last_seen_at else None,
                    avg_tool_depth,
                    failure_proxy_rate,
                    result.health_score,
                    result.status,
                    json.dumps(result.diagnostic_reasons),
                    result.security_score,
                    result.clarity_score,
                    result.overlap_score,
                    result.stability_score,
                    result.efficiency_score,
                    result.confidence_score,
                    result.v2_health_score,
                    result.v2_status,
                    json.dumps(result.v2_reasons),
                    json.dumps(result.risk_flags),
                ),
            )

    return AggregateResult(
        daily_stats=len(daily_groups),
        health_scores=len(all_skill_ids),
    )
