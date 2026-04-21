from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from skill_health.config import default_database_path


@dataclass(frozen=True)
class DoctorReport:
    database_path: str
    installed_skills_found: int
    codex_sessions_found: int
    imported_activations: int
    sample_data_present: bool
    last_aggregate: str | None
    dashboard_ready: bool
    low_confidence_skills: int
    high_risk_skills: int


def build_doctor_report(
    db_path: str | Path,
    *,
    codex_home: Path | None = None,
) -> DoctorReport:
    database_path = Path(db_path).expanduser()
    codex_root = (codex_home or (Path.home() / ".codex")).expanduser()
    sessions_root = codex_root / "sessions"
    codex_sessions_found = (
        len(list(sessions_root.glob("**/*.jsonl"))) if sessions_root.exists() else 0
    )

    if not database_path.exists():
        return DoctorReport(
            database_path=str(database_path),
            installed_skills_found=0,
            codex_sessions_found=codex_sessions_found,
            imported_activations=0,
            sample_data_present=False,
            last_aggregate=None,
            dashboard_ready=False,
            low_confidence_skills=0,
            high_risk_skills=0,
        )

    with sqlite3.connect(database_path) as connection:
        installed_skills_found = connection.execute(
            "select count(*) from skill_inventory"
        ).fetchone()[0]
        imported_activations = connection.execute(
            "select count(*) from skill_activation_events where source = ?",
            ("codex_session_skill_file",),
        ).fetchone()[0]
        sample_data_present = (
            connection.execute(
                "select 1 from skill_activation_events where source = ? limit 1",
                ("sample_data",),
            ).fetchone()
            is not None
        )
        last_aggregate = connection.execute(
            "select max(calculated_at) from skill_health_scores where window = ?",
            ("30d",),
        ).fetchone()[0]
        dashboard_ready = (
            connection.execute(
                "select count(*) from skill_health_scores where window = ?",
                ("30d",),
            ).fetchone()[0]
            > 0
        )
        low_confidence_skills = connection.execute(
            """
            select count(*)
            from skill_health_scores
            where window = ? and confidence_score is not null and confidence_score < 40
            """,
            ("30d",),
        ).fetchone()[0]
        high_risk_skills = connection.execute(
            """
            select count(*)
            from skill_health_scores
            where window = ?
              and risk_flags is not null
              and risk_flags like '%security:%'
            """,
            ("30d",),
        ).fetchone()[0]

    return DoctorReport(
        database_path=str(database_path),
        installed_skills_found=int(installed_skills_found),
        codex_sessions_found=codex_sessions_found,
        imported_activations=int(imported_activations),
        sample_data_present=bool(sample_data_present),
        last_aggregate=last_aggregate,
        dashboard_ready=bool(dashboard_ready),
        low_confidence_skills=int(low_confidence_skills),
        high_risk_skills=int(high_risk_skills),
    )


def render_doctor_report(report: DoctorReport) -> str:
    lines = [
        f"Database: {report.database_path}",
        f"Installed skills found: {report.installed_skills_found}",
        f"Codex sessions found: {report.codex_sessions_found}",
        f"Imported activations: {report.imported_activations}",
        f"Sample data present: {'yes' if report.sample_data_present else 'no'}",
        f"Last aggregate: {report.last_aggregate or 'none'}",
        f"Low confidence skills: {report.low_confidence_skills}",
        f"High risk skills: {report.high_risk_skills}",
        f"Dashboard ready: {'yes' if report.dashboard_ready else 'no'}",
    ]
    return "\n".join(lines)


def default_doctor_report() -> DoctorReport:
    return build_doctor_report(default_database_path())
