from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class HealthResult:
    health_score: int
    status: str
    diagnostic_reasons: list[str]
    security_score: float
    clarity_score: float
    overlap_score: float
    stability_score: float
    efficiency_score: float
    confidence_score: float
    v2_health_score: int
    v2_status: str
    v2_reasons: list[str]
    risk_flags: list[str]


def classify_health(score: int, severe_flags: list[str], confidence_score: float) -> str:
    if any(flag.startswith("security:") for flag in severe_flags):
        return "Unqualified"
    if confidence_score < 40:
        return "Watch"
    if score >= 70 and not severe_flags:
        return "Qualified"
    if score < 45:
        return "Unqualified"
    return "Watch"


def score_health(
    *,
    security_score: float,
    clarity_score: float,
    overlap_score: float,
    stability_score: float,
    efficiency_score: float,
    confidence_score: float,
    risk_flags: list[str],
    reasons: list[str],
    last_seen: datetime | None = None,
    activation_count: int = 0,
    unique_sessions: int = 0,
    avg_tool_depth: float | None = None,
    failure_proxy_rate: float | None = None,
    window_end: datetime | None = None,
) -> HealthResult:
    _ = window_end  # retained for backward-call compatibility
    weighted_score = (
        security_score * 0.2
        + clarity_score * 0.15
        + overlap_score * 0.15
        + stability_score * 0.15
        + efficiency_score * 0.15
        + confidence_score * 0.2
    )
    v2_health_score = int(max(0.0, min(100.0, round(weighted_score))))

    severe_flags = list(risk_flags)
    if failure_proxy_rate is not None and failure_proxy_rate > 0.6:
        severe_flags.append("failure_proxy:high")
    if activation_count == 0 and confidence_score < 50:
        severe_flags.append("confidence:no_activation_window")
    if avg_tool_depth is not None and avg_tool_depth >= 8:
        severe_flags.append("efficiency:very_deep_toolchain")

    v2_status = classify_health(v2_health_score, severe_flags, confidence_score)
    diagnostic_reasons = list(reasons)
    if last_seen is None:
        diagnostic_reasons.append("recency:no_last_seen")
    if unique_sessions <= 1:
        diagnostic_reasons.append("stability:limited_session_coverage")

    return HealthResult(
        health_score=v2_health_score,
        status=v2_status,
        diagnostic_reasons=diagnostic_reasons,
        security_score=security_score,
        clarity_score=clarity_score,
        overlap_score=overlap_score,
        stability_score=stability_score,
        efficiency_score=efficiency_score,
        confidence_score=confidence_score,
        v2_health_score=v2_health_score,
        v2_status=v2_status,
        v2_reasons=diagnostic_reasons,
        risk_flags=severe_flags,
    )
