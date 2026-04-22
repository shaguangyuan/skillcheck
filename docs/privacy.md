# Skill Health Dashboard Privacy and Local Data

_Privacy model and local data handling policy for Skill Health Dashboard._

---

## Privacy promise

Skill Health Dashboard is designed as a local-first tool. By default, it should run on the user's machine, store data locally, and avoid uploading skill usage data to any remote service.

The product exists to help users inspect their own skill usage. It is not a telemetry platform, a team monitoring system, or a cloud analytics product.

## Default behavior

By default, Skill Health Dashboard should:

- Store event data on the user's local machine
- Use a local database for raw and aggregated metrics
- Work without a user account
- Work without a remote backend
- Avoid sending skill usage data over the network
- Make collected event types visible to the user
- Allow users to delete local dashboard data

## Data collected

The MVP should collect only the data needed to calculate skill usage and health metrics.

| Data | Purpose |
| --- | --- |
| Skill activation event | Count when a skill is triggered |
| Skill name or identifier | Group events by skill |
| Event timestamp | Calculate recency and trends |
| Local session identifier when available | Calculate unique session usage |
| Event source | Distinguish official events, sample data, imports, plugins, or hooks |
| Downstream tool depth when available | Estimate whether activation led to practical work |
| Failure proxy signal when available | Estimate weak or unsuccessful activation outcomes |

The statistical core should be based on trustworthy local activation signals from supported agent platforms.

Current MVP optional importer behavior:

- Reads local history sources from supported platforms (currently Codex: `~/.codex/sessions/**/*.jsonl`, `~/.codex/logs_2.sqlite`)
- Uses local `SKILL.md` file load actions as a conservative activation proxy
- Extracts only skill id/name, skill path, timestamp, session id, and local raw reference

## Data not collected by default

Skill Health Dashboard should not collect the following by default:

- Full conversation transcripts
- User prompts
- Model responses
- Source code contents
- File contents edited by the user or agent
- Secrets, tokens, credentials, or environment variables
- Cross-user identity data
- Team analytics data
- Remote telemetry
- Prompt and response full text from imported local sessions

If a future feature needs additional data, it should be opt-in and documented before collection.

## Local storage

The MVP should store local data in a user-visible location.

Recommended default paths:

| Path | Purpose |
| --- | --- |
| `~/.skillcheck/skillcheck.sqlite` | Local SQLite database |
| `~/.skillcheck/config.toml` | Local configuration |
| `~/.skillcheck/logs/` | Local logs |
| `~/.skillcheck/exports/` | Optional local exports |

All paths should be configurable. Users should be able to inspect, back up, or delete these files directly.

## Sample data

Sample data should be synthetic and clearly labeled.

Sample data must:

- Avoid real user activity
- Avoid real prompts or code
- Be visibly marked in the dashboard
- Be removable without affecting real local data
- Include enough examples to demonstrate all health statuses

The dashboard should clearly distinguish sample data from real local activity.

## Plugin and hook boundaries

Skill Health Dashboard may optionally use plugins and hooks, but they should have narrow responsibilities.

| Layer | Appropriate role |
| --- | --- |
| Plugin | Installation, setup, configuration, and collection onboarding |
| Hook | Supplementary downstream behavior after a skill is activated |
| Collector | Local ingestion and normalization |
| Dashboard | Local display and diagnosis |

Plugins and hooks should not expand data collection silently. Any optional hook-derived signals should be documented and visible in configuration.

## Downstream behavior data

Hook-derived downstream behavior should be limited to lightweight metadata needed for health scoring.

Acceptable MVP examples:

- Number of tool calls after skill activation
- Whether a nearby tool call failed
- Whether downstream tool activity was observed
- Local timing metadata within a bounded follow-up window
- Local file-pointer references such as `path:line` for importer debugging

Avoid collecting:

- Full tool input payloads
- Full tool output payloads
- File contents
- Prompt or response text
- Secret values

`raw_event_ref` should remain a local pointer (for example `session-file-path:line-number`) and should not store full payload text.

The dashboard can calculate useful `avg_tool_depth` and `failure_proxy_rate` metrics without storing sensitive content.

## Network behavior

The default MVP should not require network access after installation.

Expected local behavior:

- Dashboard served on `localhost`
- SQLite database stored locally
- No account login required
- No remote sync enabled by default
- No analytics beacon enabled by default

If the project later adds optional update checks, extension downloads, or remote integrations, they should be documented as separate opt-in features.

## User control

Users should be able to:

- View what data sources are enabled
- View where local data is stored
- Disable optional hooks
- Clear sample data
- Delete local dashboard data
- Run the dashboard offline

Review the configured local database path and remove the local Skill Health database and related logs manually if you want to clear collected data. Do not delete user skill files.

## Data deletion scope

Deleting Skill Health Dashboard data should remove:

- Local dashboard database
- Local sample data
- Local dashboard logs if requested
- Generated local reports if requested

Deleting Skill Health Dashboard data should not remove:

- User skill files
- Claude Code configuration unrelated to the dashboard
- Git repositories
- Remote data
- Local files created by other tools

## Privacy risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Event metadata accidentally includes sensitive context | Keep optional fields conservative and avoid storing raw payloads by default |
| Hook collection grows too broad | Make hooks optional, documented, and configurable |
| Sample data is confused with real data | Clearly label sample mode and provide a clear sample data removal command |
| Users misunderstand health labels as automatic judgment | Explain that statuses are review prompts |
| Local logs contain unnecessary details | Keep logs minimal and avoid storing tool payloads |
| Future integrations introduce network behavior | Require explicit opt-in and separate documentation |

## Security expectations

The MVP is a local developer tool, not a security boundary. Users should still protect their local machine and avoid placing the database in shared or public folders.

Recommended expectations:

- Store local data in a user-owned directory
- Avoid world-readable database permissions where possible
- Avoid logging secrets or payloads
- Treat exports as user-controlled local files
- Document any future network-capable features clearly

## Transparency checklist

Before a public MVP release, the project should clearly document:

- [ ] What event sources are used
- [ ] What fields are stored locally
- [ ] Where the local database is stored
- [ ] How sample data differs from real data
- [ ] How to disable optional hooks
- [ ] How to delete local data
- [ ] Whether any feature contacts the network
- [ ] What is explicitly not collected
