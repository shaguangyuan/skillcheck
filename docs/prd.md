# Skill Health Dashboard MVP PRD

_Product requirements for the first local-first release of Skill Health Dashboard._

---

## Product definition

Skill Health Dashboard is a local-first open source tool that helps individual users understand how their agent skills are used and decide which skills should be kept, reviewed, merged, split, or retired.

The MVP is centered on local visibility rather than automation. It should collect available local skill activation data, aggregate it into understandable metrics, and present a dashboard that helps users make better maintenance decisions about their skill pool.

The statistical core should be built around the officially available `claude_code.skill_activated` event. Optional plugin integration may support installation and collection setup. Hooks may supplement the activation event with downstream toolchain behavior after a skill is triggered.

## Goals and non-goals

### Goals

- Help users see which skills are active, inactive, or questionable
- Make skill usage trends visible over time
- Provide transparent health scoring and status classification
- Support local-only storage and offline dashboard use
- Keep the MVP small enough to install, understand, and trust

### Non-goals

- Provide cloud accounts or hosted analytics
- Aggregate data across multiple users
- Automatically rewrite, delete, or refactor skills
- Automatically submit pull requests
- Provide enterprise policy or team administration features
- Build a complex AI diagnostic agent in the MVP

## Target users

### Core users

- Individual developers using Claude Code or agent skills
- Advanced users who maintain a personal skill library
- Users who want evidence before deleting, merging, or splitting skills
- Users who prefer local developer tools over remote telemetry products

### Non-core users

- Team administrators
- Enterprise IT departments
- Managers needing cross-user analytics
- Organizations needing centralized compliance reporting

## User problems

The MVP should address these user problems:

- Users have many skills but do not know which ones are actually used
- Users suspect some skills are too broad, too heavy, or redundant
- Users lack evidence for deciding whether to merge, split, delete, or rewrite skills
- Users do not have a long-term view of skill activation trends
- Users want local insight without sending usage data to a third party

## Product assumptions

- Users will install a local tool if it helps them maintain their skills
- Users value simple, actionable status labels more than complex analytics
- A standalone local dashboard is acceptable for an MVP
- Rule-based health scoring is sufficient before adding intelligent assistance
- Local privacy is a product requirement, not a later enhancement

## MVP user journeys

### Journey 1: View skill health overview

The user opens the dashboard and sees a summary of recent skill activity.

The overview should answer:

- How many skills were active in the last 30 days?
- How many known skills had zero activations in the last 30 days?
- Which skills are most frequently activated?
- How many skills are flagged as needing review?
- How many skills are candidates to merge or retire?

### Journey 2: Inspect a single skill

The user selects a skill from the table and opens its detail page.

The detail page should answer:

- How often has this skill been activated?
- When was it last seen?
- Which sessions or sources activated it?
- What usually happens after activation?
- Does it show signs of low value, unclear boundaries, or possible redundancy?
- What should the user consider doing next?

### Journey 3: Clean up the skill pool

The user reviews skills classified as `Needs Review` or `Candidate to Merge/Retire`.

The dashboard should help the user decide whether to:

- Keep the skill unchanged
- Rewrite its description or trigger guidance
- Split it into smaller skills
- Merge it with another skill
- Retire or delete it manually

## MVP scope

### Required capabilities

| Capability | Requirement |
| --- | --- |
| Local event collection | Ingest local skill activation events centered on `claude_code.skill_activated` |
| Local storage | Persist raw and aggregated data locally |
| Overview page | Show high-level skill health and recent usage summary |
| Health scoring | Calculate transparent rule-based health scores |
| Status classification | Classify skills as `Healthy`, `Needs Review`, or `Candidate to Merge/Retire` |
| Example data | Provide demo data so the dashboard can be viewed before real collection is configured |
| Documentation | Explain installation, usage, privacy, data model, and roadmap |

### Planned next pages

| Capability | Requirement |
| --- | --- |
| Skill table page | Let users compare skills by metrics and status |
| Skill detail page | Show per-skill trends, recency, downstream activity, and recommendations |

### Deferred capabilities

| Capability | Reason for deferral |
| --- | --- |
| Similar skill detection | Useful, but requires text analysis and stronger matching rules |
| Exportable health report | Valuable after the core dashboard is stable |
| AI-assisted rewrite suggestions | Should wait until rule-based diagnostics are trusted |
| Automated skill modifications | Too risky for MVP and outside the local insight goal |
| Multi-user dashboards | Conflicts with the initial personal local tool positioning |

## Pages and requirements

### Overview page

The Overview page is the landing page for the dashboard.

It should include:

| Element | Requirement |
| --- | --- |
| Active skills card | Count of skills with at least one activation in the selected time window |
| Inactive skills card | Count of known skills with zero activations in the selected time window |
| Review candidates card | Count of skills with `Needs Review` or `Candidate to Merge/Retire` status |
| Top skills list | Highest activation counts in the selected time window |
| Status distribution | Count of skills by health status |
| Recent activity trend | Daily activation trend for the selected time window |
| Empty state | Clear message when no events or sample data are available |

Default time window: 30 days.

### Skill table page

The Skill Table page is planned for the next page slice after the runnable Overview vertical slice.

It will be the primary comparison view.

It should include one row per known skill and support sorting or filtering by:

- Skill name
- Activation count
- Unique sessions
- Last seen
- Average tool depth
- Failure proxy rate
- Health score
- Status

The table should make review candidates easy to find without requiring the user to understand every metric.

### Skill detail page

The Skill Detail page is planned for the next page slice after the runnable Overview vertical slice.

It should provide context for one skill.

It should include:

| Section | Requirement |
| --- | --- |
| Summary | Skill name, status, health score, last seen, activation count |
| Trend | Daily or weekly activation trend |
| Usage context | Sessions, sources, or invocation context when available |
| Toolchain behavior | Average downstream tool depth after activation |
| Diagnosis | Rule-based reasons for current status |
| Suggested next action | Human-readable recommendation such as keep, review trigger guidance, split, merge, or retire |

The page must avoid presenting recommendations as automatic truth. It should phrase them as review prompts.

## Metrics

| Metric | Definition |
| --- | --- |
| `activation_count` | Number of observed skill activation events in a selected time window |
| `unique_sessions` | Number of distinct sessions containing at least one activation for the skill |
| `last_seen` | Most recent timestamp for an observed skill activation |
| `avg_tool_depth` | Average number of downstream tool actions observed after activation |
| `failure_proxy_rate` | Approximate rate of activations with weak downstream value signals |
| `health_score` | Rule-based score summarizing skill health |
| `status` | Label derived from health score and diagnostic rules |

## Health status rules

### Healthy

A skill may be classified as `Healthy` when it shows:

- Stable or repeated use in the selected time window
- Meaningful downstream activity after activation
- Low failure proxy rate
- No obvious signals of redundancy or unclear value

### Needs Review

A skill may be classified as `Needs Review` when it shows:

- Some usage, but inconsistent activation patterns
- Low or unclear downstream activity
- Possible mismatch between activation and useful work
- Broad or ambiguous behavior suggested by metrics
- Early warning signs but insufficient evidence for retirement

### Candidate to Merge/Retire

A skill may be classified as `Candidate to Merge/Retire` when it shows:

- Long-term low or zero usage
- Low activation value when triggered
- High likely overlap with other skills
- Maintenance cost that may exceed observed value
- Repeated weak downstream activity after activation

## Empty states and errors

### First-run empty state

When no data exists, the dashboard should explain:

- No local events have been collected yet
- The user can load sample data
- The user can configure local collection
- No data has been uploaded

### Collection unavailable state

When event collection is not configured or unavailable, the dashboard should show:

- What data source is missing
- Whether sample data is available
- Where to find setup instructions

### Calculation error state

When aggregation or scoring fails, the dashboard should show:

- A concise error message
- The affected time window or skill when available
- A pointer to local logs or troubleshooting documentation

## Privacy requirements

The MVP must follow these privacy requirements:

- Store data locally by default
- Avoid uploading event data
- Avoid requiring a user account
- Make collected event types visible to the user
- Allow local data deletion
- Work without a remote server after installation

## Success criteria

The MVP is successful when:

- A new user can install and launch the local dashboard from documentation
- The dashboard can display sample data
- The dashboard can show at least one real skill with valid statistics when collection is configured
- Users can understand the three status categories
- Users can identify at least one skill worth reviewing, merging, splitting, or retiring
- The product remains usable without cloud sync or a remote backend

## Acceptance checklist

- [ ] Local event collection can run
- [ ] Local database initialization can run
- [ ] Dashboard can launch locally
- [ ] Overview page shows summary metrics
- [ ] Skill Table page is delivered as the next page slice
- [ ] Skill Detail page is delivered as the next page slice
- [ ] Sample data can populate the dashboard
- [ ] Empty states are understandable
- [ ] Error states point to useful next steps
- [ ] Privacy documentation states what is and is not collected
- [ ] Installation documentation is sufficient for a new user

## Future roadmap hooks

The MVP should leave room for:

- Similarity detection between skills
- More detailed trend analysis
- Exportable local reports
- Optional intelligent skill review
- Description and trigger guidance suggestions
- Manual workflow support for splitting or merging skills
