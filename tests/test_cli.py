import sqlite3
from pathlib import Path

from skill_health.cli import build_parser
from skill_health.cli import main
from skill_health.dashboard import build_overview_payload
from skill_health.config import default_database_path


def test_parser_accepts_init_command():
    parser = build_parser()
    args = parser.parse_args(["init"])
    assert args.command == "init"
    assert args.db == str(default_database_path())


def test_parser_accepts_demo_load_command():
    parser = build_parser()
    args = parser.parse_args(["demo", "load"])
    assert args.command == "demo"
    assert args.demo_command == "load"


def test_parser_accepts_dashboard_command_with_port():
    parser = build_parser()
    args = parser.parse_args(["dashboard", "--port", "4242"])
    assert args.command == "dashboard"
    assert args.port == 4242


def test_parser_accepts_scan_skills_command():
    parser = build_parser()
    args = parser.parse_args(["scan", "skills"])
    assert args.command == "scan"
    assert args.scan_command == "skills"


def test_parser_accepts_import_codex_command():
    parser = build_parser()
    args = parser.parse_args(["import", "codex"])
    assert args.command == "import"
    assert args.import_command == "codex"


def test_parser_accepts_doctor_command():
    parser = build_parser()
    args = parser.parse_args(["doctor"])
    assert args.command == "doctor"


def test_parser_accepts_refresh_command():
    parser = build_parser()
    args = parser.parse_args(["refresh"])
    assert args.command == "refresh"


def test_parser_accepts_summary_command():
    parser = build_parser()
    args = parser.parse_args(["summary"])
    assert args.command == "summary"
    assert args.format == "text"
    assert args.all is False


def test_parser_accepts_summary_json_format():
    parser = build_parser()
    args = parser.parse_args(["summary", "--format", "json"])
    assert args.command == "summary"
    assert args.format == "json"


def test_parser_accepts_summary_all_flag():
    parser = build_parser()
    args = parser.parse_args(["summary", "--all"])
    assert args.command == "summary"
    assert args.all is True


def test_main_init_initializes_database(tmp_path, capsys):
    db_path = tmp_path / "skill-health.sqlite"

    exit_code = main(["init", "--db", str(db_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Local database initialized:" in captured.out
    assert db_path.exists()


def test_main_demo_load_loads_sample_events(tmp_path, capsys):
    db_path = tmp_path / "skill-health.sqlite"

    exit_code = main(["demo", "load", "--db", str(db_path)])
    captured = capsys.readouterr()
    with sqlite3.connect(db_path) as connection:
        inserted = connection.execute(
            "select count(*) from skill_activation_events"
        ).fetchone()[0]

    assert exit_code == 0
    assert captured.out == f"Loaded {inserted} sample events.\n"
    assert db_path.exists()

    second_exit = main(["demo", "load", "--db", str(db_path)])
    second_captured = capsys.readouterr()

    assert second_exit == 0
    assert second_captured.out == "Loaded 0 sample events.\n"


def test_main_demo_clear_removes_sample_events(tmp_path, capsys):
    db_path = tmp_path / "skill-health.sqlite"

    load_exit = main(["demo", "load", "--db", str(db_path)])
    capsys.readouterr()
    aggregate_exit = main(["aggregate", "--db", str(db_path)])
    capsys.readouterr()
    with sqlite3.connect(db_path) as connection:
        loaded = connection.execute(
            "select count(*) from skill_activation_events"
        ).fetchone()[0]
    clear_exit = main(["demo", "clear", "--db", str(db_path)])
    captured = capsys.readouterr()
    with sqlite3.connect(db_path) as connection:
        remaining_events = connection.execute(
            "select count(*) from skill_activation_events"
        ).fetchone()[0]
    payload = build_overview_payload(db_path)

    assert load_exit == 0
    assert aggregate_exit == 0
    assert clear_exit == 0
    assert captured.out == f"Cleared {loaded} sample events.\n"
    assert remaining_events == 0
    assert payload["total_skills"] == 0
    assert payload["sample_data"] is False
    assert payload["top_skills"] == []


def test_main_aggregate_rebuilds_derived_tables(tmp_path, capsys):
    db_path = tmp_path / "skill-health.sqlite"

    load_exit = main(["demo", "load", "--db", str(db_path)])
    capsys.readouterr()
    aggregate_exit = main(["aggregate", "--db", str(db_path)])
    captured = capsys.readouterr()

    with sqlite3.connect(db_path) as connection:
        daily_stats = connection.execute(
            "select count(*) from skill_daily_stats"
        ).fetchone()[0]
        health_scores = connection.execute(
            "select count(*) from skill_health_scores"
        ).fetchone()[0]

    assert load_exit == 0
    assert aggregate_exit == 0
    assert captured.out == (
        f"Rebuilt aggregates: {daily_stats} daily stats, {health_scores} health scores.\n"
    )
    assert daily_stats > 0
    assert health_scores >= 3


def test_main_dashboard_invokes_serve_dashboard_with_requested_settings(
    tmp_path, monkeypatch, capsys
):
    from skill_health import cli

    db_path = tmp_path / "skill-health.sqlite"
    calls: list[tuple[str, object]] = []

    def fake_serve_dashboard(db, host, port):
        calls.append(("serve", Path(db), host, port))

    def fake_rebuild_aggregates(db):
        calls.append(("aggregate", Path(db)))
        return type("Result", (), {"daily_stats": 0, "health_scores": 0})()

    monkeypatch.setattr(cli, "serve_dashboard", fake_serve_dashboard)
    monkeypatch.setattr(cli, "rebuild_aggregates", fake_rebuild_aggregates)

    exit_code = main(
        [
            "dashboard",
            "--db",
            str(db_path),
            "--host",
            "127.0.0.1",
            "--port",
            "4242",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert calls == [
        ("aggregate", db_path),
        ("serve", db_path, "127.0.0.1", 4242),
    ]
    assert db_path.exists()
    assert captured.out == ""


def test_main_scan_skills_invokes_inventory_scan(tmp_path, monkeypatch, capsys):
    from skill_health import cli

    db_path = tmp_path / "skill-health.sqlite"
    monkeypatch.setattr(
        cli,
        "scan_skill_roots",
        lambda db: type("Scan", (), {"scanned_files": 3, "upserted_skills": 2})(),
    )

    exit_code = main(["scan", "skills", "--db", str(db_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == "Scanned 3 SKILL.md files and upserted 2 skills.\n"


def test_main_import_codex_invokes_importer(tmp_path, monkeypatch, capsys):
    from skill_health import cli

    db_path = tmp_path / "skill-health.sqlite"
    monkeypatch.setattr(
        cli,
        "import_codex_history",
        lambda db: type("Import", (), {"imported_events": 4, "sessions_found": 2})(),
    )

    exit_code = main(["import", "codex", "--db", str(db_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (
        captured.out
        == "Imported 4 activation events from 2 Codex sessions.\n"
    )


def test_main_doctor_prints_report(tmp_path, monkeypatch, capsys):
    from skill_health import cli

    db_path = tmp_path / "skill-health.sqlite"

    monkeypatch.setattr(cli, "build_doctor_report", lambda db: object())
    monkeypatch.setattr(cli, "render_doctor_report", lambda report: "doctor-output")

    exit_code = main(["doctor", "--db", str(db_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == "doctor-output\n"


def test_main_refresh_runs_pipeline_and_prints_doctor(tmp_path, monkeypatch, capsys):
    from skill_health import cli

    db_path = tmp_path / "skill-health.sqlite"
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        cli,
        "scan_skill_roots",
        lambda db: calls.append(("scan", Path(db)))
        or type("Scan", (), {"scanned_files": 5, "upserted_skills": 4})(),
    )
    monkeypatch.setattr(
        cli,
        "import_codex_history",
        lambda db: calls.append(("import", Path(db)))
        or type("Import", (), {"imported_events": 8, "sessions_found": 3})(),
    )
    monkeypatch.setattr(
        cli,
        "rebuild_aggregates",
        lambda db: calls.append(("aggregate", Path(db)))
        or type("Agg", (), {"daily_stats": 9, "health_scores": 10})(),
    )
    monkeypatch.setattr(
        cli,
        "build_doctor_report",
        lambda db: calls.append(("doctor", Path(db))) or object(),
    )
    monkeypatch.setattr(cli, "render_doctor_report", lambda report: "doctor-output")

    exit_code = main(["refresh", "--db", str(db_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert calls == [
        ("scan", db_path),
        ("import", db_path),
        ("aggregate", db_path),
        ("doctor", db_path),
    ]
    assert "Refresh complete." in captured.out
    assert "doctor-output" in captured.out


def test_main_summary_prints_summary_report(tmp_path, monkeypatch, capsys):
    from skill_health import cli

    db_path = tmp_path / "skill-health.sqlite"
    seen: list[int | None] = []

    def fake_build(db, top_limit=None):
        seen.append(top_limit)
        return object()

    monkeypatch.setattr(cli, "build_summary_report", fake_build)
    monkeypatch.setattr(cli, "render_summary_report", lambda report: "summary-output")

    exit_code = main(["summary", "--db", str(db_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == "summary-output\n"
    assert seen == [None]


def test_main_summary_prints_summary_json(tmp_path, monkeypatch, capsys):
    from skill_health import cli

    db_path = tmp_path / "skill-health.sqlite"
    seen: list[int | None] = []

    def fake_build(db, top_limit=None):
        seen.append(top_limit)
        return object()

    monkeypatch.setattr(cli, "build_summary_report", fake_build)
    monkeypatch.setattr(cli, "render_summary_report_json", lambda report: '{"ok": true}')

    exit_code = main(["summary", "--format", "json", "--db", str(db_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == '{"ok": true}\n'
    assert seen == [None]


def test_main_summary_all_passes_no_limit(tmp_path, monkeypatch, capsys):
    from skill_health import cli

    db_path = tmp_path / "skill-health.sqlite"
    seen: list[int | None] = []

    def fake_build(db, top_limit=None):
        seen.append(top_limit)
        return object()

    monkeypatch.setattr(cli, "build_summary_report", fake_build)
    monkeypatch.setattr(cli, "render_summary_report", lambda report: "summary-output")

    exit_code = main(["summary", "--all", "--db", str(db_path)])
    capsys.readouterr()

    assert exit_code == 0
    assert seen == [None]
