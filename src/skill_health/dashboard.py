from __future__ import annotations

import json
import sqlite3
from collections import Counter
from functools import partial
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
from pathlib import Path

from skill_health import templates
from skill_health.storage import initialize_database

STATUS_CLASS_MAP = {
    "Qualified": "healthy",
    "Watch": "review",
    "Unqualified": "candidate",
}


def build_overview_payload(db_path: str | Path) -> dict[str, object]:
    path = Path(db_path)
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            """
            select
                skill_id,
                skill_name,
                activation_count,
                unique_sessions,
                last_seen,
                v2_health_score,
                v2_status,
                v2_reasons,
                security_score,
                confidence_score
            from skill_health_scores
            where window = ?
            order by v2_health_score desc, activation_count desc, skill_name asc
            """,
            ("30d",),
        ).fetchall()
        sample_data = (
            connection.execute(
                "select 1 from skill_activation_events where source = ? limit 1",
                ("sample_data",),
            ).fetchone()
            is not None
        )

    top_skills = []
    status_counts: Counter[str] = Counter(
        {
            "Qualified": 0,
            "Watch": 0,
            "Unqualified": 0,
        }
    )
    for (
        skill_id,
        skill_name,
        activation_count,
        unique_sessions,
        last_seen,
        health_score,
        status,
        diagnostic_reasons,
        security_score,
        confidence_score,
    ) in rows:
        status_counts[str(status)] += 1
        top_skills.append(
            {
                "skill_id": skill_id,
                "skill_name": skill_name,
                "activation_count": int(activation_count),
                "unique_sessions": int(unique_sessions),
                "last_seen": last_seen,
                "health_score": int(health_score),
                "status": status,
                "diagnostic_reasons": json.loads(diagnostic_reasons),
                "security_score": float(security_score) if security_score is not None else None,
                "confidence_score": float(confidence_score) if confidence_score is not None else None,
            }
        )

    return {
        "window": "30d",
        "total_skills": len(top_skills),
        "status_counts": dict(status_counts),
        "top_skills": top_skills[:5],
        "sample_data": sample_data,
    }


def render_overview_html(payload: dict[str, object]) -> str:
    return templates.overview(payload)


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "SkillHealthDashboard/1.0"

    def __init__(self, *args, db_path: str | Path, **kwargs):
        self.db_path = Path(db_path)
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/overview"}:
            payload = build_overview_payload(self.db_path)
            html = render_overview_html(payload)
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/api/overview":
            payload = build_overview_payload(self.db_path)
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_error(404, "Not Found")

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def serve_dashboard(db_path: str | Path, host: str, port: int) -> None:
    initialize_database(db_path)
    handler = partial(DashboardHandler, db_path=db_path)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Skill Health Dashboard is running locally: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
