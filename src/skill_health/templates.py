from __future__ import annotations

from html import escape


STATUS_CLASS_MAP = {
    "Qualified": "healthy",
    "Watch": "review",
    "Unqualified": "candidate",
}


def page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)}</title>
    <style>
      :root {{
        color-scheme: light;
        --bg: #f5f7fb;
        --panel: #ffffff;
        --text: #122033;
        --muted: #5f6b7a;
        --border: #d8e0ea;
        --accent: #2356d7;
        --healthy: #127a3f;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: Arial, Helvetica, sans-serif;
        background: var(--bg);
        color: var(--text);
      }}
      main {{
        max-width: 1120px;
        margin: 0 auto;
        padding: 32px 20px 48px;
      }}
      h1, h2, h3, p {{ margin: 0; }}
      .hero {{
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-bottom: 24px;
      }}
      .eyebrow {{
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 12px;
        color: var(--muted);
      }}
      .summary-grid, .status-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px;
        margin-bottom: 24px;
      }}
      .panel {{
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 16px;
      }}
      .metric {{
        font-size: 30px;
        font-weight: 700;
        margin-top: 8px;
      }}
      .label {{
        color: var(--muted);
        font-size: 14px;
      }}
      .status-name {{
        font-size: 15px;
        font-weight: 700;
      }}
      .status-count {{
        font-size: 26px;
        font-weight: 700;
        margin-top: 8px;
      }}
      .banner {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        border: 1px solid #d4c58a;
        background: #fff8db;
        color: #735c07;
        border-radius: 999px;
        padding: 6px 12px;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 16px;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 8px;
        overflow: hidden;
      }}
      th, td {{
        text-align: left;
        padding: 12px 14px;
        border-bottom: 1px solid var(--border);
        vertical-align: top;
      }}
      th {{
        background: #eef3fb;
        color: var(--muted);
        font-size: 13px;
        text-transform: uppercase;
      }}
      tr:last-child td {{ border-bottom: 0; }}
      .status-healthy {{ color: var(--healthy); }}
      .status-candidate {{ color: #a04b00; }}
      .status-review {{ color: var(--accent); }}
    </style>
  </head>
  <body>
    <main>
      {body}
    </main>
  </body>
</html>"""


def overview(payload: dict[str, object]) -> str:
    status_counts = payload.get("status_counts", {})
    top_skills = payload.get("top_skills", [])
    sample_data = bool(payload.get("sample_data"))

    status_cards = []
    for status, count in sorted(status_counts.items()):  # type: ignore[union-attr]
        status_slug = STATUS_CLASS_MAP.get(str(status), "other")
        status_cards.append(
            f"""<section class="panel status-{status_slug}">
              <div class="status-name">{escape(str(status))}</div>
              <div class="status-count">{int(count)}</div>
            </section>"""
        )

    rows = []
    for skill in top_skills:  # type: ignore[assignment]
        status = str(skill.get("status", ""))
        status_slug = STATUS_CLASS_MAP.get(status, "other")
        reasons = skill.get("diagnostic_reasons", [])
        reason_text = "; ".join(str(reason) for reason in reasons)
        rows.append(
            "<tr>"
            f"<td>{escape(str(skill.get('skill_name', '')))}</td>"
            f"<td>{escape(str(skill.get('skill_id', '')))}</td>"
            f"<td class=\"status status-{status_slug}\">{escape(status)}</td>"
            f"<td>{int(skill.get('health_score', 0))}</td>"
            f"<td>{int(skill.get('activation_count', 0))}</td>"
            f"<td>{int(skill.get('unique_sessions', 0))}</td>"
            f"<td>{escape(str(skill.get('last_seen', '')))}</td>"
            f"<td>{escape(reason_text)}</td>"
            "</tr>"
        )

    body = f"""
      <section class="hero">
        <div class="eyebrow">Local overview</div>
        <h1>Skill Health Dashboard</h1>
        <p class="label">Window: {escape(str(payload.get('window', '')))} · Total skills: {int(payload.get('total_skills', 0))}</p>
        {'<div class="banner">Sample data</div>' if sample_data else ''}
      </section>
      <section class="summary-grid">
        <section class="panel">
          <div class="label">Total skills</div>
          <div class="metric">{int(payload.get('total_skills', 0))}</div>
        </section>
      </section>
      <section class="status-grid">
        {''.join(status_cards)}
      </section>
      <section class="panel" style="padding:0">
        <table>
          <thead>
            <tr>
              <th>Skill</th>
              <th>ID</th>
              <th>Status</th>
              <th>Score</th>
              <th>Activations</th>
              <th>Sessions</th>
              <th>Last seen</th>
              <th>Signals</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
      </section>
    """
    return page("Skill Health Dashboard", body)
