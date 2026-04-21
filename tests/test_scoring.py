from __future__ import annotations

from skill_health.scoring import classify_health
from skill_health.scoring import score_health


def test_high_dimension_scores_classify_as_qualified():
    result = score_health(
        security_score=90,
        clarity_score=80,
        overlap_score=85,
        stability_score=78,
        efficiency_score=82,
        confidence_score=90,
        risk_flags=[],
        reasons=["ok"],
    )
    assert result.v2_health_score >= 80
    assert result.v2_status == "Qualified"


def test_low_confidence_forces_watch():
    result = score_health(
        security_score=95,
        clarity_score=80,
        overlap_score=85,
        stability_score=75,
        efficiency_score=70,
        confidence_score=20,
        risk_flags=[],
        reasons=["low confidence"],
    )
    assert result.v2_status == "Watch"


def test_security_flags_can_force_unqualified():
    result = score_health(
        security_score=20,
        clarity_score=70,
        overlap_score=60,
        stability_score=60,
        efficiency_score=60,
        confidence_score=75,
        risk_flags=["security:rm\\s+-rf"],
        reasons=["security risk"],
    )
    assert result.v2_status == "Unqualified"


def test_classify_health_thresholds():
    assert classify_health(80, [], 80) == "Qualified"
    assert classify_health(65, [], 20) == "Watch"
    assert classify_health(35, [], 80) == "Unqualified"
