from __future__ import annotations

import sqlite3
from pathlib import Path

from skill_health.importers.codex import import_codex_history
from skill_health.storage import initialize_database


def test_import_codex_history_extracts_skill_file_loads(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"
    codex_home = tmp_path / ".codex"
    session_dir = codex_home / "sessions"
    session_dir.mkdir(parents=True)

    skill_root = codex_home / "skills"
    skill_dir = skill_root / "frontend-design"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        """---
name: frontend-design
description: Build polished interfaces.
---
""",
        encoding="utf-8",
    )

    (session_dir / "session-1.jsonl").write_text(
        "\n".join(
            [
                '{"timestamp":"2026-04-21T12:00:00+00:00","tool":"shell","command":"Get-Content \\"'
                + str(skill_file).replace("\\", "\\\\")
                + '\\""}',
                '{"timestamp":"2026-04-21T12:01:00+00:00","tool":"shell","command":"echo ignored"}',
            ]
        ),
        encoding="utf-8",
    )

    initialize_database(db_path)
    result = import_codex_history(
        db_path,
        codex_home=codex_home,
        skill_roots=[skill_root],
    )

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            select skill_id, skill_name, source, activation_reason, raw_event_ref
            from skill_activation_events
            """
        ).fetchall()

    assert result.sessions_found == 1
    assert result.imported_events == 1
    assert len(rows) == 1
    assert rows[0][0] == "frontend-design"
    assert rows[0][1] == "frontend-design"
    assert rows[0][2] == "codex_session_skill_file"
    assert rows[0][3] == "skill_file_loaded"
    assert str(session_dir / "session-1.jsonl") in rows[0][4]


def test_import_codex_history_is_idempotent(tmp_path):
    db_path = tmp_path / "skill-health.sqlite"
    codex_home = tmp_path / ".codex"
    session_dir = codex_home / "sessions"
    session_dir.mkdir(parents=True)
    skill_root = codex_home / "skills"
    skill_dir = skill_root / "unused"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# Skill", encoding="utf-8")

    session_file = session_dir / "session-dup.jsonl"
    session_file.write_text(
        '{"timestamp":"2026-04-21T12:00:00+00:00","command":"cat "'
        + str(skill_file).replace("\\", "/")
        + '"}',
        encoding="utf-8",
    )

    initialize_database(db_path)
    first = import_codex_history(db_path, codex_home=codex_home, skill_roots=[skill_root])
    second = import_codex_history(
        db_path,
        codex_home=codex_home,
        skill_roots=[skill_root],
    )

    with sqlite3.connect(db_path) as connection:
        count = connection.execute(
            "select count(*) from skill_activation_events where source = ?",
            ("codex_session_skill_file",),
        ).fetchone()[0]

    assert first.imported_events == 1
    assert second.imported_events == 0
    assert count == 1
