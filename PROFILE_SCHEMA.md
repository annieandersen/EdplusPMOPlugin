# Shared User Profile Schema

**Location:** `~/.claude/profile.json`
**Purpose:** One shared file across PM-oriented Claude Code plugins so they read/write the same user facts (name, brand voice, board lists, channel lists, Coda hubs) without stomping each other.

## Shape

```json
{
  "schemaVersion": 1,
  "core": {
    "user": {
      "name": "Auryan Ratliff",
      "email": "apratlif@asu.edu",
      "role": "PM",
      "timezone": "America/Phoenix"
    },
    "brand": {
      "voice": "conversational, direct, practical",
      "tone": "friendly but not casual; assumes the reader is busy",
      "doNotUse": ["corporate jargon", "emojis in Slack"]
    },
    "preferences": {
      "defaultMeetingRange": "last_week"
    }
  },
  "plugins": {
    "pm-skills": {
      "jira": {
        "boards": [
          {
            "projectKey": "SPLT",
            "projectName": "EdPlus: Split Studio",
            "baseUrl": "https://asudev.jira.com",
            "jqlFilter": "project = SPLT AND status != Done AND updated >= -30d",
            "addedAt": "2026-04-19"
          }
        ]
      },
      "slack": {
        "channels": [
          { "id": "C0123456789", "name": "split-studio-updates", "type": "public", "addedAt": "2026-04-19", "webhookUrl": null }
        ]
      },
      "coda": {
        "hubDocUri": "coda://docs/Nh3S1m8BlQ",
        "feedbackTableUri": "coda://docs/Nh3S1m8BlQ/tables/..."
      },
      "automations": {
        "templates": [
          {
            "key": "agentforce-standup-notes",
            "template": "meeting-sync",
            "answers": {
              "meetingTitle": "EdPlus Agentforce Check-in",
              "codaParentUri": "coda://docs/…/pages/…",
              "cron": "0 9 * * 1-5"
            },
            "savedAt": "2026-04-23T..."
          }
        ]
      },
      "meta": {
        "createdAt": "2026-04-19T...",
        "updatedAt": "2026-04-19T..."
      }
    }
  }
}
```

## Rules

### For all plugins

- **`core.*` is shared convention** — every PM-oriented plugin may read it; writes should be minimal and limited to first-run self-bootstrap (the profile skeleton written by `/pm-feedback` or `/pm-automations` on first invocation when no profile exists) or explicit user action.
- **`plugins.<name>.*` is that plugin's sandbox** — other plugins MUST NOT modify keys outside their own namespace.
- **Never store secrets here** — API tokens, OAuth keys, and passwords stay in the MCP auth store they belong to. This file is for references (e.g., channel IDs), not credentials.
- **Always update `meta.updatedAt`** when your plugin writes to its namespace.
- **Schema migrations**: if `schemaVersion` is lower than you expect, migrate carefully and bump the version. Never hard-fail — peer plugins may be on different release cadences.

### Default read order

Skills should read in this order and merge:

1. `~/.claude/profile.json` (preferred, shared)
2. Plugin-local fallback (e.g., `pm-config.json` kept for backward compat)
3. User prompt if still missing

## Adding a new plugin namespace

Pick a stable kebab-case name (`pm-skills`, `content-system`, `canvas-builder`, etc.) and add keys under `plugins.<name>`. Document your namespace's expected shape in a similar SCHEMA doc on your plugin. Example:

```json
"plugins": {
  "pm-skills": { "jira": {...}, "slack": {...} },
  "content-system": { "campaigns": [...] },
  "canvas-builder": { "courses": [...] }
}
```

## `plugins.pm-skills.automations`

Added for the `/pm-automations` skill. Holds **saved interview drafts** (templates the user answered but didn't confirm, or starred for reuse) — not the automations themselves. The scheduled-tasks MCP is the source of truth for created tasks; this file just remembers user-preferred answer sets to pre-fill future interviews.

Shape: `templates: Array<{ key: string, template: "meeting-sync"|"channel-to-coda"|"weekly-canvas"|"agenda-prep"|"custom", answers: Record<string, string>, savedAt: ISO }>`.

Do not store prompt text, credentials, or MCP IDs here — only user-visible answers (meeting titles, cron strings, destination URIs).

## Backward compatibility

- `pm-skills` reads profile first; the `/meeting-sync` artifact falls back to the legacy `pm-config.json` at the plugin root if the profile is missing a JIRA board, and then to its own in-canvas config flow.
- `pm-config.json` is no longer migrated automatically (the `/pm-setup` skill that did this was removed in v2.1). If you have one, it stays as a read-only hint.
