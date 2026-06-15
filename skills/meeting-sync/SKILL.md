---
name: meeting-sync
description: "Launch a live Cowork artifact that turns recent Granola meetings into reviewable JIRA ticket proposals and a Slack summary. The artifact runs in the user's Cowork canvas — it fetches meetings, cross-references the JIRA board, generates update/new-ticket proposals, and lets the user submit to JIRA and post to Slack directly from the artifact UI. Requires Cowork plus MCP connections for Granola, JIRA (Zapier), and Slack."
user_invocable: true
---

# Meeting Sync

> **Run**: `/meeting-sync`
> **Time**: ~30 seconds to open the artifact; the user drives the rest
> **Pattern**: Ships a self-contained HTML artifact into the user's Cowork canvas. The artifact owns all MCP calls (Granola, JIRA, Slack) after launch.

## Purpose

Turns meeting discussions into JIRA actions without a local dashboard. This skill does **one** thing: load the user's profile, confirm Cowork is reachable, and push the bundled `artifact.html` into Cowork as a live artifact. Everything after that — meeting selection, board fetch, AI proposals, review, submit, Slack post — happens inside the artifact itself using MCP tools declared in its `cowork-artifact-meta` block.

There are no local files, no local dev server, and no polling loop. Claude's job ends once the artifact is live.

---

## Required MCPs

The artifact depends on the following MCPs being connected in the user's Claude Code environment. This list comes from the `cowork-artifact-meta` JSON block at the top of `artifact.html` — if the user updates the artifact, re-check that block for the source of truth.

| MCP server | Purpose | Tool examples |
|---|---|---|
| **cowork** | Host the live artifact | `mcp__cowork__update_artifact` |
| **Granola** | Pull recent meeting notes | `list_meetings`, `get_meetings` |
| **Zapier** (JIRA) | Read board state + write issues/comments | `jira_software_cloud_find_issues_via_jql`, `jira_software_cloud_add_comment_to_issue`, `jira_software_cloud_create_issue`, `jira_software_cloud_find_project` |
| **Slack** | Post the team summary | `slack_send_message`, `slack_search_channels` |

If any of these are missing, the artifact will surface the gap in its own UI — but Cowork itself must be present for this skill to run at all (that's the launch dependency).

---

## Phase 0: Load profile

Read `~/.claude/profile.json`.

- Use `plugins.pm-skills.jira.boards` and `plugins.pm-skills.slack.channels` if present.
- Read `core.user` and `core.brand` — the artifact picks these up via its own context when drafting comments and the Slack summary voice.
- If the profile is missing or schema < 1, fall back to `pm-config.json` at the plugin root (legacy).

If neither source has any boards or channels, that's fine — the Cowork artifact has its own in-canvas onboarding flow (it asks the user to pick a JIRA project and Slack channel the first time it runs, and persists them in both `localStorage` and its own artifact tag). Hand off to the artifact anyway; it'll self-configure.

This phase is light; the artifact does its own config read once it loads. The Claude-side profile read is a hint, not a gate.

---

## Phase 1: Verify Cowork is available

Check whether any `mcp__cowork__*` tool is in the current tool list. In particular, confirm one of:

- `mcp__cowork__update_artifact` (preferred — updates in place if an artifact already exists, otherwise creates)
- `mcp__cowork__create_artifact` (fallback if `update_artifact` isn't exposed in this environment)

If neither is present, stop and tell the user:

> "This skill requires Cowork. Run it inside Claude Code's Cowork environment, or upgrade your Claude Code install to a version that ships the Cowork MCP."

Do not try to fall back to a local file or browser preview — the v2 pattern is Cowork-only.

---

## Phase 2: Push the artifact to Cowork

### Why this phase has work in it

The bundled `artifact.html` ships with **sentinel tokens** in place of MCP server UUIDs (`MCP_GRANOLA`, `MCP_ZAPIER`, `MCP_SLACK`), in both the `cowork-artifact-meta` manifest at the top of the file AND every `callMcpTool('mcp__MCP_*__...')` call site in the JS body. The artifact will not work as-is — Cowork's manifest parser grants tools by exact name match, and `callMcpTool` requires the user's actual `mcp__<uuid>__<tool>` form. We learned the hard way (2.1.0–2.1.2) that runtime resolution from inside the artifact is unreliable: `mcp__cowork__read_widget_context` returns widget state, not the granted tool list, and `window.cowork.tools` isn't populated. So substitution must happen here, before the push, where Claude can actually see the user's tool list.

### Step 1: Resolve the running user's MCP UUIDs

Inspect the current Claude Code tool list and find one tool from each of the three connectors. The probe tool for each sentinel is unique enough that a single match nails the prefix:

| Sentinel | Probe tool (exact suffix) | Why this probe |
|---|---|---|
| `MCP_GRANOLA` | a tool name ending in `__list_meetings` | Only Granola exposes this. |
| `MCP_ZAPIER` | a tool name ending in `__jira_software_cloud_find_project` | Only Zapier's Jira app exposes this. |
| `MCP_SLACK` | a tool name ending in **exactly** `__slack_send_message` (not `__slack_send_channel_message` or other variants) | Disambiguates the dedicated Slack connector from Zapier's Slack-named tools. |

For each sentinel, extract the prefix segment — i.e. given `mcp__<prefix>__<suffix>`, capture `<prefix>`. That's the user's per-install server identifier (typically a UUID). Use ToolSearch with the probe name to surface candidate tools if the schema isn't already loaded.

If any of the three connectors can't be found, **stop here**. Tell the user which one is missing and what to do, e.g.:

> "Granola isn't connected on your machine — open Claude → Settings → Connectors, add Granola, then re-run `/meeting-sync`."

Do not push a half-substituted artifact. Cowork will grant nothing for the missing connector and the artifact will appear to work but silently fail.

### Step 2: Substitute the sentinels in the artifact bytes

Read `{skill_dir}/artifact.html` and do three literal string replacements over the whole file (not just the manifest — the JS body needs them too):

- Every occurrence of `MCP_GRANOLA` → the Granola prefix you resolved
- Every occurrence of `MCP_ZAPIER`  → the Zapier prefix you resolved
- Every occurrence of `MCP_SLACK`   → the Slack prefix you resolved

Do **not** substitute `mcp__cowork__*` — `cowork` is a fixed server name, not a per-user UUID. Don't touch anything else in the file.

Sanity-check the result before pushing: it should contain zero remaining occurrences of `MCP_GRANOLA`, `MCP_ZAPIER`, or `MCP_SLACK`. If any survive, the substitution missed something and the push will produce a broken artifact.

### Step 3: Push to Cowork

Call `mcp__cowork__update_artifact`; fall back to `mcp__cowork__create_artifact` if the former isn't exposed.

Target parameter shape (names may vary slightly by Cowork version — consult the tool schema at call time):

```
mcp__cowork__update_artifact({
  title:   "Meeting Sync — {YYYY-MM-DD}",   // today's date in the user's locale
  content: <string: the substituted HTML body>,
  mime:    "text/html"                       // if the tool requires a content type
})
```

If the tool errors on unknown params, drop them and retry with just `title` + `content`. If `update_artifact` reports "no existing artifact to update", call `create_artifact` with the same args.

---

## Phase 3: Hand off to the user

Once Cowork confirms the artifact is live, tell the user — briefly:

> "Meeting Sync is live in your Cowork canvas. From here:
> 1. Pick the meetings you want to process (the artifact pulls them from Granola).
> 2. Review the ticket updates and new-ticket proposals — edit inline, toggle approvals.
> 3. Click **Submit to JIRA** to push comments and create issues.
> 4. Pick a Slack channel and hit **Send to Slack** to post the summary.
>
> I'll step back — the artifact talks to Granola, JIRA, and Slack directly. Ping me if you hit a snag."

That's it. No heartbeats, no polling. The artifact is the product.

---

## When the user seems unhappy

If the user says things like "that comment was wrong", "I didn't want that tone", "the summary missed the point", or "this artifact isn't doing what I need", offer:

> "Want me to file this as feedback so we improve the skill? I'll capture the context and drop it in the Plugin Feedback table on your hub."

If yes, invoke `/pm-feedback`. Don't nag — offer once per distinct complaint.

---

## Error handling

- **Cowork MCP absent** → see Phase 1: stop with a clear upgrade message.
- **`artifact.html` missing from the skill directory** → report a plugin install problem. Don't attempt to regenerate it.
- **Cowork `update_artifact` rejects the payload** → try `create_artifact`. If both fail, surface the raw error to the user and suggest reinstalling the plugin.
- **Everything downstream (Granola / JIRA / Slack)** → the artifact surfaces those errors in its own UI, including "connect the X MCP" prompts when a connector isn't reachable. Don't pre-empt them from the chat side.

---

## Sharability notes

Plug-and-play for anyone with:

1. Cowork (required — this is the launch surface)
2. Granola (meeting notes)
3. JIRA via Zapier MCP
4. Slack MCP (optional, but the summary step won't post without it)
5. Coda MCP (optional, for `/pm-feedback`)

New users just run `/meeting-sync` — the artifact handles its own onboarding on first launch. No local servers, no API keys, no file edits.
