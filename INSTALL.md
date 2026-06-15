# Installing the PM plugin

Version: **2.1.3** (plugin slug: `pm-plugin`)

## What's in v2.1

Four skills, all user-invocable:

| Skill | What it does |
|---|---|
| `/meeting-sync` | Launches a live Cowork artifact that fetches Granola meetings, cross-references your JIRA board, and generates reviewable ticket proposals + a Slack summary. The artifact drives JIRA writes and the Slack post directly — no local server. The artifact runs its own onboarding on first launch, so there's nothing to configure in Claude Code first. |
| `/pm-feedback` | Files feedback about any plugin skill into the Feedback table on the PM Skills Plugin Hub (Coda). Auto-captures the task, input, and output from conversation context. Self-bootstraps a minimal profile if none exists. |
| `/pm-automations` | Interview-driven builder for recurring scheduled agents. Optionally scans your connected MCPs (Granola meetings, JIRA boards, Slack channels, Coda docs) to suggest automations, then creates them via the Scheduled Tasks MCP. Self-bootstraps a minimal profile if none exists. |
| `/canvas-updates-builder` | Guided setup wizard for weekly Slack Canvas update pipelines. Produces two scheduled tasks per pipeline — a draft task and a publish task. Invoke with the slash command, or trigger by saying "build a weekly update skill". |

## Prerequisites

- **Claude Code** with the plugin system and Cowork enabled.
- At least one of these MCPs connected (more = more features):
  - **Cowork** — launch pad for the Meeting Sync artifact. Required for `/meeting-sync`.
  - **Granola** — meeting notes source. Required for `/meeting-sync` and most automation templates.
  - **JIRA** (via Zapier MCP) — ticket read/write. Required for `/meeting-sync`.
  - **Slack** (via Zapier MCP) — posting, canvas building, channel resolution. Required for `/canvas-updates-builder`; optional elsewhere.
  - **Coda** — `/pm-feedback` routing. Required for the feedback loop.
  - **Scheduled Tasks** (built into Claude Code) — required for `/pm-automations` and `/canvas-updates-builder`.

No Node, no local server, no port reservations, no explicit setup skill to run first.

## Steps

### 1. Install through Claude Code's plugin manager

Install this plugin via the Claude Code plugin interface (drag-and-drop the zip, or use your org's marketplace). The plugin manager reads `.claude-plugin/plugin.json` and places the plugin under `~/.claude/plugins/`.

### 2. Restart Claude Code

So it picks up the new skill definitions.

### 3. Pick a skill

Everything self-configures on first run — no separate onboarding step:

- `/meeting-sync` — turn meetings into JIRA actions via the Cowork artifact. The artifact asks for your JIRA project and Slack channel the first time it runs, then persists that inside Cowork.
- `/pm-automations` — build recurring scheduled agents through a guided interview. Writes a minimal `~/.claude/profile.json` silently if one doesn't exist.
- `/pm-feedback` — file feedback whenever something's off. Also self-bootstraps the profile on first run, pulling your email silently from the Coda MCP if available.
- `/canvas-updates-builder` — guided setup for weekly Slack Canvas update pipelines. Also triggers on natural-language phrases like "build a weekly update skill".

---

## What's new in 2.1.3

- **Meeting Sync: portability fix done right.** 2.1.0 hardcoded the plugin author's MCP UUIDs into the artifact; 2.1.1 and 2.1.2 tried to make the artifact resolve UUIDs from inside Cowork at runtime, but the introspection paths we relied on (`mcp__cowork__read_widget_context`, `window.cowork.tools`) don't return what we need on current Cowork builds. 2.1.3 puts substitution back in the right place — the `/meeting-sync` skill detects the running user's Granola/Zapier/Slack UUIDs from Claude Code's tool list and rewrites the bundled artifact's sentinel tokens (both manifest and JS call sites) before pushing to Cowork. Each user's push produces a personalized artifact; the plugin itself ships portable.
- **Meeting Sync: "Analyze Selected" button no longer stays disabled.** The selection screen now auto-picks the first saved JIRA board if none is selected on entry (which is what happens on first launch when `CONFIG.savedBoards` was empty at state-init time). The `updateSelectionCounts` function now logs `selected=N, board=KEY, disabled=true/false` to the debug panel, so selection-related issues are diagnosable from one line.
- **PM Feedback: removed the form-style UI.** `/pm-feedback` no longer calls `AskUserQuestion`, which was rendering a skill picker + two text fields as a structured form. The skill is now conversational: it infers the skill, task, input, output, and issue from the conversation, drafts the full feedback entry, and shows it in one short message for a "send / edit / no" confirm. The Coda write logic (column ID resolution, row format) is unchanged. The skill now also auto-offers proactively when the user sounds dissatisfied or when a bug got fixed mid-conversation.

## What was new in 2.1.2

- **Meeting Sync resolver now uses Cowork's introspection API.** 2.1.1 tried to address connectors by canonical name (`mcp__Granola__list_meetings`) first, and only fell back to the host tool list if that didn't work. In practice Cowork's `callMcpTool` requires the user's per-install server UUID, and the `window.cowork.tools` fallback isn't populated inside artifacts — so 2.1.1 still failed silently on most installs. 2.1.2 calls `mcp__cowork__read_widget_context` once at first use, extracts the granted tool list, resolves each sentinel (`MCP_GRANOLA`, `MCP_ZAPIER`, `MCP_SLACK`) to the user's actual UUID prefix by tool-name suffix, and caches the result. If a connector isn't connected, the artifact surfaces a clear "open Claude → Settings → Connectors, add X" message instead of failing silently.
- **Slack vs. Zapier disambiguation hardened.** The resolver uses an anchored suffix match on `__slack_send_message` so Zapier's `slack_send_channel_message` / `slack_send_direct_message` no longer accidentally claim the Slack sentinel.

## What was new in 2.1.1

- **Meeting Sync artifact is now portable across installs.** Previously the bundled `artifact.html` had this user's per-installation MCP server UUIDs (Granola, Zapier, Slack) hard-coded in 20 places, so when anyone else opened it in their Cowork canvas every tool call resolved to nothing. The artifact now declares tools using canonical Anthropic connector names (`mcp__Granola__*`, `mcp__Zapier__*`, `mcp__Slack__*`) and resolves the real per-user prefix at load time inside its own `callMcpTool` — name-form first, then host-tool introspection by suffix, then candidate-walk on tool-not-found. Push the same bytes to any user's Cowork; it just works as long as they have Granola, Zapier (for Jira), and Slack connected.
- **`/meeting-sync` no longer pre-flights MCP connections.** That logic moved into the artifact, where it can actually see what Cowork has granted. The skill just reads `artifact.html` verbatim and pushes it via `mcp__cowork__update_artifact`.

## What was new in 2.1

- **Removed `/pm-setup`.** The skill was vestigial — `/meeting-sync` now runs entirely inside a Cowork artifact that manages its own config, `/canvas-updates-builder` re-collects everything fresh each run, and the two remaining skills that need a profile (`/pm-feedback` and `/pm-automations`) self-bootstrap one silently on first run.
- **Renamed `slack-canvas-updates-builder` → `canvas-updates-builder`.** Now a proper slash command (`/canvas-updates-builder`) like the other skills, not a natural-language-only trigger. Natural-language triggers still work.
- **Scheduled tasks no longer notify on completion.** Both `/pm-automations` and `/canvas-updates-builder` now pass `notifyOnCompletion: false` on every `create_scheduled_task` call. The Claude Code completion banner was noisy and unreliable; real notifications come through Slack/Coda/JIRA where the user is already watching.

## What was new in 2.0

- **Meeting Sync moved to a Cowork artifact.** No local dashboard server, no `launch.json` to patch, no `npm install`, no port 3850. The skill pushes `artifact.html` into the user's Cowork canvas, and the artifact owns all downstream MCP calls.
- **New skill: `/pm-automations`** — interview-driven builder for recurring scheduled agents.
- **New skill** (originally `slack-canvas-updates-builder`, renamed in 2.1) — guided setup for weekly Slack Canvas update pipelines.
- **Deletions** from 1.x: the `dashboard/` folder, `.claude/launch.json`, and the root-level bridge files (`proposals.json`, `claude-heartbeat.json`, `slack-triggered.json`).
- **Profile schema** extended with `plugins.pm-skills.automations.templates[]` for saved automation drafts.

## Troubleshooting

- **`/meeting-sync` says "Cowork required"** — run it inside a Claude Code environment that has the Cowork MCP enabled, or upgrade Claude Code.
- **Scheduled task didn't fire** — open `/pm-automations`, choose "List & manage my automations", confirm the task is enabled and the cron matches your local timezone. Claude Code must be running for scheduled tasks to execute.
- **Ticket titles aren't clickable in the artifact** — click the dashed ID badge to set your JIRA base URL (saves inside the artifact's own state; every ticket becomes a link).
- **`/pm-feedback` can't reach Coda** — the skill prints the row JSON so you have a record and falls back to a local append-only log at `~/.claude/pm-feedback-pending.json`.

## Security notes

- No API keys or tokens are stored anywhere in the plugin — everything routes through user-authenticated MCPs.
- Profile lives under `~/.claude/` — outside the project folder so it can't leak into git.
- Legacy activity-log fire-and-forget POSTs from v1 skill code paths silently no-op — the dashboard server that used to receive them is gone. No content is exfiltrated.
- Scheduled task prompts live in Claude Code's local scheduled-tasks store (`~/.claude/scheduled-tasks/`) — never committed to the plugin.

See `PROFILE_SCHEMA.md` for the shared profile format and the **How it works** page in the Coda hub for the architecture.
