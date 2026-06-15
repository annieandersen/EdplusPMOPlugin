---
name: pm-feedback
description: "Route feedback about any PM Skills plugin skill into the hub's Feedback table. You (Claude) infer the skill, task, input, output, and issue from the conversation, draft a full feedback entry, and show the user a one-line yes/edit/no. Conversational only. Never render AskUserQuestion or any form-style picker for this skill."
user_invocable: true
---

# PM Feedback

> **Run**: `/pm-feedback` (or auto-offer when the user sounds dissatisfied)
> **Time**: ~10 seconds — the user reads a draft and says yes / edit / no
> **Writes to**: The Feedback table on the PM Skills Plugin Hub (Coda)

## Purpose

When a plugin skill produces something unhelpful — wrong ticket proposal, off-tone Slack summary, missed context, a bug we had to work around — route that feedback into the hub's Feedback table so it can be triaged.

**The user's job** is to express the issue in their own words OR just confirm a draft you wrote from context. **Your job** is everything else: identifying which skill, summarizing what they were trying to do, capturing the relevant input and output, extracting any suggestion they made, and writing it all into Coda. The user should never see a form, a picker, a multi-field input, or any structured question UI.

---

## Hard rules

- **Never call `AskUserQuestion`** in this skill. It renders a form-style UI (skill picker + "What's the issue?" + "Suggestion" text fields) and that's exactly the experience we're moving away from. Ask in plain prose if you must ask anything at all.
- **Never ask the user to pick the skill** from a list. Infer it from the conversation. If you genuinely can't tell, ask in one short sentence: "Is this feedback about meeting-sync, or something else?" — not as a multi-choice picker.
- **Never ask multiple questions at once.** If a draft is missing something, ask one short follow-up, get the answer, and move on.
- **Auto-draft from context whenever possible.** If the conversation already contains a clear issue (the user complained, you fixed a bug, a skill produced bad output the user reacted to), draft the entire feedback entry from that context. Don't make the user re-explain.

---

## Phase 1: Load config (self-bootstrapping)

Read `~/.claude/profile.json`. Get:

- `plugins.pm-skills.coda.feedbackTableUri`
- `core.user.email` (for the Submitter column)

**Self-bootstrap if anything is missing.** There is no `/pm-setup` skill anymore — this skill creates what it needs silently.

1. **If the file is missing entirely**: write this skeleton, then continue:
   ```json
   {
     "schemaVersion": 1,
     "core": {
       "user": { "name": null, "email": null, "role": "PM", "timezone": "America/Phoenix" },
       "brand": { "voice": "conversational, direct, practical", "tone": "friendly but not casual; assumes the reader is busy", "doNotUse": [] },
       "preferences": { "defaultMeetingRange": "last_week" }
     },
     "plugins": {
       "pm-skills": {
         "jira": { "boards": [] },
         "slack": { "channels": [] },
         "coda": {
           "hubDocUri": "coda://docs/Nh3S1m8BlQ",
           "feedbackTableUri": "coda://docs/Nh3S1m8BlQ/tables/grid-oPj79TwqCD"
         },
         "automations": { "templates": [] },
         "meta": { "createdAt": "<ISO now>", "updatedAt": "<ISO now>" }
       }
     }
   }
   ```

2. **If `feedbackTableUri` is missing**: set it to `coda://docs/Nh3S1m8BlQ/tables/grid-oPj79TwqCD` (the canonical hub table) and save.

3. **If `core.user.email` is missing**: try `mcp__Coda__whoami` silently. If it returns an email, write it to the profile and save. If Coda isn't connected, leave `null` and proceed — the Submitter column will land empty and the user can fix it later. Do not prompt.

Never tell the user you had to bootstrap. This is a transparent self-heal.

---

## Phase 2: Draft the feedback from conversation context

Before talking to the user, write a full draft of all the fields below. You're filling out the row; the user is just signing off on it.

| Field | How to fill |
|---|---|
| **Skill** | Which plugin skill is the feedback about? Pick one of: `meeting-sync`, `pm-automations`, `canvas-updates-builder`, `pm-feedback`, `new-skill-request` (if the user is asking for a skill that doesn't exist yet), or `general`. Infer from what skill was being run or discussed when the issue surfaced. Don't ask the user. |
| **Task** | 1–2 sentences: what was the user trying to accomplish? Lift from the user's recent message(s). |
| **Input from the user** | The most recent user instruction or message that kicked off the problematic behavior (truncate to ~500 chars). |
| **Output** | What the skill produced — summarize the last assistant action or response the user reacted to (truncate to ~500 chars). If the issue is a bug you had to fix during this conversation, the "output" is the bug description and what was wrong with it. |
| **Main Feedback** | The user's stated issue, OR if they haven't stated one explicitly, your synthesis of what went wrong based on the conversation. Write it in the user's voice and tone — first person, conversational, the same brand voice the rest of the plugin uses. Specific and actionable: not "this skill is bad" but "the artifact resolver tried canonical-name addressing first, which silently fails inside Cowork because `callMcpTool` requires UUIDs". |
| **Suggestion** | What the user said they'd rather happen, OR your inference if they didn't say. Optional — leave blank if neither you nor they have a clear suggestion. |

### When you have plenty of context (the common case)

If the conversation has already surfaced the issue — the user complained, you debugged something, a fix was applied, etc. — draft all fields silently, then show the draft to the user in a single message:

```
Drafted this feedback for the hub:

**Skill**: meeting-sync
**Task**: <one-line task summary>
**Issue**: <2-4 sentence Main Feedback in the user's voice>
**Suggestion**: <one line, or "none">

Look good? Reply "send" to file it, or tell me what to change.
```

Keep it tight — the user should be able to read it in five seconds. Don't show Input/Output snippets unless the user asks; those go into the Coda row but they're not interesting to read back in the chat.

### When you have thin context (the user typed `/pm-feedback` cold)

Ask one short, conversational question in prose: "What's on your mind? — give me a sentence or two and I'll write it up." Then take whatever they say, expand it into the structured fields, and show the draft for confirm.

### Confirmation handling

- `send` / `yes` / `looks good` / `ship it` → proceed to Phase 4.
- Any edit instruction ("make it sharper", "change the suggestion to X", "swap the skill to pm-automations") → revise the draft and re-show it.
- `no` / `cancel` / `nevermind` → bail out, tell the user nothing was filed.

---

## Phase 3: (Removed)

The old Phase 3 used `AskUserQuestion` to present a form. That's gone. Drafting and confirmation both live in Phase 2 above.

---

## Phase 4: Write to Coda

### Step 4a: Resolve column IDs

`table_rows_manage` writes require column **IDs** (not names). Read the table schema once per invocation and cache the name→ID mapping.

Call `mcp__Coda__page_read` with `contentTypesToInclude: ["tables"]` on the Plugin Feedback page (parent of the Feedback table) to get the schema. For each column you need to write, pull its `columnId`. Example IDs for the canonical hub's Feedback table (subject to change if the hub is ever rebuilt — always resolve fresh):

| Name | Example ID |
|---|---|
| Submitter | `c-Tp7E5_8ls_` |
| Skill | `c-m0PuGJ2fMs` |
| Main Feedback | `c-tHPb6u8LAa` |
| Task | `c-Mv_Eof9Z73` |
| Input from the user | `c-XLNmwrkgbP` |
| Output | `c-uNTSscgd5N` |
| Suggestion | `c-1x7I8KAMgN` |
| Account for | `c-NUINFD91mM` |
| Submitted | `c-ZnGGiAcT9H` |

### Step 4b: Add the row

Call `mcp__Coda__table_rows_manage` with `action: "add"`, passing resolved IDs in `columns` and the matching value array in `rows`:

```json
{
  "uri": "<feedbackTableUri from profile, typically coda://docs/Nh3S1m8BlQ/tables/grid-oPj79TwqCD>",
  "data": {
    "action": "add",
    "columns": [
      "<ID for Submitter>",
      "<ID for Skill>",
      "<ID for Main Feedback>",
      "<ID for Task>",
      "<ID for Input from the user>",
      "<ID for Output>",
      "<ID for Suggestion>",
      "<ID for Account for>",
      "<ID for Submitted>"
    ],
    "rows": [
      [
        "<core.user.email>",
        "<inferred skill key>",
        "<Main Feedback from the draft>",
        "<Task from the draft>",
        "<Input snippet from the draft>",
        "<Output snippet from the draft>",
        "<Suggestion from the draft, or empty>",
        false,
        "<ISO now>"
      ]
    ]
  }
}
```

> Payload shape notes:
> - `columns` is an array of **column IDs** (`c-...`), not display names. Display names are rejected.
> - `rows` is an array of value-arrays; each inner array positionally matches `columns`.
> - Do not pass per-row objects keyed by column name — that format is rejected.

**Canonical URIs** (for the shared PM Skills Plugin Hub — these are hardcoded into the profile skeleton in Phase 1):

- Hub doc: `coda://docs/Nh3S1m8BlQ`
- Feedback table: `coda://docs/Nh3S1m8BlQ/tables/grid-oPj79TwqCD`

- `Account for` is always false on submission — maintainers toggle it true when triaged.
- Use markdown in canvas fields for any emphasis (e.g., `**decision**`).

---

## Phase 5: Confirm + link

Get the row URL from the response (or construct from the table URL).

Tell the user concisely:

```
Filed: "<one-line summary of the Main Feedback>"
Tagged: {skill} • Submitted as: {email}
View: {row link}
```

Keep it short — one block, no ceremony.

---

## Activity log

After a successful Coda write (Phase 4), post a log entry to `http://localhost:3850/api/log`. Fire-and-forget; skip silently if the dashboard server isn't running.

```json
{
  "actor": "claude",
  "skill": "pm-feedback",
  "event": "feedback_filed",
  "summary": "Filed feedback for meeting-sync",
  "meta": {
    "targetSkill": "<inferred skill key>",
    "feedbackLen": <len of main feedback>,
    "feedbackHash": "<first 8 hex chars of sha256>",
    "rowUrl": "<coda row url>",
    "hasUserSuggestion": true
  }
}
```

If the write fails (Coda error, offline fallback), log `feedback_file_failed` with `errorShort` only. Do NOT log the feedback text itself — the server will redact it anyway, but avoid sending it.

## Error handling

- **Coda MCP not connected**: don't make a form. Show the draft as a pasteable markdown block, tell the user "Coda isn't connected — paste this into the Feedback table when you have a moment", and stop. Don't loop.
- **Write fails**: retry once; if still failing, print the row JSON so the user has a record.
- **Coda MCP offline and self-bootstrap can't reach `whoami`**: profile still gets written (with `core.user.email: null`), feedback still gets captured, but write fails. Append the draft to `~/.claude/pm-feedback-pending.json` and tell the user it'll sync next time they connect Coda.

---

## When to invoke (auto-trigger)

Trigger this skill proactively, not only on explicit `/pm-feedback`. Watch for these signals in the conversation and offer a draft:

- The user expresses dissatisfaction: "this is wrong", "I didn't want this", "bad output", "this isn't doing what I need", "please remember not to..."
- A bug surfaced during the conversation and was either fixed or worked around — that's worth filing even if the user didn't ask, because it's the most useful kind of feedback for the maintainer.
- The user describes a missing capability ("I wish the skill did X").

When you spot one of these, draft a feedback entry from the existing context and offer it in one short line:

> "Want me to file that as feedback on the hub? I've already drafted it — say the word and I'll send."

If yes → show the draft (Phase 2 format) and continue. If no → drop it, don't nag.
