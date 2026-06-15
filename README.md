# PM Skills Plugin (`pm-plugin`)

A PM-productivity plugin for Claude Code. Current version: **2.1.3** (see [`VERSION`](VERSION)).

It turns Granola meetings into reviewable JIRA proposals plus a Slack summary, builds
weekly Slack Canvas update pipelines, walks PMs through creating recurring scheduled
agents, and routes feedback into a shared Coda hub. The plugin self-bootstraps a user
profile (brand voice, JIRA boards, Slack channels) on first run, so it ships portable —
no API keys or tokens are stored anywhere; everything routes through user-authenticated MCPs.

## Slash commands / skills

| Skill | What it does |
|-------|--------------|
| `/meeting-sync` | Launches a live Cowork artifact: recent Granola meetings → JIRA ticket proposals → Slack summary |
| `/canvas-updates-builder` | Guided setup for an automated weekly Slack Canvas update pipeline |
| `/pm-automations` | Interview-driven builder for recurring scheduled PM agents |
| `/pm-feedback` | Routes feedback about any skill into the shared Coda Feedback table |

## Repository layout

```
.claude-plugin/plugin.json   Plugin manifest (name, version, author)
VERSION                      Plugin version (source of truth, matches plugin.json)
INSTALL.md                   Install steps + full version changelog
PROFILE_SCHEMA.md            Shape of the self-bootstrapped user profile
pm-config.json               Example user config (JIRA boards, defaults)
skills/
  meeting-sync/              SKILL.md + bundled Cowork artifact.html (+ backups/)
  canvas-updates-builder/    SKILL.md
  pm-automations/            SKILL.md
  pm-feedback/               SKILL.md
```

## Installing / developing

See [`INSTALL.md`](INSTALL.md) for install steps and the version-by-version changelog.

## MCP dependencies

The skills call user-authenticated MCP servers (Granola, JIRA via Zapier, Slack, Coda)
and the Cowork runtime. MCP server UUIDs are detected per-user at runtime and substituted
into the bundled artifact before it is pushed — the plugin source stays portable. No
credentials live in this repo.

## Not included here

A separate `catalog-compare` research project (ASU vs. UTK course-catalog comparison —
scrapers, ~250 MB of scraped data, generated reports, a Vercel deploy) lives alongside the
plugin in the original working folder but is **not** part of this plugin and is intentionally
excluded from this repository.

## Ownership

Originally authored by Auryan Ratliff (apratlif@asu.edu). This repository was created to hand
off plugin development; see repository collaborators for current maintainers.
