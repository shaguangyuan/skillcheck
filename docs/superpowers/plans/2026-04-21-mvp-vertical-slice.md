# Skill Health Dashboard MVP Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable local MVP: initialize SQLite storage, load sample skill events, aggregate health metrics, and view them in a local dashboard.

**Architecture:** Use a small Python package with clear modules for CLI, storage, demo data, aggregation, scoring, and dashboard serving. The MVP uses SQLite for local data and a standard-library HTTP server for the dashboard to minimize installation friction.

**Tech Stack:** Python 3.11+, SQLite via `sqlite3`, standard-library `http.server`, `pytest` for tests, no frontend build step.

---

## File structure

| Path | Responsibility |
| --- | --- |
| `pyproject.toml` | Package metadata, pytest config, console script |
| `src/skill_health/__init__.py` | Package version |
| `src/skill_health/__main__.py` | Enables `python -m skill_health` |
| `src/skill_health/cli.py` | CLI commands |
| `src/skill_health/config.py` | Default local paths |
| `src/skill_health/storage.py` | SQLite schema and database helpers |
| `src/skill_health/demo.py` | Synthetic demo event loading and clearing |
| `src/skill_health/aggregate.py` | Daily stats and health score aggregation |
| `src/skill_health/scoring.py` | Health score and status calculation |
| `src/skill_health/dashboard.py` | Local HTTP dashboard and JSON endpoints |
| `src/skill_health/templates.py` | HTML rendering helpers |
| `tests/` | Pytest coverage for each module |

## Task 1: Scaffold package and CLI entry point

**Files:**

- Create: `pyproject.toml`
- Create: `src/skill_health/__init__.py`
- Create: `src/skill_health/__main__.py`
- Create: `src/skill_health/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_cli.py`:

```python
from skill_health.cli import build_parser


def test_parser_accepts_init_command():
    parser = build_parser()
    args = parser.parse_args(["init"])
    assert args.command == "init"


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
```

- [ ] **Step 2: Run the CLI tests and verify they fail**

Run: `pytest tests/test_cli.py -v`

Expected: FAIL because the `skill_health` package and `build_parser` function do not exist yet.

- [ ] **Step 3: Add package metadata**

Create `pyproject.toml` with setuptools metadata, Python `>=3.11`, optional `dev = ["pytest>=8.0"]`, console script `skillcheck = "skill_health.cli:main"`, package discovery under `src`, and pytest `pythonpath = ["src"]`.

- [ ] **Step 4: Add minimal package files**

Create `src/skill_health/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/skill_health/__main__.py`:

```python
from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Add the CLI parser**

Create `src/skill_health/cli.py` with `build_parser()` supporting `init`, `demo load`, `demo clear`, `aggregate`, and `dashboard --host --port`.

- [ ] **Step 6: Run the CLI tests and verify they pass**

Run: `pytest tests/test_cli.py -v`

Expected: PASS with 3 tests passing.

## Task 2: Implement local SQLite schema initialization

**Files:**

- Create: `src/skill_health/config.py`
- Create: `src/skill_health/storage.py`
- Modify: `src/skill_health/cli.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write failing storage tests**

Create `tests/test_storage.py`:

```python
import sqlite3

from skill_health.storage import initialize_database


def table_names(db_path):
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "select name from sqlite_master where type = 'table' order by name"
        ).fetchall()
    return [row[0] for row in rows]


def test_initialize_database_creates_required_tables(tmp_path):
    db_path = tmp_path / "skillcheck.sqlite"
    initialize_database(db_path)
    assert table_names(db_path) == [
        "skill_activation_events",
        "skill_daily_stats",
        "skill_health_scores",
    ]


def test_initialize_database_is_idempotent(tmp_path):
    db_path = tmp_path / "skillcheck.sqlite"
    initialize_database(db_path)
    initialize_database(db_path)
    assert table_names(db_path) == [
        "skill_activation_events",
        "skill_daily_stats",
        "skill_health_scores",
    ]
```

- [ ] **Step 2: Run the storage tests and verify they fail**

Run: `pytest tests/test_storage.py -v`

Expected: FAIL because `skill_health.storage` does not exist.

- [ ] **Step 3: Add path configuration**

Create `src/skill_health/config.py`:

```python
from __future__ import annotations

from pathlib import Path


def default_data_dir() -> Path:
    return Path.home() / ".skillcheck"


def default_database_path() -> Path:
    return default_data_dir() / "skillcheck.sqlite"
```

- [ ] **Step 4: Add SQLite schema creation**

Create `src/skill_health/storage.py` with an `initialize_database(db_path)` function that creates:

- `skill_activation_events`
- `skill_daily_stats`
- `skill_health_scores`

Use the fields defined in `docs/data-definitions.md`.

- [ ] **Step 5: Wire `skillcheck init`**

Modify `src/skill_health/cli.py` so `skillcheck init --db <path>` calls `initialize_database()` and prints `Local database initialized: <path>`.

- [ ] **Step 6: Run storage and CLI tests**

Run: `pytest tests/test_storage.py tests/test_cli.py -v`

Expected: PASS with 5 tests passing.

## Task 3: Add sample data loading and clearing

**Files:**

- Create: `src/skill_health/demo.py`
- Modify: `src/skill_health/cli.py`
- Create: `tests/test_demo.py`

- [ ] **Step 1: Write failing demo data tests**

Create `tests/test_demo.py`:

```python
import sqlite3

from skill_health.demo import clear_demo_data, load_demo_data
from skill_health.storage import initialize_database


def count_events(db_path):
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("select count(*) from skill_activation_events").fetchone()
    return row[0]


def test_load_demo_data_inserts_synthetic_events(tmp_path):
    db_path = tmp_path / "skillcheck.sqlite"
    initialize_database(db_path)
    inserted = load_demo_data(db_path)
    assert inserted > 0
    assert count_events(db_path) == inserted


def test_clear_demo_data_removes_sample_events(tmp_path):
    db_path = tmp_path / "skillcheck.sqlite"
    initialize_database(db_path)
    load_demo_data(db_path)
    removed = clear_demo_data(db_path)
    assert removed > 0
    assert count_events(db_path) == 0
```

- [ ] **Step 2: Run demo tests and verify they fail**

Run: `pytest tests/test_demo.py -v`

Expected: FAIL because `skill_health.demo` does not exist.

- [ ] **Step 3: Implement deterministic demo data**

Create `src/skill_health/demo.py` with:

- `build_demo_events(now=None)` returning synthetic rows for `research-lookup`, `broad-writer`, and `old-formatter`
- `load_demo_data(db_path)` inserting rows with `source = "sample_data"`
- `clear_demo_data(db_path)` deleting only rows with `source = "sample_data"`

- [ ] **Step 4: Wire `demo load` and `demo clear`**

Modify `src/skill_health/cli.py` so:

- `skillcheck demo load --db <path>` initializes the database and loads sample events
- `skillcheck demo clear --db <path>` initializes the database and clears sample events

- [ ] **Step 5: Run demo, storage, and CLI tests**

Run: `pytest tests/test_demo.py tests/test_storage.py tests/test_cli.py -v`

Expected: PASS with 7 tests passing.

## Task 4: Implement aggregation and health scoring

**Files:**

- Create: `src/skill_health/scoring.py`
- Create: `src/skill_health/aggregate.py`
- Modify: `src/skill_health/cli.py`
- Create: `tests/test_scoring.py`
- Create: `tests/test_aggregate.py`

- [ ] **Step 1: Write failing scoring tests**

Create `tests/test_scoring.py`:

```python
from skill_health.scoring import classify_health, score_health


def test_score_health_rates_recent_frequent_use_as_healthy():
    result = score_health(
        activation_count=12,
        unique_sessions=6,
        days_since_last_seen=2,
        avg_tool_depth=4.0,
        failure_proxy_rate=0.0,
    )
    assert result.health_score == 100
    assert result.status == "Healthy"


def test_score_health_marks_stale_low_value_skill_as_candidate():
    result = score_health(
        activation_count=0,
        unique_sessions=0,
        days_since_last_seen=120,
        avg_tool_depth=0.0,
        failure_proxy_rate=1.0,
    )
    assert result.health_score == 0
    assert result.status == "Candidate to Merge/Retire"


def test_classify_health_marks_middle_score_for_review():
    assert classify_health(55, []) == "Needs Review"
```

- [ ] **Step 2: Run scoring tests and verify they fail**

Run: `pytest tests/test_scoring.py -v`

Expected: FAIL because `skill_health.scoring` does not exist.

- [ ] **Step 3: Implement scoring rules**

Create `src/skill_health/scoring.py` with:

- `HealthResult` dataclass containing `health_score`, `status`, and `diagnostic_reasons`
- `classify_health(score, severe_flags)` returning one of the three MVP statuses
- `score_health(...)` applying the point model from `docs/data-definitions.md`

- [ ] **Step 4: Write failing aggregation tests**

Create `tests/test_aggregate.py`:

```python
import sqlite3

from skill_health.aggregate import rebuild_aggregates
from skill_health.demo import load_demo_data
from skill_health.storage import initialize_database


def test_rebuild_aggregates_creates_daily_stats_and_scores(tmp_path):
    db_path = tmp_path / "skillcheck.sqlite"
    initialize_database(db_path)
    load_demo_data(db_path)
    result = rebuild_aggregates(db_path)
    assert result.daily_stats > 0
    assert result.health_scores >= 2


def test_rebuild_aggregates_assigns_expected_demo_statuses(tmp_path):
    db_path = tmp_path / "skillcheck.sqlite"
    initialize_database(db_path)
    load_demo_data(db_path)
    rebuild_aggregates(db_path)
    with sqlite3.connect(db_path) as conn:
        statuses = dict(
            conn.execute(
                "select skill_name, status from skill_health_scores where window = '30d'"
            ).fetchall()
        )
    assert statuses["research-lookup"] == "Healthy"
    assert statuses["broad-writer"] in {"Needs Review", "Candidate to Merge/Retire"}
```

- [ ] **Step 5: Run aggregation tests and verify they fail**

Run: `pytest tests/test_aggregate.py -v`

Expected: FAIL because `skill_health.aggregate` does not exist.

- [ ] **Step 6: Implement aggregate rebuilding**

Create `src/skill_health/aggregate.py` with:

- `AggregateResult` dataclass containing `daily_stats` and `health_scores`
- `rebuild_aggregates(db_path, now=None)` deleting and rebuilding derived tables
- daily aggregation grouped by date and skill
- 30-day health scoring grouped by skill
- JSON-encoded `diagnostic_reasons`

- [ ] **Step 7: Wire `skillcheck aggregate`**

Modify `src/skill_health/cli.py` so `skillcheck aggregate --db <path>` initializes storage, rebuilds aggregates, and prints counts.

- [ ] **Step 8: Run aggregation and scoring tests**

Run: `pytest tests/test_scoring.py tests/test_aggregate.py tests/test_demo.py tests/test_storage.py tests/test_cli.py -v`

Expected: PASS with 12 tests passing.

## Task 5: Add local dashboard overview and JSON endpoint

**Files:**

- Create: `src/skill_health/templates.py`
- Create: `src/skill_health/dashboard.py`
- Modify: `src/skill_health/cli.py`
- Create: `tests/test_dashboard.py`

- [ ] **Step 1: Write failing dashboard tests**

Create `tests/test_dashboard.py`:

```python
import json

from skill_health.aggregate import rebuild_aggregates
from skill_health.dashboard import build_overview_payload, render_overview_html
from skill_health.demo import load_demo_data
from skill_health.storage import initialize_database


def test_build_overview_payload_returns_status_counts(tmp_path):
    db_path = tmp_path / "skillcheck.sqlite"
    initialize_database(db_path)
    load_demo_data(db_path)
    rebuild_aggregates(db_path)
    payload = build_overview_payload(db_path)
    assert payload["window"] == "30d"
    assert payload["total_skills"] >= 2
    assert "Healthy" in payload["status_counts"]
    json.dumps(payload)


def test_render_overview_html_contains_dashboard_title():
    html = render_overview_html(
        {
            "window": "30d",
            "total_skills": 1,
            "status_counts": {"Healthy": 1},
            "top_skills": [{"skill_name": "research-lookup", "activation_count": 10, "status": "Healthy"}],
        }
    )
    assert "Skill Health Dashboard" in html
    assert "research-lookup" in html
```

- [ ] **Step 2: Run dashboard tests and verify they fail**

Run: `pytest tests/test_dashboard.py -v`

Expected: FAIL because `skill_health.dashboard` does not exist.

- [ ] **Step 3: Add HTML templates**

Create `src/skill_health/templates.py` with:

- `page(title, body)` returning a complete HTML document
- `overview(payload)` rendering total skills, status cards, and top skills
- inline CSS with restrained, readable local dashboard styling

- [ ] **Step 4: Add dashboard payloads and server**

Create `src/skill_health/dashboard.py` with:

- `build_overview_payload(db_path)` reading `skill_health_scores`
- `render_overview_html(payload)` delegating to templates
- `DashboardHandler` serving `/`, `/overview`, and `/api/overview`
- `serve_dashboard(db_path, host, port)` using `ThreadingHTTPServer`

- [ ] **Step 5: Wire `skillcheck dashboard`**

Modify `src/skill_health/cli.py` so `skillcheck dashboard --db <path> --host 127.0.0.1 --port 3000` initializes storage and serves the dashboard.

- [ ] **Step 6: Run all tests**

Run: `pytest -v`

Expected: PASS with all tests passing.

## Task 6: Update documentation for the runnable MVP

**Files:**

- Modify: `README.md`
- Modify: `docs/install-and-usage.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Update README quick start**

Add a `Quick start` section to `README.md` after the documentation table:

````markdown
## Quick start

```bash
python -m pip install -e ".[dev]"
skillcheck init
skillcheck demo load
skillcheck aggregate
skillcheck dashboard
```

Then open `http://127.0.0.1:3000`.
````

- [ ] **Step 2: Update installation guide commands**

In `docs/install-and-usage.md`, replace planned command shapes with the concrete MVP commands:

```bash
python -m pip install -e ".[dev]"
skillcheck init
skillcheck demo load
skillcheck aggregate
skillcheck dashboard
```

- [ ] **Step 3: Update changelog**

Add under `Unreleased` in `CHANGELOG.md`:

```markdown
### MVP implementation

- Added Python package scaffold and CLI
- Added SQLite schema initialization
- Added synthetic sample data loading and clearing
- Added local aggregation and health scoring
- Added local dashboard overview page and JSON endpoint
```

- [ ] **Step 4: Run final verification**

Run:

```bash
pytest -v
python -m skill_health --help
```

Expected:

- `pytest` passes
- `python -m skill_health --help` prints CLI help with `init`, `demo`, `aggregate`, and `dashboard`

## Execution notes

- Use TDD for each task: write the test, watch it fail, implement the smallest passing code, then rerun.
- The first MVP includes only the Overview page. Skill Table and Skill Detail are the next vertical slice after storage, demo data, aggregation, and dashboard serving are proven.
- Do not add cloud sync, account login, remote telemetry, automatic skill edits, or AI diagnostics in this implementation slice.
- Because the current directory is not a git repository, worktree creation and commits are unavailable until git is initialized.

