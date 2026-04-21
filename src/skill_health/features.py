from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
import re


TOKEN_RE = re.compile(r"[a-zA-Z0-9_]{3,}")
BOUNDARY_HINTS = ("use when", "do not use", "avoid when", "not for", "适用", "不适用")
SECURITY_PATTERNS = (
    re.compile(r"rm\s+-rf", re.I),
    re.compile(r"del\s+/f", re.I),
    re.compile(r"format\s+[a-z]:", re.I),
    re.compile(r"curl\s+.*https?://", re.I),
    re.compile(r"invoke-webrequest", re.I),
    re.compile(r"api[_-]?key|token|secret|password", re.I),
)


@dataclass(frozen=True)
class DimensionFeatures:
    security_score: float
    clarity_score: float
    overlap_score: float
    stability_score: float
    efficiency_score: float
    confidence_score: float
    risk_flags: list[str]
    reasons: list[str]


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _build_security(description: str, event_texts: list[str]) -> tuple[float, list[str]]:
    joined = "\n".join([description] + event_texts)
    flags: list[str] = []
    score = 100.0

    for pattern in SECURITY_PATTERNS:
        if pattern.search(joined):
            flags.append(f"security:{pattern.pattern}")
            score -= 15.0
    if re.search(r"(?:\.\./|[a-zA-Z]:\\windows\\|/etc/)", joined, re.I):
        flags.append("security:path_boundary_risk")
        score -= 20.0
    if re.search(r"(upload|send to|exfiltrate|pastebin|webhook)", joined, re.I):
        flags.append("security:external_transfer_hint")
        score -= 15.0

    return max(0.0, min(100.0, score)), flags


def _build_clarity(description: str) -> float:
    text = (description or "").strip()
    if not text:
        return 20.0
    score = 45.0
    if len(text) >= 40:
        score += 20.0
    if any(hint in text.lower() for hint in BOUNDARY_HINTS):
        score += 25.0
    if ":" in text or ";" in text:
        score += 10.0
    return max(0.0, min(100.0, score))


def _build_overlap(skill_text: str, all_skill_texts: dict[str, str], skill_id: str) -> tuple[float, float]:
    current_tokens = _tokenize(skill_text)
    max_similarity = 0.0
    for other_id, other_text in all_skill_texts.items():
        if other_id == skill_id:
            continue
        similarity = _jaccard_similarity(current_tokens, _tokenize(other_text))
        if similarity > max_similarity:
            max_similarity = similarity
    score = max(0.0, min(100.0, (1 - max_similarity) * 100.0))
    return score, max_similarity


def _build_stability(session_activation_counts: list[int], failure_proxy_rate: float | None) -> float:
    if len(session_activation_counts) <= 1:
        base = 55.0
    else:
        mean = sum(session_activation_counts) / len(session_activation_counts)
        variance = sum((value - mean) ** 2 for value in session_activation_counts) / len(
            session_activation_counts
        )
        std = sqrt(variance)
        cv = std / mean if mean > 0 else 1.0
        base = max(0.0, min(100.0, 100.0 - cv * 60.0))
    if failure_proxy_rate is not None:
        base -= failure_proxy_rate * 25.0
    return max(0.0, min(100.0, base))


def _build_efficiency(avg_tool_depth: float | None, activation_count: int) -> float:
    if activation_count == 0:
        return 25.0
    if avg_tool_depth is None:
        return 50.0
    if avg_tool_depth < 1:
        return 35.0
    if avg_tool_depth <= 4:
        return 90.0
    if avg_tool_depth <= 7:
        return 65.0
    return 40.0


def _build_confidence(
    *,
    activation_count: int,
    unique_sessions: int,
    has_failure_signal: bool,
    has_depth_signal: bool,
) -> float:
    score = 20.0
    score += min(40.0, activation_count * 4.0)
    score += min(20.0, unique_sessions * 5.0)
    if has_failure_signal:
        score += 10.0
    if has_depth_signal:
        score += 10.0
    return max(0.0, min(100.0, score))


def build_dimension_features(
    *,
    skill_id: str,
    skill_name: str,
    description: str,
    activation_count: int,
    unique_sessions: int,
    avg_tool_depth: float | None,
    failure_proxy_rate: float | None,
    session_activation_counts: list[int],
    event_texts: list[str],
    all_skill_texts: dict[str, str],
) -> DimensionFeatures:
    security_score, security_flags = _build_security(description, event_texts)
    clarity_score = _build_clarity(description)
    combined_text = f"{skill_name}\n{description}"
    overlap_score, max_similarity = _build_overlap(combined_text, all_skill_texts, skill_id)
    stability_score = _build_stability(session_activation_counts, failure_proxy_rate)
    efficiency_score = _build_efficiency(avg_tool_depth, activation_count)
    confidence_score = _build_confidence(
        activation_count=activation_count,
        unique_sessions=unique_sessions,
        has_failure_signal=failure_proxy_rate is not None,
        has_depth_signal=avg_tool_depth is not None,
    )

    reasons = [
        f"security={security_score:.1f}",
        f"clarity={clarity_score:.1f}",
        f"overlap={overlap_score:.1f} (max_similarity={max_similarity:.2f})",
        f"stability={stability_score:.1f}",
        f"efficiency={efficiency_score:.1f}",
        f"confidence={confidence_score:.1f}",
    ]
    flags = list(security_flags)
    if max_similarity >= 0.75:
        flags.append("overlap:high_similarity")
    if confidence_score < 40:
        flags.append("confidence:low_evidence")

    return DimensionFeatures(
        security_score=security_score,
        clarity_score=clarity_score,
        overlap_score=overlap_score,
        stability_score=stability_score,
        efficiency_score=efficiency_score,
        confidence_score=confidence_score,
        risk_flags=flags,
        reasons=reasons,
    )
