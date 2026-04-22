# Changelog

_Release notes for Skill Health Dashboard._

---

## Unreleased

## v0.1.0 - 2026-04-21

### Added

- Real local skill inventory table and scanner (`skill_inventory`, `skillcheck scan skills`)
- Optional Codex history importer (`skillcheck import codex`) using conservative `SKILL.md` load proxies
- Doctor diagnostics command (`skillcheck doctor`)
- One-command refresh orchestration (`skillcheck refresh`)
- Structured summary output (`skillcheck summary --format json`) with default full-skill listing
- V2 six-dimension health scoring with confidence-aware statuses:
  - `security_score`
  - `clarity_score`
  - `overlap_score`
  - `stability_score`
  - `efficiency_score`
  - `confidence_score`
- New health categories: `Qualified`, `Watch`, `Unqualified`
- CI workflow for automated pytest checks on push and pull request

### MVP implementation

- Python CLI for local setup, demo loading, aggregation, and dashboard start
- SQLite schema for raw events, daily aggregates, and health scores
- Demo sample data with a current-UTC default anchor and fixed-anchor test support
- Aggregation and scoring that parse aware timestamps, bucket by normalized instants, and treat unavailable downstream data with neutral credit
- Overview dashboard page implemented as the first runnable UI surface
- `/api/overview` JSON endpoint for the dashboard

### Added

- Initial open source product documentation package
- Project README with local-first product positioning
- MVP PRD covering pages, scope, status rules, and acceptance criteria
- Data definitions for activation events, daily stats, and health scores
- Installation and usage guide for the planned MVP workflow
- Privacy and local data handling document
- Architecture document for collection, storage, aggregation, scoring, and dashboard layers
- Roadmap for Phase 1, Phase 2, and Phase 3
- MIT license
- GitHub issue templates for bug reports and feature requests
