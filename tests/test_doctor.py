from __future__ import annotations

from skill_health.aggregate import rebuild_aggregates
from skill_health.demo import DEMO_ANCHOR
from skill_health.demo import load_demo_data
from skill_health.doctor import build_doctor_report
from skill_health.doctor import render_doctor_report
from skill_health.inventory import scan_skill_roots
from skill_health.storage import initialize_database


def test_build_doctor_report_handles_missing_database(tmp_path):
    db_path = tmp_path / "missing.sqlite"
    report = build_doctor_report(db_path, codex_home=tmp_path / ".codex")

    assert report.database_path == str(db_path)
    assert report.installed_skills_found == 0
    assert report.imported_activations == 0
    assert report.sample_data_present is False
    assert report.dashboard_ready is False


def test_build_doctor_report_reflects_local_state(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"
    codex_home = tmp_path / ".codex"
    (codex_home / "sessions").mkdir(parents=True)
    (codex_home / "sessions" / "a.jsonl").write_text("", encoding="utf-8")

    skill_dir = tmp_path / "skills" / "unused-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("name: unused-skill\n", encoding="utf-8")

    initialize_database(db_path)
    scan_skill_roots(db_path, [tmp_path / "skills"])
    load_demo_data(db_path, now=DEMO_ANCHOR)
    rebuild_aggregates(db_path, now=DEMO_ANCHOR)

    report = build_doctor_report(db_path, codex_home=codex_home)
    rendered = render_doctor_report(report)

    assert report.installed_skills_found >= 1
    assert report.codex_sessions_found == 1
    assert report.sample_data_present is True
    assert report.last_aggregate is not None
    assert report.dashboard_ready is True
    assert "Database:" in rendered
    assert "Dashboard ready: yes" in rendered
