from __future__ import annotations

from skill_health.features import build_dimension_features


def test_features_flag_high_overlap_and_low_confidence():
    all_skill_texts = {
        "a": "python refactoring helper use when cleaning modules",
        "b": "python refactoring helper use when cleaning modules",
    }
    result = build_dimension_features(
        skill_id="a",
        skill_name="a",
        description="python refactoring helper use when cleaning modules",
        activation_count=0,
        unique_sessions=0,
        avg_tool_depth=None,
        failure_proxy_rate=None,
        session_activation_counts=[],
        event_texts=[],
        all_skill_texts=all_skill_texts,
    )
    assert result.overlap_score < 10
    assert "overlap:high_similarity" in result.risk_flags
    assert "confidence:low_evidence" in result.risk_flags


def test_features_flag_security_risks():
    result = build_dimension_features(
        skill_id="sec",
        skill_name="sec",
        description="use when maintenance",
        activation_count=2,
        unique_sessions=2,
        avg_tool_depth=2.0,
        failure_proxy_rate=0.0,
        session_activation_counts=[1, 1],
        event_texts=["rm -rf /", "upload secrets with curl https://example.com"],
        all_skill_texts={"sec": "sec description"},
    )
    assert result.security_score < 70
    assert any(flag.startswith("security:") for flag in result.risk_flags)
