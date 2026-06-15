---
name: pm-automations
user_invocable: true
description: "Guided builder for recurring PM automations. Interviews you with AskUserQuestion, optionally scans your Granola/JIRA/Slack/Coda connectors for ideas, then creates scheduled agents via the scheduled-tasks MCP — meeting-notes sync, channel-to-Coda sync, Friday canvas drafts, agenda prep, or fully custom. Also lists, pauses, updates, or deletes your existing automations."
---

# PM Automations

> **Run**: `/pm-automations`
> **Time**: 2–6 minutes per automation
> **Writes to**: `scheduled-tasks` MCP (source of truth for created tasks), `~/.claude/profile.json` (saved templates only)

## Purpose

PMs accumulate recurring chores — sync this meeting's notes to that Coda page, pull new tickets from that board into that tracker, draft a weekly update every Friday at 3 PM. This skill interviews the PM, drafts the agent prompt, and creates the scheduled task. It also manages the ones already installed.

Never hard-codes names, channels, or boards — everything is discovered from the user's profile and connected MCPs or asked during the interview.

---

## Phase 0: Load profile + preflight

Read `~/.claude/profile.json`.

- **Profile missing or empty**: write a minimal skeleton silently (`schemaVersion: 1`, `core.user.role: "PM"`, `core.user.timezone: "America/Phoenix"`, empty boards/channels arrays, canonical Coda hub URIs, empty `automations.templates`). Continue — the interview will gather anything the composed prompt needs. Do not mention the bootstrap to the user; this is a transparent self-heal. There is no `/pm-setup` skill.
- **scheduled-tasks MCP not connected**: stop and tell the user. This skill cannot function without it. Suggested message: *"I need the scheduled-tasks MCP to create automations. Enable it in your Claude Code MCP settings, then re-run `/pm-automations`."*
- **Other MCPs (Granola, Zapier, Slack, Coda, Google Drive)**: probe lazily — only when a phase actually needs them. Degrade gracefully.

Cache into memory for this session: `core.user.timezone`, `plugins.pm-skills.jira.boards`, `plugins.pm-skills.slack.channels`, `plugins.pm-skills.coda.hubDocUri`.

---

## Phase 1: Intent

Single **AskUserQuestion** — what do you want to do?

| Option | Label | Next |
|---|---|---|
| A | Create a new automation | Phase 2 |
| B | Suggest automations from my work | Phase 3 |
| C | List & manage my automations | Phase 6 |
| D | I'm done | exit |

Route to the matching phase. Do not proceed to interview until this is answered.

---

## Phase 2: Template picker

**AskUserQuestion** (4 options max — respect the cap):

| Key | Template | What it does |
|---|---|---|
| `meeting-sync` | Meeting-notes sync | After each recurring Granola meeting, create/update a Coda subpage with the notes |
| `channel-to-coda` | Channel or board → Coda | Daily: pull new items (Slack messages with a keyword, JIRA issues matching a JQL) into a Coda table |
| `weekly-canvas` | Weekly Slack canvas draft | Friday afternoon: gather context, draft a weekly update canvas, DM the user to review |
| `agenda-prep` | Agenda prep | Before a recurring meeting, draft a time-boxed agenda and DM it |
| `custom` | Custom — describe in chat | Free-form; go to Phase 4 with no prefilled template |

Store the picked template key — Phase 4 uses it to choose which follow-ups to ask and Phase 5 uses it to seed the prompt.

---

## Phase 3: Optional MCP scan (suggest mode)

Only run if the user picked option B in Phase 1, or explicitly asks for suggestions.

**AskUserQuestion** — which sources can I scan? (multi-select up to 4):

- Granola (recent recurring meetings)
- JIRA (boards from your profile)
- Slack (channels from your profile)
- Coda (your docs)

Run the scans the user opted into. Each scan is best-effort; on MCP error, skip that source and note it. Log one `mcp_scan_offered` before running, one `mcp_scan_completed` after.

### Granola

`mcp__1440c8b2-51d3-4f4c-82f6-470fd1d99431__list_meetings` → cluster by title. Recurring titles (≥ 2 occurrences in the last 30 days) are the candidates. Examples to surface: *"You have a weekly 'Success Center' meeting — sync its notes to Coda after each run?"*

### JIRA

For each board in `plugins.pm-skills.jira.boards`, run `mcp__b0cecf87-6ef8-477a-9c32-42aba87e5138__jira_software_cloud_find_issues_via_jql` with a narrow recent-update JQL. Surface: *"Your EPAITF board has 7 new SFTF-labeled issues this week — sync them into a Coda Action Item Tracker daily?"*

### Slack

For each channel in `plugins.pm-skills.slack.channels`, call `mcp__b0cecf87-6ef8-477a-9c32-42aba87e5138__slack_get_conversation` (small limit) to confirm activity. Surface: *"`#prepcallsummary-beta` had 14 new messages this week — sync feedback into a Coda action-items table?"*

### Coda

`mcp__Coda__search` for the user's docs. Use to help with destination suggestions in Phase 4 — not to generate automations on its own.

### Present

Up to 5 concrete suggestions as a short list. For each, include the template type and the prefilled fields you'd propose. End with:

> "Pick one to create (or say 'none' to go back)."

On selection, drop the user into Phase 4 with those fields prefilled.

---

## Phase 4: Interview

Ask in small batches — **each AskUserQuestion may have up to 4 options**, so split long choice lists across multiple questions. Skip any field the template doesn't need or that's already filled from Phase 3.

### Common questions (most templates)

1. **Name** — free-text. Kebab-case it for the `taskId`. Example: `agentforce-standup-notes`.
2. **Schedule** — AskUserQuestion:
   - Daily at a time I'll pick
   - Weekly on a day I'll pick
   - After each occurrence of a specific meeting (Granola-triggered variants still need a recurring cron — ask user for the meeting's usual time + a buffer)
   - Custom cron
   Follow up for the specific time/day/cron as needed. Store as a 5-field cron in **local time**; the MCP evaluates cron in the user's timezone.
3. **Destination** — depends on template:
   - Coda: paste page URL or search via `mcp__Coda__search`
   - Slack: pick from profile channels or paste channel ID / `#name` / URL
   - DM-me: use the email on the profile (`core.user.email`) via `slack_find_user_by_email`
4. **Source** — depends on template:
   - Meeting-sync: meeting title (confirm match via `list_meetings` if Granola is connected)
   - Channel-to-Coda: Slack channel or JIRA JQL / board + label
   - Weekly canvas: list of sources to gather from (multi-select up to 4: Granola meetings by title, Slack channels, JIRA boards)
   - Agenda prep: meeting title + how far ahead (e.g., 2 days before at 9:05 AM)

### Validate before Phase 5

- Name sanitized to kebab-case, under 60 chars
- Cron is a valid 5-field expression
- Every URL/ID the user pasted resolves (Coda URL via `mcp__Coda__url_convert`, Slack channel via `slack_get_conversation`, JIRA project via `jira_software_cloud_find_project`). If a check fails, ask one targeted follow-up — don't ask the whole batch again.

Cap: if the interview balloons past ~8 questions total, stop and suggest the `custom` template with a free-text brief instead.

---

## Phase 5: Compose prompt + create

### Compose the agent prompt

Write a concrete natural-language instruction the scheduled agent will run on every fire. It must cover:

- **Trigger context** — "This task runs daily at 8 AM." or "This runs 2 days before each Bi-Weekly Guru Evolution Check-In."
- **Data to pull** — specific MCP calls (e.g., `list_meetings` filtered by title, or a JQL string) with concrete arguments.
- **Transformation** — what to extract, how to structure it (bullets, table rows, a canvas outline).
- **Destination write** — the exact Coda page URI / Slack channel ID / user DM target, and the write tool (e.g., `mcp__Coda__page_create` under parent `<uri>`, or `mcp__b0cecf87-6ef8-477a-9c32-42aba87e5138__slack_create_canvas`).
- **Idempotency note** — avoid duplicate writes; use date-stamped subpage titles or an upsert pattern keyed on a natural ID.
- **Failure behavior** — on MCP error, DM the user a short note rather than silently failing.

Keep the prompt tight. Reference profile fields by value (resolve now), not by path — the scheduled session won't load this skill's context.

### Show and confirm

Print the composed prompt in a fenced block, plus a summary table:

| Field | Value |
|---|---|
| taskId | `{kebab}` |
| description | one line |
| schedule | human + cron |
| template | `{key}` |

**AskUserQuestion**: "Create this now, edit the prompt, or cancel?" Three options.

### Create

On confirm, call `mcp__scheduled-tasks__create_scheduled_task`:

- `taskId` — kebab-cased name
- `description` — one-line summary for the sidebar
- `prompt` — the composed prompt above
- `cronExpression` — local-time 5-field cron (recurring)
- `fireAt` — ISO 8601 with offset (one-time only; mutually exclusive with cron)
- `notifyOnCompletion` — **always pass `false`**. Completion notifications from Claude Code aren't useful for these automations (they fire silently in the background and their output lands in Slack/Coda/JIRA where the user will see it anyway). Do not prompt the user about this — just set `false` on every create call.

Report back:

```
Created: {taskId}
Next run: {nextRunAt}
Manage with /pm-automations → List & manage.
```

---

## Phase 6: Manage existing

Call `mcp__scheduled-tasks__list_scheduled_tasks`. Render as a table:

| # | taskId | Schedule | Enabled | Next run | Last run |
|---|---|---|---|---|---|

**AskUserQuestion**: "What would you like to do?" (up to 4 options):

- Pause / resume one
- Change the schedule
- Edit the prompt
- Delete one

For each, ask which `taskId` (free-text; validate against the list). Then call `mcp__scheduled-tasks__update_scheduled_task` with the matching fields:

- Pause → `enabled: false` (resume → `true`)
- Change schedule → `cronExpression` or `fireAt`
- Edit prompt → `prompt` (show current, ask for replacement)
- Delete → the MCP does not expose delete via the three tools loaded here; offer pause-and-rename instead, and tell the user the task folder lives at `~/.claude/scheduled-tasks/{taskId}/` if they want to remove it manually.

Confirm each action with a short AskUserQuestion before firing. Log `automation_updated` or `automation_deleted` as appropriate.

---

## Activity log

Fire-and-forget POST to `http://localhost:3850/api/log` after each meaningful step. Skip silently if the dashboard server isn't running.

```json
{
  "actor": "claude",
  "skill": "pm-automations",
  "event": "automation_created",
  "summary": "Created agentforce-standup-notes",
  "meta": {
    "taskId": "agentforce-standup-notes",
    "taskIdHash": "<first 8 hex chars of sha256>",
    "template": "meeting-sync",
    "schedule": "0 9 * * 1-5",
    "hasGranolaSource": true,
    "hasCodaDestination": true,
    "promptLen": 1482
  }
}
```

Events to emit: `automation_created`, `automation_updated`, `automation_deleted`, `mcp_scan_offered`, `mcp_scan_completed`. Never log prompt text, meeting titles, channel names, Coda URLs, or any PII — counts, template keys, cron strings, booleans, and the `taskIdHash` only.

---

## Error handling

- **scheduled-tasks MCP not connected** — hard-stop with a clear fix-it message; do not continue into the interview.
- **Granola / JIRA / Slack / Coda MCP missing** — scan phase skips that source, interview falls back to free-text. Note the degradation once; don't nag.
- **Cron or ISO timestamp invalid** — re-ask that single field; don't restart the interview.
- **Resolution failure on a URL/ID** — one targeted follow-up; on second failure accept as-is and note the risk in the confirmation summary.
- **User says "cancel"** at confirmation — do not create the task; offer to save the draft as a template in `plugins.pm-skills.automations.templates` (Phase 4 answers only, no secrets).

---

## Sharability — MCPs required

| Tier | MCP | Used for |
|---|---|---|
| Hard | `scheduled-tasks` | Create / list / update automations |
| Optional | Granola (`1440c8b2-…`) | Scan recurring meetings; meeting-title triggers |
| Optional | Zapier (`b0cecf87-…`) | JIRA JQL scans, Slack channel posts, Slack canvases |
| Optional | Coda | Destination page creation + search |
| Optional | Google Drive (`7f076ffb-…`) | Alternate destination for doc-based writes |

Any PM can install this skill. The interview adapts to whatever's connected — each missing optional MCP just removes one template pathway, never blocks the skill.

---

## Example composed prompts (reference only — do not hard-code)

**Meeting-sync template** (seed — resolve URIs/titles at interview time):

> Runs daily at 9 AM local. Use `list_meetings` to find meetings from the last 24 hours titled `{meetingTitle}`. For each, create a Coda subpage under `{codaParentUri}` titled `{meetingTitle} — {YYYY-MM-DD}` with the meeting summary and action items. Skip if a page with the same title already exists. On failure, DM `{userEmail}` with a short error.

**Weekly canvas template** (seed):

> Runs Friday 3 PM local. Gather: last week's `{meetingTitles[]}` from Granola, recent messages in `{slackChannels[]}`, and updated issues in `{jiraBoards[]}`. Draft a weekly update in the brand voice (see profile). Create a Slack canvas in `{draftChannelId}` titled `Weekly Update — {YYYY-MM-DD}`, then DM `{userEmail}` with the canvas link and ask for review.

Use these as shape references when composing the real prompt; never ship them unedited.
