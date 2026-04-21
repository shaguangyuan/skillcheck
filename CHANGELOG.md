# Changelog

_Release notes for Skill Health Dashboard._

---

## Unreleased

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
