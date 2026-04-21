from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import sqlite3


@dataclass(frozen=True)
class SummaryReport:
    window: str
    installed_skills: int
    scored_skills: int
    total_activations_30d: int
    status_breakdown: list[tuple[str, int]]
    average_dimensions: dict[str, float]
    top_skills: list[tuple[str, int, int, str, float, float]]
    action_hints: list[str]


def _build_action_hints(status_breakdown: list[tuple[str, int]]) -> list[str]:
    counts = {status: count for status, count in status_breakdown}
    unqualified = counts.get("Unqualified", 0)
    watch = counts.get("Watch", 0)
    qualified = counts.get("Qualified", 0)
    hints: list[str] = []

    if unqualified > 0:
        hints.append(
            f"Review and consider deleting/merging {unqualified} Unqualified skills first."
        )
    else:
        hints.append("No Unqualified skills detected; deletion is not urgent.")

    if watch > max(5, qualified):
        hints.append(
            "Watch count is high; gather more evidence or replace with clearer skills."
        )
    else:
        hints.append("Watch ratio is manageable; optimize gradually by priority.")

    if qualified == 0:
        hints.append("No Qualified skills yet; introduce stronger baseline skills.")
    else:
        hints.append(f"{qualified} Qualified skills are available as preferred options.")

    return hints


def build_summary_report(db_path: str | Path, top_limit: int | None = None) -> SummaryReport:
    path = Path(db_path)
    with sqlite3.connect(path) as connection:
        installed_skills = connection.execute(
            "select count(*) from skill_inventory"
        ).fetchone()[0]
        scored_skills = connection.execute(
            "select count(*) from skill_health_scores where window = ?",
            ("30d",),
        ).fetchone()[0]
        total_activations_30d = connection.execute(
            "select coalesce(sum(activation_count), 0) from skill_health_scores where window = ?",
            ("30d",),
        ).fetchone()[0]
        status_breakdown = connection.execute(
            """
            select status, count(*)
            from skill_health_scores
            where window = ?
            group by status
            order by count(*) desc, status asc
            """,
            ("30d",),
        ).fetchall()
        average_dimensions_row = connection.execute(
            """
            select
                coalesce(avg(security_score), 0.0),
                coalesce(avg(clarity_score), 0.0),
                coalesce(avg(overlap_score), 0.0),
                coalesce(avg(stability_score), 0.0),
                coalesce(avg(efficiency_score), 0.0),
                coalesce(avg(confidence_score), 0.0)
            from skill_health_scores
            where window = ?
            """,
            ("30d",),
        ).fetchone()
        base_sql = """
            select skill_name, v2_health_score, activation_count, v2_status, security_score, confidence_score
            from skill_health_scores
            where window = ?
            order by v2_health_score desc, activation_count desc, skill_name asc
        """
        if top_limit is None:
            top_skills = connection.execute(base_sql, ("30d",)).fetchall()
        else:
            top_skills = connection.execute(
                base_sql + " limit ?",
                ("30d", top_limit),
            ).fetchall()

    return SummaryReport(
        window="30d",
        installed_skills=int(installed_skills),
        scored_skills=int(scored_skills),
        total_activations_30d=int(total_activations_30d),
        status_breakdown=[(str(status), int(count)) for status, count in status_breakdown],
        average_dimensions={
            "security": float(average_dimensions_row[0]),
            "clarity": float(average_dimensions_row[1]),
            "overlap": float(average_dimensions_row[2]),
            "stability": float(average_dimensions_row[3]),
            "efficiency": float(average_dimensions_row[4]),
            "confidence": float(average_dimensions_row[5]),
        },
        top_skills=[
            (
                str(name),
                int(score),
                int(activations),
                str(status),
                float(security if security is not None else 0.0),
                float(confidence if confidence is not None else 0.0),
            )
            for name, score, activations, status, security, confidence in top_skills
        ],
        action_hints=_build_action_hints(
            [(str(status), int(count)) for status, count in status_breakdown]
        ),
    )


def render_summary_report(report: SummaryReport) -> str:
    lines = [
        f"Window: {report.window}",
        f"Installed skills: {report.installed_skills}",
        f"Scored skills: {report.scored_skills}",
        f"Total activations ({report.window}): {report.total_activations_30d}",
        "Average dimensions:",
        f"- security: {report.average_dimensions['security']:.1f}",
        f"- clarity: {report.average_dimensions['clarity']:.1f}",
        f"- overlap: {report.average_dimensions['overlap']:.1f}",
        f"- stability: {report.average_dimensions['stability']:.1f}",
        f"- efficiency: {report.average_dimensions['efficiency']:.1f}",
        f"- confidence: {report.average_dimensions['confidence']:.1f}",
        "Status breakdown:",
    ]
    if report.status_breakdown:
        lines.extend([f"- {status}: {count}" for status, count in report.status_breakdown])
    else:
        lines.append("- none")

    lines.append("Skills (30d):")
    if report.top_skills:
        lines.extend(
            [
                f"- {name}: score={score}, activations={activations}, status={status}, security={security:.1f}, confidence={confidence:.1f}"
                for name, score, activations, status, security, confidence in report.top_skills
            ]
        )
    else:
        lines.append("- none")
    lines.append("Action hints:")
    lines.extend([f"- {hint}" for hint in report.action_hints])
    return "\n".join(lines)


def summary_report_to_dict(report: SummaryReport) -> dict[str, object]:
    skills_payload = [
        {
            "skill_name": name,
            "v2_health_score": score,
            "activation_count": activations,
            "v2_status": status,
            "security_score": security,
            "confidence_score": confidence,
        }
        for name, score, activations, status, security, confidence in report.top_skills
    ]
    return {
        "version": "v2",
        "window": report.window,
        "totals": {
            "installed_skills": report.installed_skills,
            "scored_skills": report.scored_skills,
            "total_activations": report.total_activations_30d,
        },
        "average_dimensions": report.average_dimensions,
        "status_breakdown": [
            {"status": status, "count": count} for status, count in report.status_breakdown
        ],
        "skills": skills_payload,
        "top_skills_deprecated": True,
        "top_skills": skills_payload,
        "action_hints": report.action_hints,
    }


def render_summary_report_json(report: SummaryReport) -> str:
    return json.dumps(summary_report_to_dict(report), ensure_ascii=False, indent=2)
