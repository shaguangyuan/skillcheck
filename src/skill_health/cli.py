from __future__ import annotations

import argparse
from typing import Sequence

from skill_health.config import default_database_path
from skill_health.aggregate import rebuild_aggregates
from skill_health.dashboard import serve_dashboard
from skill_health.demo import clear_demo_data
from skill_health.demo import load_demo_data
from skill_health.doctor import build_doctor_report
from skill_health.doctor import render_doctor_report
from skill_health.importers.codex import import_codex_history
from skill_health.inventory import scan_skill_roots
from skill_health.storage import initialize_database
from skill_health.summary import build_summary_report
from skill_health.summary import render_summary_report
from skill_health.summary import render_summary_report_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skillcheck")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize local storage")
    init_parser.add_argument("--db", default=str(default_database_path()))
    init_parser.set_defaults(command="init")

    demo_parser = subparsers.add_parser("demo", help="Manage demo data")
    demo_subparsers = demo_parser.add_subparsers(dest="demo_command", required=True)
    demo_load_parser = demo_subparsers.add_parser("load", help="Load demo data")
    demo_load_parser.add_argument("--db", default=str(default_database_path()))
    demo_load_parser.set_defaults(command="demo", demo_command="load")
    demo_clear_parser = demo_subparsers.add_parser("clear", help="Clear demo data")
    demo_clear_parser.add_argument("--db", default=str(default_database_path()))
    demo_clear_parser.set_defaults(command="demo", demo_command="clear")
    demo_parser.set_defaults(command="demo")

    scan_parser = subparsers.add_parser("scan", help="Scan local data sources")
    scan_subparsers = scan_parser.add_subparsers(dest="scan_command", required=True)
    scan_skills_parser = scan_subparsers.add_parser(
        "skills", help="Scan installed SKILL.md files"
    )
    scan_skills_parser.add_argument("--db", default=str(default_database_path()))
    scan_skills_parser.set_defaults(command="scan", scan_command="skills")
    scan_parser.set_defaults(command="scan")

    import_parser = subparsers.add_parser("import", help="Import local usage history")
    import_subparsers = import_parser.add_subparsers(
        dest="import_command", required=True
    )
    import_codex_parser = import_subparsers.add_parser(
        "codex", help="Import local Codex skill usage proxies"
    )
    import_codex_parser.add_argument("--db", default=str(default_database_path()))
    import_codex_parser.set_defaults(command="import", import_command="codex")
    import_parser.set_defaults(command="import")

    refresh_parser = subparsers.add_parser(
        "refresh", help="Run scan, import, aggregate, and doctor"
    )
    refresh_parser.add_argument("--db", default=str(default_database_path()))
    refresh_parser.set_defaults(command="refresh")

    aggregate_parser = subparsers.add_parser("aggregate", help="Aggregate local data")
    aggregate_parser.add_argument("--db", default=str(default_database_path()))
    aggregate_parser.set_defaults(command="aggregate")

    dashboard_parser = subparsers.add_parser("dashboard", help="Run the dashboard")
    dashboard_parser.add_argument("--db", default=str(default_database_path()))
    dashboard_parser.add_argument("--host", default="127.0.0.1")
    dashboard_parser.add_argument("--port", type=int, default=3000)
    dashboard_parser.set_defaults(command="dashboard")

    doctor_parser = subparsers.add_parser("doctor", help="Run local diagnostics")
    doctor_parser.add_argument("--db", default=str(default_database_path()))
    doctor_parser.set_defaults(command="doctor")

    summary_parser = subparsers.add_parser(
        "summary", help="Print text summary in terminal"
    )
    summary_parser.add_argument("--db", default=str(default_database_path()))
    summary_parser.add_argument("--format", choices=["text", "json"], default="text")
    summary_parser.add_argument(
        "--all",
        action="store_true",
        help="Include all scored skills instead of top 10",
    )
    summary_parser.set_defaults(command="summary")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        database_path = initialize_database(args.db)
        print(f"Local database initialized: {database_path}")
        return 0

    if args.command == "demo" and args.demo_command == "load":
        initialize_database(args.db)
        inserted = load_demo_data(args.db)
        print(f"Loaded {inserted} sample events.")
        return 0

    if args.command == "demo" and args.demo_command == "clear":
        initialize_database(args.db)
        removed = clear_demo_data(args.db)
        rebuild_aggregates(args.db)
        print(f"Cleared {removed} sample events.")
        return 0

    if args.command == "aggregate":
        initialize_database(args.db)
        result = rebuild_aggregates(args.db)
        print(
            f"Rebuilt aggregates: {result.daily_stats} daily stats, {result.health_scores} health scores."
        )
        return 0

    if args.command == "scan" and args.scan_command == "skills":
        initialize_database(args.db)
        result = scan_skill_roots(args.db)
        print(
            "Scanned "
            f"{result.scanned_files} SKILL.md files and upserted {result.upserted_skills} skills."
        )
        return 0

    if args.command == "import" and args.import_command == "codex":
        initialize_database(args.db)
        result = import_codex_history(args.db)
        print(
            "Imported "
            f"{result.imported_events} activation events from {result.sessions_found} Codex sessions."
        )
        return 0

    if args.command == "refresh":
        initialize_database(args.db)
        scan_result = scan_skill_roots(args.db)
        import_result = import_codex_history(args.db)
        aggregate_result = rebuild_aggregates(args.db)
        report = build_doctor_report(args.db)
        rendered_report = render_doctor_report(report)
        print(
            "Refresh complete. "
            f"Scanned {scan_result.scanned_files} files ({scan_result.upserted_skills} upserted), "
            f"imported {import_result.imported_events} events from {import_result.sessions_found} sessions, "
            f"rebuilt {aggregate_result.daily_stats} daily stats and {aggregate_result.health_scores} scores."
        )
        print(rendered_report)
        return 0

    if args.command == "dashboard":
        initialize_database(args.db)
        rebuild_aggregates(args.db)
        serve_dashboard(args.db, args.host, args.port)
        return 0

    if args.command == "doctor":
        initialize_database(args.db)
        report = build_doctor_report(args.db)
        print(render_doctor_report(report))
        return 0

    if args.command == "summary":
        initialize_database(args.db)
        report = build_summary_report(args.db, top_limit=None)
        if args.format == "json":
            print(render_summary_report_json(report))
        else:
            print(render_summary_report(report))
        return 0

    parser.error(f"command not implemented yet: {args.command}")
