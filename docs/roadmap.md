# Skill Health Dashboard Roadmap

_Planned release path for the local-first Skill Health Dashboard project._

---

## Roadmap principles

Skill Health Dashboard should grow from a small, trustworthy local tool into a richer skill maintenance assistant without losing its local-first character.

The roadmap follows these principles:

- Start with local visibility before automation
- Keep the MVP understandable and installable
- Make every metric explainable
- Treat health labels as review prompts, not commands
- Avoid cloud dependency by default
- Add intelligent assistance only after the rule-based foundation is useful

## Phase overview

| Phase | Theme | Outcome |
| --- | --- | --- |
| Phase 1 | Local MVP | Users can collect local skill activation data, view dashboard metrics, and identify review candidates |
| Phase 2 | Better insight | Users get richer trends, similarity signals, and exportable local reports |
| Phase 3 | Optional assistance | Users can ask for review help, rewrite suggestions, and split or merge guidance |

## Phase 1: Local MVP

Phase 1 proves the core product value: a user can install the tool locally, see skill usage, and decide which skills deserve attention.

### Included

| Area | Scope |
| --- | --- |
| Local collection | Ingest local skill activation events centered on `claude_code.skill_activated` |
| Local storage | Store raw events and aggregates in SQLite |
| Dashboard | Provide Overview, Skill Table, and Skill Detail pages |
| Health scoring | Use transparent rule-based scoring |
| Status labels | Classify skills as `Healthy`, `Needs Review`, or `Candidate to Merge/Retire` |
| Sample data | Provide synthetic data for demo and first-run validation |
| Documentation | Provide README, PRD, data definitions, installation guide, privacy document, and roadmap |

### Not included

- Cloud accounts
- Multi-user analytics
- Remote synchronization
- Automatic skill editing
- Automatic pull request creation
- Advanced AI diagnostic agents
- Enterprise controls

### Success criteria

- A new user can install and launch the local dashboard
- The dashboard works with sample data
- The dashboard can display at least one real skill after collection is configured
- The user can understand the three health statuses
- The user can identify at least one skill worth reviewing
- No remote backend is required

## Phase 2: Better insight

Phase 2 improves the quality of recommendations while keeping the product local and transparent.

### Candidate features

| Feature | Value |
| --- | --- |
| Similar skill detection | Helps users find overlapping or redundant skills |
| Richer trend analysis | Shows whether a skill is growing, fading, or sporadic |
| Configurable scoring thresholds | Lets advanced users tune health rules |
| Report export | Produces local Markdown or JSON summaries |
| Improved hook enrichment | Adds better downstream toolchain metrics without storing sensitive payloads |
| Better filtering | Helps users focus by status, time window, source, or usage pattern |

### Constraints

Phase 2 should not require a cloud service. Similarity detection and reports should be possible locally by default.

## Phase 3: Optional intelligent assistance

Phase 3 can add intelligent review support after the metrics and rules are trusted.

### Candidate features

| Feature | Value |
| --- | --- |
| Skill reviewer | Explains why a skill may be broad, stale, or low value |
| Description rewrite suggestions | Helps users improve `description` or `when_to_use` text |
| Split suggestions | Suggests how to divide a broad skill into narrower skills |
| Merge suggestions | Suggests how to combine overlapping skills |
| Cleanup planning | Helps users plan manual cleanup without directly changing files |

### Guardrails

Any intelligent assistance should:

- Be optional
- Explain its reasoning
- Avoid automatic edits by default
- Respect local privacy expectations
- Clearly distinguish model-generated suggestions from measured metrics

## Possible release milestones

| Milestone | Goal |
| --- | --- |
| `v0.1` | Documentation package and product specification |
| `v0.2` | Sample data, local database schema, and aggregation prototype |
| `v0.3` | Overview and Skill Table pages |
| `v0.4` | Skill Detail page and health scoring |
| `v0.5` | Local collection setup around `claude_code.skill_activated` |
| `v1.0` | Stable local MVP with documentation, privacy guarantees, and sample data |

Version numbers are planning markers. Actual releases should be adjusted based on implementation progress and user feedback.

## Open product questions

These questions should be answered during or after Phase 1:

- How hard is local collection setup for a new user?
- Do users understand `failure_proxy_rate` without extra explanation?
- Are the default health scoring thresholds too strict or too lenient?
- Do users prefer a simple dashboard or more detailed analytical views?
- Is similarity detection important enough for Phase 2?
- Should exports be Markdown-first, JSON-first, or both?
- Should configuration be project-local, user-global, or support both?

## Contribution opportunities

Early contributors can help with:

- Validating the data model
- Testing local installation flows
- Designing sample data
- Improving empty and error states
- Reviewing health scoring rules
- Building dashboard pages
- Documenting supported event sources
- Testing privacy and data deletion behavior

## Long-term direction

The long-term direction is a local skill maintenance workbench: a tool that helps users keep their skill library small, useful, and understandable.

The project should remain focused on personal skill health. It may grow richer, but it should not drift into a cloud telemetry platform or team surveillance tool.

