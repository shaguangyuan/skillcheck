from __future__ import annotations

from skill_health.aggregate import rebuild_aggregates
from skill_health.demo import DEMO_ANCHOR
from skill_health.demo import load_demo_data
from skill_health.inventory import scan_skill_roots
from skill_health.storage import initialize_database
from skill_health.summary import build_summary_report
from skill_health.summary import render_summary_report
from skill_health.summary import render_summary_report_json
from skill_health.summary import summary_report_to_dict


def test_build_summary_report_with_real_rows(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"
    skills_dir = tmp_path / "skills" / "unused-skill"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text(
        """---
name: unused-skill
description: Present but not activated.
---
""",
        encoding="utf-8",
    )

    initialize_database(db_path)
    scan_skill_roots(db_path, [tmp_path / "skills"])
    load_demo_data(db_path, now=DEMO_ANCHOR)
    rebuild_aggregates(db_path, now=DEMO_ANCHOR)

    report = build_summary_report(db_path)
    text = render_summary_report(report)

    assert report.installed_skills >= 1
    assert report.scored_skills >= 1
    assert report.total_activations_30d >= 1
    assert report.top_skills
    assert report.action_hints
    assert "Installed skills:" in text
    assert "Status breakdown:" in text
    assert "Skills (30d):" in text
    assert "Action hints:" in text


def test_build_summary_report_handles_empty_database(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"
    initialize_database(db_path)

    report = build_summary_report(db_path)
    text = render_summary_report(report)

    assert report.installed_skills == 0
    assert report.scored_skills == 0
    assert report.total_activations_30d == 0
    assert report.top_skills == []
    assert report.action_hints
    assert "Installed skills: 0" in text


def test_summary_report_to_dict_has_stable_structure(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"
    initialize_database(db_path)
    report = build_summary_report(db_path)
    data = summary_report_to_dict(report)

    assert data["version"] == "v2"
    assert data["window"] == "30d"
    assert "totals" in data
    assert "average_dimensions" in data
    assert "status_breakdown" in data
    assert "skills" in data
    assert "top_skills" in data
    assert data["top_skills_deprecated"] is True
    assert "action_hints" in data


def test_render_summary_report_json_outputs_json_object(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"
    initialize_database(db_path)
    report = build_summary_report(db_path)
    text = render_summary_report_json(report)

    assert text.strip().startswith("{")
    assert '"version": "v2"' in text


def test_build_summary_report_respects_explicit_top_limit(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"
    skills_dir = tmp_path / "skills"
    for idx in range(12):
        skill_dir = skills_dir / f"skill-{idx}"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: skill-{idx}\ndescription: test skill {idx}\n---\n",
            encoding="utf-8",
        )

    initialize_database(db_path)
    scan_skill_roots(db_path, [skills_dir])
    rebuild_aggregates(db_path, now=DEMO_ANCHOR)

    top10 = build_summary_report(db_path, top_limit=10)
    all_rows = build_summary_report(db_path, top_limit=None)

    assert len(top10.top_skills) == 10
    assert len(all_rows.top_skills) >= 12
