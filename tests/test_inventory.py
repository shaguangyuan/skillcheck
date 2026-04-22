from __future__ import annotations

import sqlite3
from pathlib import Path

from skill_health.aggregate import rebuild_aggregates
from skill_health.inventory import default_skill_roots
from skill_health.inventory import scan_skill_roots
from skill_health.storage import initialize_database


def test_scan_skill_roots_records_skill_frontmatter(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"
    skill_dir = tmp_path / "skills" / "frontend-design"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        """---
name: frontend-design
description: Build polished frontend interfaces.
---

# Frontend Design
""",
        encoding="utf-8",
    )

    initialize_database(db_path)
    result = scan_skill_roots(db_path, [tmp_path / "skills"])

    assert result.scanned_files == 1
    assert result.upserted_skills == 1

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            select skill_id, skill_name, description, source, path
            from skill_inventory
            """
        ).fetchone()

    assert row[0] == "frontend-design"
    assert row[1] == "frontend-design"
    assert row[2] == "Build polished frontend interfaces."
    assert row[3] == "local_skill_scan"
    assert row[4] == str(skill_file)


def test_rebuild_aggregates_scores_installed_skill_without_activations(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"
    skill_dir = tmp_path / "skills" / "unused-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: unused-skill
description: Present but not activated.
---
""",
        encoding="utf-8",
    )

    initialize_database(db_path)
    scan_skill_roots(db_path, [tmp_path / "skills"])
    result = rebuild_aggregates(db_path)

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            select skill_id, activation_count, unique_sessions, last_seen, v2_status
            from skill_health_scores
            where skill_id = ?
            """,
            ("unused-skill",),
        ).fetchone()

    assert result.health_scores == 1
    assert row == (
        "unused-skill",
        0,
        0,
        None,
        "Watch",
    )


def test_default_skill_roots_includes_codex_plugin_cache(monkeypatch, tmp_path):
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)

    roots = default_skill_roots()

    assert home / ".codex" / "plugins" / "cache" in roots


def test_scan_skill_roots_discovers_plugin_cache_skills(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"
    plugin_skill_dir = (
        tmp_path
        / ".codex"
        / "plugins"
        / "cache"
        / "plugin-id"
        / "skills"
        / "gh-fix-ci"
    )
    plugin_skill_dir.mkdir(parents=True)
    plugin_skill = plugin_skill_dir / "SKILL.md"
    plugin_skill.write_text(
        "---\nname: github:gh-fix-ci\ndescription: Fix GitHub CI failures.\n---\n",
        encoding="utf-8",
    )

    initialize_database(db_path)
    result = scan_skill_roots(
        db_path,
        [tmp_path / ".codex" / "plugins" / "cache"],
    )

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            select skill_id, path
            from skill_inventory
            where skill_id = ?
            """,
            ("github:gh-fix-ci",),
        ).fetchone()

    assert result.scanned_files == 1
    assert row == ("github:gh-fix-ci", str(plugin_skill))
