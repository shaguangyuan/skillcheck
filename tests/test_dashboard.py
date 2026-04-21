from __future__ import annotations

from skill_health.aggregate import rebuild_aggregates
from skill_health.dashboard import build_overview_payload
from skill_health.dashboard import render_overview_html
from skill_health.demo import DEMO_ANCHOR
from skill_health.demo import load_demo_data
from skill_health.storage import initialize_database


def test_build_overview_payload_summarizes_demo_database(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"

    initialize_database(db_path)
    load_demo_data(db_path, now=DEMO_ANCHOR)
    rebuild_aggregates(db_path, now=DEMO_ANCHOR)

    payload = build_overview_payload(db_path)

    assert payload["window"] == "30d"
    assert payload["total_skills"] >= 2
    assert payload["status_counts"]["Qualified"] >= 1
    assert any(
        row["skill_id"] == "research-lookup" for row in payload["top_skills"]
    )


def test_build_overview_payload_marks_sample_data(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"

    initialize_database(db_path)
    load_demo_data(db_path, now=DEMO_ANCHOR)
    rebuild_aggregates(db_path, now=DEMO_ANCHOR)

    payload = build_overview_payload(db_path)

    assert payload["sample_data"] is True


def test_render_overview_html_includes_title_and_skill_name(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"

    initialize_database(db_path)
    load_demo_data(db_path, now=DEMO_ANCHOR)
    rebuild_aggregates(db_path, now=DEMO_ANCHOR)
    payload = build_overview_payload(db_path)

    html = render_overview_html(payload)

    assert "Skill Health Dashboard" in html
    assert "research-lookup" in html


def test_render_overview_html_uses_safe_status_classes(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"

    initialize_database(db_path)
    load_demo_data(db_path, now=DEMO_ANCHOR)
    rebuild_aggregates(db_path, now=DEMO_ANCHOR)
    payload = build_overview_payload(db_path)

    html = render_overview_html(payload)

    assert 'class="status status-healthy"' in html
    assert 'class="panel status-candidate"' in html
    assert "Unqualified" in html
    assert 'class="status-Unqualified"' not in html


def test_quickstart_demo_data_stays_fresh_with_current_clock(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"

    initialize_database(db_path)
    load_demo_data(db_path)
    rebuild_aggregates(db_path)

    payload = build_overview_payload(db_path)

    assert any(
        row["skill_id"] == "research-lookup" and row["activation_count"] > 0
        for row in payload["top_skills"]
    )
    assert any(count > 0 for count in payload["status_counts"].values())
    assert payload["status_counts"]["Qualified"] > 0
    assert payload["status_counts"]["Unqualified"] < payload["total_skills"]
