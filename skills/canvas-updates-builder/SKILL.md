---
name: canvas-updates-builder
user_invocable: true
description: >
  Guided setup wizard that builds a personalized automated Slack Canvas weekly update pipeline for any user or team.
  Creates two scheduled tasks: a draft task (gathers context, synthesizes an update, posts it to a draft canvas for
  review) and a publish task (reads the approved draft, sends the announcement to the Slack channel, and pushes the
  canvas body to the live canvas). Designed for org-wide distribution — works on public and private channels.
  Run with `/canvas-updates-builder`, or trigger by saying: "set up a canvas update automation",
  "build a weekly update skill", "automate my weekly status update", "create my own scheduled canvas update",
  or any similar request to build a recurring Slack Canvas update workflow.
---

# Canvas Updates Builder

This skill walks the user through a complete setup wizard and produces two ready-to-run scheduled tasks:

1. **Draft task** — gathers context from connected sources (Slack, Jira, Granola), synthesizes an update per configured focus areas, writes a draft to the approval canvas (including an editable announcement message at the top), and pings the task owner for review.
2. **Publish task** — checks for approval, reads the draft canvas, posts the announcement message to the Slack channel via `slack_send_message`, and pushes only the canvas body content (everything below the message block) to the live canvas.

**Key architectural note on the draft canvas format:**
The top of the draft canvas always contains a `**Slack Message:**` block with the pre-authored announcement text. The task owner can edit this in the canvas before approving. The publish task reads and sends it as a Slack message, but never copies it to the live canvas — only the content below it goes to the live canvas.

Work through each phase in order. Use `AskUserQuestion` for all multi-choice decisions. Never skip phases.

---

## Opening + Connector Check — Run This First

Before sending any message, silently call `slack_search_channels` with query "general" to test whether Slack is connected.

Store the result as SLACK_CONNECTED (true/false). Then send a single structured opening message using the template below.

---

### Opening Message Template

Adapt the tone naturally but preserve the structure and hierarchy exactly. This is the first and only message before setup questions begin.

---

**Let's set up your automated Slack Canvas update.**

Here's how the automation works once it's running:

**Step 1 — Draft (runs on your chosen day/time)**
Claude pulls context from your connected sources — Slack channels, meeting notes, Jira tickets — synthesizes this week's update, and writes it to a **private draft canvas** in Slack. It then pings you to review. The draft includes the exact announcement message Claude will post to your channel, which you can edit before approving.

**Step 2 — Publish (runs after you approve)**
You review the draft canvas, make any edits you want (including tweaking the announcement message), and reply *approved*. On your scheduled publish day, Claude posts the announcement to your Slack channel and pushes the canvas body to your **live team canvas**.

---

**A few things to know before we start:**

- **Your formatting is preserved.** Share your existing canvas link and Claude will read it and match your exact layout every time. Multi-column sections will be flattened to a single column (a Slack API limitation), but all content is kept.
- **No canvas yet?** No problem — Claude will create one for you.
- **Works on any EdPlus channel.** Because this runs through your organization's Claude Slack bot, it can post to any public or private channel within your EdPlus workspace. Channels in other Slack workspaces aren't accessible — if that's your situation, Claude will still update the canvas automatically and DM you the announcement text to post manually.
- **Scheduling heads-up.** These tasks need Claude to be running to fire automatically. If your computer is asleep or Claude is closed, you can always trigger either task manually by saying "run [task name]."

---

**Connector status:**

[Insert connector status block below]

---

### Connector Status Blocks

**If SLACK_CONNECTED = true:**
```
✅ Slack — connected
```
Then immediately call `AskUserQuestion` with Phase 2 questions. Do not say anything else first.

---

**If SLACK_CONNECTED = false:**
```
⛔ Slack — not connected (required)

Slack is required for this automation. Here's how to connect it:
→ Connect Slack to Claude: https://scribehow.com/viewer/How_to_Connect_Slack_to_Claude_AI__9LJG07bVSDmAlc92hcql7Q

Once connected, come back and say "let's continue the canvas update builder" and we'll pick up right here.
```
Stop. Do not proceed to Phase 2 until Slack is confirmed connected.

---

## Phase 2: Gather Core Inputs — Round 1 (Canvases & Channel)

Use `AskUserQuestion` to ask all three questions together in a single call.

**Question 1:** "Do you have an existing live Slack Canvas you'd like Claude to update each week? Paste the link below, or choose 'Create one for me' and Claude will set it up."
- Option A: "Create one for me"
- Other: Paste your canvas link — e.g. `https://yourworkspace.slack.com/docs/T.../F0...`

**If the user typed a URL:** extract the canvas ID (the `F0XXXXXXXX` segment — everything after the last `/`). Store as LIVE_CANVAS_ID. Do not call `slack_read_canvas` yet — that happens in Phase 5.

**If the user chose "Create one for me":** Do not create the canvas yet — it will be created in Phase 5 after reading the template format. Set LIVE_CANVAS_PENDING = true. Tell the user: *"Great — I'll create your live canvas in a moment after I set up the formatting."*

**Question 2:** "Do you have an existing draft/approval canvas? This is where Claude writes the weekly draft for your review before anything goes live. Paste the link, or let Claude create it."
- Option A: "Create one for me"
- Other: Paste your draft canvas link — e.g. `https://yourworkspace.slack.com/docs/T.../F0...`

**If the user typed a URL:** extract the canvas ID and store as DRAFT_CANVAS_ID.
**If the user chose "Create one for me":** call `slack_create_canvas` with title "Weekly Update — Draft & Approval" and a placeholder body. Store the returned canvas ID as DRAFT_CANVAS_ID and note the URL to share with the user.

**Question 3:** "Which Slack channel should the weekly announcement be posted to when it publishes? Paste the channel name or link — e.g. `#language-buddy` or `https://yourworkspace.slack.com/archives/C012345`"
- Other: (free text)

After collecting answers, look up the channel ID using `slack_search_channels` and store it as ANNOUNCEMENT_CHANNEL_ID. Also store the channel name as ANNOUNCEMENT_CHANNEL_NAME.

**If the channel is not found in search results**, send this message — do NOT ask them to try again yet:

> "**#[channel-name]** isn't in the EdPlus Slack workspace, so Claude can't post there automatically.
>
> Here's what that means in practice:
> **Your canvas still updates every week on schedule** — that part works regardless of which channel you post to.
> **For the announcement, you'd post it yourself.** After each draft is approved, Claude will DM you the message text, ready to copy-paste. If you want it to go out automatically every week, you can set up a Slack Workflow that posts on a recurring schedule. Or just paste it manually once you've reviewed the draft — up to you.
>
> No wrong answer here."

Then immediately use `AskUserQuestion` — do not ask them to retype the channel name:
- Option A: **"Continue with #[channel-name] — I'll handle posting myself"** (Your canvas updates automatically. Claude DMs you the announcement text each week.)
- Option B: **"Use a different channel inside EdPlus"** (I'll type a new one.)

If they choose **Option A**:
- Set ANNOUNCEMENT_CHANNEL_ID to null.
- Set ANNOUNCEMENT_CHANNEL_NAME to whatever the user originally typed (for labeling in task prompts).
- Set MANUAL_ANNOUNCEMENT = true.
- Move on immediately. Do not confirm again or re-explain. Proceed to the next question.

If they choose **Option B**: ask once for a channel within the EdPlus workspace as free text, retry `slack_search_channels`. If not found again, repeat this same fork — do not loop silently.

---

## Phase 3: Gather Core Inputs — Round 2 (Canvas Focus & Context Sources)

### 3A: Canvas Focus

Use `AskUserQuestion`:

**Question:** "What does this canvas cover? List each focus area with a short description so Claude knows exactly what to track and attribute each week."
- Option A: "Just one thing — I'll describe it"
- Other: List them — e.g. "Language Buddy (AI language learning app), ASU AI Hub (faculty tooling)" or "EdPlus marketing team — campaigns and content" or "Q2 GTM campaign — launch readiness"

Store as CANVAS_FOCUS. If the user chose Option A, ask them to describe it as free text (e.g., "Language Buddy — AI language learning app for ASU students", or "EdPlus design team", or "Spring 2026 enrollment campaign").

This canvas can cover anything: a product, a team, a project, a campaign — or a mix. CANVAS_FOCUS will be embedded into the draft task so Claude knows what to attribute content to when synthesizing context from multiple sources.

### 3B: Context Sources

Use `AskUserQuestion` to ask all three together:

**Question 1 (multi-select):** "Which Slack channels should I search each week for context?"
- Option A: "Same as my announcement channel" — use the channel set up in Phase 2 (no extra lookup needed)
- Option B: "Other channels — I'll specify" — I'll type the channel names or links
- Option C: "Skip — don't search any Slack channels"

If they select Option A only: reuse ANNOUNCEMENT_CHANNEL_ID and ANNOUNCEMENT_CHANNEL_NAME from Phase 2 — no additional lookup needed.
If they select Option B (with or without A): ask for the additional channels as free text (comma-separated). Look up each using `slack_search_channels`. For any channel not found, send this message once:

> "I couldn't find **#[channel-name]** — it's not in the EdPlus workspace, so Claude won't be able to search it each week."

Then use `AskUserQuestion`:
- Option A: **"Skip #[channel-name] — don't search it"**
- Option B: **"Replace it with a different EdPlus channel"** (I'll type the name.)

Do not loop. If Option B results in another not-found channel, repeat this fork once more and offer the same two choices. Never ask the user to retype the same channel name.
If they select both A and B: combine the announcement channel with the additional specified channels.
If they select Option C: set SLACK_SEARCH_CHANNELS to null.

**Question 2:** "Paste your Jira epic or ticket IDs, separated by commas. The first one will be treated as the primary reference; the rest as supporting context. Not using Jira? Choose 'Skip Jira.'"
- Option A: "Skip Jira"
- Other: PROJ-123, PROJ-456, PROJ-789

If the user typed IDs:
- Silently call `jira_software_cloud_find_issue_by_key` with the first ID to test the connection.
- **If Jira IS connected:** store all IDs. First = primary reference; rest = supporting context. Set JIRA_CONNECTED = true.
- **If Jira is NOT connected:** tell the user:
  > "⚠️ Jira doesn't appear to be connected yet. Here's how to set it up:
  > → Connect Jira via Zapier MCP: https://scribehow.com/viewer/Connecting_Jira_to_Claude_through_Zapier_MCP__4BJbW516RjekOWk78Hkp8g
  >
  > Connect it and say "continue with Jira" to use those IDs, or say "skip Jira" to proceed without it."
  Then pause and wait for their response.
If the user chose "Skip Jira": set JIRA_IDS to null and JIRA_CONNECTED = false.

**Question 3:** "Do you use Granola for meeting notes? If yes, Claude will search your meeting transcripts as the highest-priority context source each week."
- Option A: "Yes — pull from Granola"
- Option B: "No Granola"

If the user chose "Yes":
- Silently call `query_granola_meetings` with a minimal query (e.g. "meeting") to test the connection.
- **If Granola IS connected:** set GRANOLA_CONNECTED = true.
- **If NOT connected:** tell the user:
  > "⚠️ Granola doesn't appear to be connected. Make sure the Granola MCP is enabled in your Claude settings, then say "continue with Granola" to include it, or "skip Granola" to proceed without it."
  Then pause and wait.

### 3C: Confirm Source Priority Order

Once all sources are collected, send the user a plain-text message showing their ranked source list:

> "Here's how I'll weight your sources each week when writing the update — higher priority wins when there's overlap:
>
> [List sources in priority order, e.g.:]
> 1. 🏆 Granola meeting notes (highest — decisions and commitments from actual conversations)
> 2. Jira [PRIMARY_TICKET] comments (high — recent status changes and blockers)
> 3. Slack channels: #[channel-1], #[channel-2] (medium — activity and signals from the past 7 days)
> 4. Jira supporting epics: [SUPPORTING_TICKETS] (reference only — background context, lowest weight)
>
> Does this order look right, or would you like to adjust it?"

Use `AskUserQuestion`:
- Option A: "Looks good — use this order"
- Option B: "I'd like to adjust the priority — let me specify"

If they choose Option B: ask them to describe the order they want as free text. Adjust the stored priority list accordingly. This final priority order will be embedded verbatim into the draft task prompt.

### 3D: Tone & Writing Focus

Now that sources are confirmed, ask the user how they want the weekly update to feel and what to emphasize in the writing. This preference gets embedded directly into the draft task so every generated update reflects their intent.

Use `AskUserQuestion` with a multi-select question:

**Question:** "How should Claude approach the writing each week? Select everything that applies — these will shape the tone and focus of every draft. (Don't see what you need? Use 'Other' to describe it.)

Whatever you select, every draft always starts from a base of clear, direct writing that doesn't assume the reader has any context from the week — exec-friendly by default. Your choices add to that baseline, they don't replace it."

- Option A: **Executive-facing** — High altitude. Lead with decisions made and outcomes. Minimize detail, maximize signal.
- Option B: **Cross-team visibility** — Emphasize what other teams need to know or act on. Clear handoffs and dependencies.
- Option C: **Progress and momentum** — Celebrate what shipped and what moved forward. Keep energy positive.
- Option D: **Risks and blockers first** — Surface problems prominently so they don't get buried below progress.
- Option E: **Research and insights** — Prioritize learnings, user feedback, and data signals over activity.
- Option F: **Other** — Anything else? Type it in. (e.g., "Keep it casual and warm", "Always end with a clear ask for the team", "Use emoji sparingly")

After collecting their response:
- Combine all selected options into a single `TONE_AND_FOCUS_NOTES` block. For each selected option, include its label and a one-line description of what it means in practice.
- If the user typed anything in "Other", append it verbatim as an additional instruction.
- This block will be pasted directly into the draft task's Step 3 synthesis instructions.

**Example of a combined block:**
```
Writing focus for this canvas:
- Executive-facing: Lead with decisions and outcomes. Minimize detail. One sentence per product in the overview is enough if there's nothing significant.
- Risks and blockers first: If there's an active blocker, it should appear in the Overview and again in Risks — don't bury it.
- Other: Always end the Coming Up section with a clear ask or owner so there's no ambiguity about who's doing what.
```

Store the final block as `TONE_AND_FOCUS_NOTES`.

---

## Phase 4: Schedule, Approval & Announcement Message

### 4A: Schedule

Use `AskUserQuestion`:

**Question 1:** "When would you like the draft to be generated each week?"
- Option A: "Friday afternoon (e.g., 3 PM Friday)" (Recommended — gives you the weekend to review)
- Option B: "A different day/time — I'll specify"

**Question 2:** "When would you like the approved update to be published?"
- Option A: "Monday morning (e.g., 9 AM Monday)" (Recommended — fresh start to the week)
- Option B: "A different day/time — I'll specify"

If the user chose custom times, ask for them as free text. Parse into 5-field cron expressions (LOCAL time):
- "Friday 3 PM" → `0 15 * * 5`
- "Monday 9 AM" → `0 9 * * 1`

**If MANUAL_ANNOUNCEMENT = true:** After parsing the user's desired publish time, subtract 30 minutes to get the actual cron expression. Store both:
- `PUBLISH_TIME_USER_FACING` — the time the user asked for (e.g., "9 AM")
- `PUBLISH_TIME_CRON` — 30 minutes earlier (e.g., `0 8 30 * * 1` → `30 8 * * 1`)

Then tell the user: *"Since you'll be posting the announcement manually, I've scheduled the publish task for [PUBLISH_TIME_CRON rendered as human time, e.g. '8:30 AM'] instead of [PUBLISH_TIME_USER_FACING] — this gives the canvas time to update so everything is ready right when you want to post at [PUBLISH_TIME_USER_FACING]."*

The publish task prompt header says "You run every [PUBLISH_DAY] at [PUBLISH_TIME_USER_FACING]" (human-readable), but use PUBLISH_TIME_CRON for the `cronExpression` when creating the task.

### 4B: Approval Destination

Every draft goes through an approval step before anything gets published. Send this note:

> "💡 **Quick tip on approval notifications:** Slack DMs from bots can't @-mention you the way a channel message can — so if Claude notifies you via DM, you may not get a proper ping and could easily miss it. Routing approvals to a channel lets Claude @-mention you directly every time a draft is ready.
>
> Note: this is just for draft review pings — it's separate from where the weekly announcement gets posted to your team."

Then use `AskUserQuestion`:

> "Where would you like the approval notification sent when the draft is ready?"
- Option A: "DM to me — just me managing this" (no @mention ping — you may miss the notification)
- Option B: "Post to the announcement channel — same channel the update gets posted to" (Recommended if your announcement channel is accessible)
- Option C: "Post to a different channel — I'll specify"

If they choose Option B: reuse ANNOUNCEMENT_CHANNEL_ID and ANNOUNCEMENT_CHANNEL_NAME from Phase 2. Store APPROVAL_DESTINATION as `channel`. Store APPROVAL_CHANNEL_ID = ANNOUNCEMENT_CHANNEL_ID. No additional lookup needed.

If they choose Option C: ask for the channel name as free text. Look up the channel ID using `slack_search_channels`. **If not found**, send this message once:

> "I couldn't find **#[channel-name]** — it's not in the EdPlus workspace, so Claude can't post approval notifications there."

Then use `AskUserQuestion`:
- Option A: **"Fall back to DM — just notify me directly"** (no @mention ping, but it'll work)
- Option B: **"Try a different EdPlus channel"** (I'll type the name.)

If Option A: set APPROVAL_DESTINATION as `dm`, APPROVAL_CHANNEL_ID to null.
If Option B: ask once for a new channel name and retry. If still not found, default to DM and tell the user: *"Couldn't find that one either — I'll send approval notifications as a DM to keep things moving."*

Do not loop indefinitely. After two failed lookups, always fall back to DM automatically. Store as APPROVAL_CHANNEL_ID. Store APPROVAL_DESTINATION as `channel`.

If they choose Option A (DM): store APPROVAL_DESTINATION as `dm` and set APPROVAL_CHANNEL_ID to null.

Store the approval destination type and resolved ID for use in Phases 7 and 8.

### 4C: Pre-Author the Announcement Message

Now that you know the canvas topic, products, and announcement channel, draft the exact message Claude will post to the channel each week when the update publishes.

Write a natural, channel-appropriate announcement message. It should:
- Open with a brief, friendly greeting appropriate to the team's context
- Reference the canvas focus (whatever the update is about — product, team, campaign, etc.)
- Include a placeholder for the link to the live canvas on its own line

**Example for a single product:**
```
Morning everyone, here's last week's Language Buddy updates! 🎉
[link to live canvas]
```

**Example for multiple products:**
```
Hey team, your weekly AI product updates are live! 👇
Language Buddy | ASU AI Hub
[link to live canvas]
```

Send the drafted message to the user:
> "Here's the announcement message I'll post to **#[ANNOUNCEMENT_CHANNEL_NAME]** each week when your update publishes. You can also edit it directly in the draft canvas before approving each week if you want to tweak it for that specific update.
>
> ---
> [drafted message]
> ---
>
> Want to adjust the wording?"

Use `AskUserQuestion`:
- Option A: "Looks great — use this"
- Option B: "Let me edit it — I'll type the version I want"

If they choose Option B: collect their version as free text.

Store the final message as ANNOUNCEMENT_MESSAGE. This will be embedded verbatim in the draft task as the default `**Slack Message:**` block each week.

---

## Phase 5: Auto-Analyze the Live Canvas (No User Guidance Needed)

If LIVE_CANVAS_PENDING is false (the user provided an existing canvas), call `slack_read_canvas` with LIVE_CANVAS_ID and continue with 5A–5E below. The goal is to reverse-engineer the canvas structure so the draft task can replicate it precisely — without asking the user to explain their formatting. Do not ask the user any questions in this phase.

### 5A: Extract and Classify Every Section

For each section (delineated by `#`, `##`, `###` headers or `---` dividers):

1. **Header text** — record exactly as written, including emoji (e.g., `:large_green_circle: Progress this Week`)
2. **Content type** — `paragraph`, `bullet-list`, `numbered-list`, `table`, `image`, `date-stamp`, or `mixed`
3. **Item count** — how many bullets, sentences, or list items are typically present
4. **Item structure** — detect patterns: bold label + colon + description, plain sentences, links only, nested lists
5. **Approximate item length** — short (≤10 words), medium (10–25 words), long (25+ words)
6. **Contains links** — yes/no; inline or reference block
7. **Contains date tags** — yes/no; note format (`![](slack_date:YYYY-MM-DD)`)
8. **Contains images** — yes/no; note reference style

### 5B: Identify Protected Sections

Mark any section as **PROTECTED** if its header contains (case-insensitive):
`resources`, `links`, `references`, `key`, `sources`, `documentation`, `useful`, `tools`, `contacts`, `about`, `important`, `pinned`, `archive`

Protected sections: never delete or overwrite their content, never remove the header, only append if the user explicitly requests it. Extract and store verbatim content — this gets hardcoded into the draft task prompt.

### 5C: Detect Layout Issues

If `::: {.layout}` or `::: {.column}` syntax is found, tell the user:
> "I noticed your canvas uses a multi-column layout. The Slack Canvas API doesn't support columns in updates, so I'll render the same content in a single-column format — all the information will still be there, just stacked vertically."

### 5D: Detect the Date Format

If the canvas uses `![](slack_date:YYYY-MM-DD)` tags, all generated content must use this format. If it uses plain text dates, match that style.

### 5E: Build the Section Template

For each non-protected section:
```
## [exact header text]

[content type: bullet-list | numbered-list | paragraph | etc.]
[item count: e.g., max 5 bullets]
[item structure: e.g., **Bold label:** description ≤25 words]
[inclusion rule: inferred from purpose — e.g., "only if active and unresolved", "only if something shipped this week"]
```

For protected sections:
```
## [exact header text]

[PROTECTED — reproduce this content verbatim every time:]
[full literal content, copied exactly]
```

### 5-Pre: Handle the No-Canvas Case

If LIVE_CANVAS_PENDING is true (the user chose "Create one for me" in Phase 2):

1. Call `slack_read_canvas` with `canvas_id`: `F0ARKEMBLNS`
   This is the master template canvas. Do NOT edit it — read only.

2. Run the full 5A through 5E analysis against the template canvas content, exactly as you would for a user's existing canvas. This produces the section template for the draft task.

3. Call `slack_create_canvas` with title "[Topic] — Weekly Updates" (using the canvas focus from Phase 3A — e.g. "Language Buddy — Weekly Updates" or "EdPlus Marketing — Weekly Updates"). Use the section structure derived from the template canvas as the initial body content of the new canvas (reproduce the headers, dividers, and placeholder structure — not the template's actual data). Store the returned canvas ID as LIVE_CANVAS_ID and the URL as LIVE_CANVAS_URL. Tell the user: *"I've created your live canvas — here's the link: [LIVE_CANVAS_URL]. You can share this with your team."*

4. Continue to Phase 6. The 5A–5E steps below have already been executed against the template.

If the `slack_read_canvas` call for `F0ARKEMBLNS` fails for any reason, fall back to the following default section template and embed it directly into the draft task:

```
## Overview

[content type: paragraph]
[item count: 1–2 sentences]
[item structure: plain prose, no bullets. Cover what changed this week, the biggest win or callout, and what's coming up.]
[inclusion rule: always include]

---

## Progress this Week

[content type: bullet-list]
[item count: max 5 bullets]
[item structure: **Bold label:** description ≤25 words]
[inclusion rule: only if something meaningfully shipped, was decided, or was discovered this week]

---

## Risks & Blockers

[content type: bullet-list]
[item count: max 5 bullets]
[item structure: **Risk name:** impact + optional owner or next step ≤25 words]
[inclusion rule: only if the risk is active and unresolved right now]

---

## Coming Up / Next Steps

[content type: numbered-list]
[item count: max 5 items]
[item structure: plain sentence — concrete action, owner, 1–2 week horizon]
[inclusion rule: only concrete actions with a clear owner due within 1–2 weeks]

---

## Recent Insights

[content type: bullet-list]
[item count: 2 to 4 bullets]
[item structure: plain sentence ≤25 words]
[inclusion rule: only if the finding is new or has changed since the last update]
```

Then skip to Phase 6.

---

## Phase 6: Resolve the Task Owner's Slack User ID

Call `slack_search_users` with the user's name or email if known, OR use the logged-in Slack user ID from the `slack_search_users` tool description (it appears as "Current logged in user's Slack user_id is UXXXXXXXXX").

Store this as TASK_OWNER_SLACK_ID. This will be embedded in both task prompts.

---

## Phase 7: Build and Create the Draft Task

Generate the full draft task prompt by substituting every collected value. Do not summarize or abstract — every canvas ID, channel ID, Jira ticket, and section template must be written out in full. This prompt must be entirely self-contained: a future Claude session must be able to run it cold with no prior context.

**Anti-hallucination requirement:** The generated task must make absolutely clear that every claim, figure, and fact written to the canvas must be traceable to a specific retrieved source from Step 2. Nothing should be inferred, assumed, or filled in to sound plausible. If sources come back empty, the task should write that clearly — not fabricate content that resembles what might have happened.

When embedding `[TONE_AND_FOCUS_NOTES]`, paste the full block collected in Phase 3D verbatim — every line, exactly as constructed. This block is the primary writing personality for every draft this task generates, so it must be complete and specific, not summarized.

### Draft Canvas Format — Critical

The draft canvas always starts with a `**Slack Message:**` block containing the pre-authored announcement message. This block is written fresh every week by the draft task (resetting to the default). The task owner may edit it in the canvas before approving — those edits are preserved by the publish task. The publish task reads the message and sends it to Slack, but **never** copies it to the live canvas.

### Real-World Example — Use This as Your Quality Bar

```
You are the Language Buddy Friday draft task. You run every Friday at 3 PM.

Your job is to gather context, synthesize this week's Language Buddy update, write the full draft to the approval canvas (F0APAPMA6R3), and notify the task owner for review. You do NOT update the live canvas (F0AQ5FE1WJD) or post to any channel. Those happen in the publish task only.

TASK OWNER SLACK ID: U07KX4CK741
DRAFT CANVAS ID: F0APAPMA6R3
DRAFT CANVAS URL: https://asu.enterprise.slack.com/docs/T024GDW9H/F0APAPMA6R3
LIVE CANVAS ID: F0AQ5FE1WJD — DO NOT TOUCH IN THIS TASK
LIVE CANVAS URL: https://asu.enterprise.slack.com/docs/T024GDW9H/F0AQ5FE1WJD
APPROVAL CHANNEL ID: C0XXXXXXXXX
CANVAS FOCUS: Language Buddy — AI-powered language learning app for ASU students
(When reassigning this task to a new owner, update TASK OWNER SLACK ID to the new owner's Slack user ID.)

---

## Step 1: Determine the Report Date

Calculate the date of the coming Monday from today (Friday) — today + 3 days. Use this in all ![](slack_date:YYYY-MM-DD) tags.

---

## Step 1.5: Read the Live Canvas — Capture Last Week's Content

Call slack_read_canvas with canvas_id: F0AQ5FE1WJD.

Store the current content of each section as LAST_WEEK_CONTENT. This is the fallback baseline — if a section has no new sourced content this week, you'll carry forward whatever was there last week rather than leaving it blank or writing a placeholder.

---

## Step 2: Gather Context — Strict Priority Order

Run ALL sources before writing anything. Higher-priority sources take precedence when content overlaps.

### PRIORITY 1 — Granola Meeting Notes (highest weight)
Call query_granola_meetings with:
- "Language Buddy"
- "LB product update"
- "language learning"
⚠️ GRANOLA LOOKBACK RULE: Only use meetings from the **past 7 days**. Check each meeting's date before extracting anything. If a meeting occurred more than 7 days ago, skip it entirely — do not include its content.
Extract: decisions made, blockers raised, commitments and next steps, UXR findings, demo feedback, anything exec-relevant.

### PRIORITY 2 — Jira AIPD-2564 Comments (high weight)
Fetch AIPD-2564 using jira_software_cloud_find_issue_by_key. Focus on:
- Recent comments (most important)
- Status changes, decisions, blockers in comments
- Linked sub-tasks with recent activity

### PRIORITY 3 — Slack Channels (medium weight)
Search using slack_search_public_and_private, past 7 days:
- #language-buddy: shipped features, decisions, blockers, UXR findings, stakeholder updates
- #language-buddy-tech: dev progress, technical blockers, deployments, integrations
Discard: scheduling coordination, one-word acknowledgments, emoji reactions.

### REFERENCE ONLY — Supporting Jira Epics (lowest weight)
Fetch for background context only. Do not let these override Priority 1–3:
- AIPD-2444 (v3 Discovery)
- AIPD-3020 (UXR Spring 2026)
- AIPD-3022 (Dev Spring 2026)

---

## Step 3: Synthesize the Draft

Rules:
- Granola and AIPD-2564 comments take precedence over all other sources
- Bullets ≤25 words. No jargon. Outcomes over activity.
- No em-dashes (—) — use colons or commas instead.
- Inclusion test: "Would an ASU exec need this to make a decision or assess risk?" If no, cut it.

Base writing standards — always applied:

Writing tone — exec-friendly, clear, and readable by anyone with no assumed context:
- Write like a sharp colleague giving a status update, not like a bot generating a report.
- Use plain, direct language. Say "finished" not "successfully completed." Say "blocked by" not "currently impacted by."
- Get to the point fast. Lead with what happened or what matters, not setup or context.
- Don't assume the reader was in the room. Write so someone with zero context from this week can understand the situation in one read.
- Never use AI filler: "dive into," "leverage," "optimize," "unlock," "game-changing," "revolutionary," "transformative," "it's worth noting that," "it's important to highlight."
- Keep it honest. If progress was small, say so. Don't inflate or hype.
- The reader is busy. Every sentence should earn its place. If it doesn't help them make a decision or understand a risk, cut it.

Organization — scannable and self-contained:
- Anchor every bullet with "Language Buddy:" first so a reader can scan and find what's relevant immediately.
- No buried lede: the most important thing in each section should be the first bullet, not the last.
- Short over long. If a bullet needs more than 25 words, it's doing two jobs — split it or cut it.

Additional writing focus for this canvas:
- Executive-facing: Lead with decisions and outcomes. Minimize detail.
- Progress and momentum: Celebrate what shipped and what moved forward.

| Section | Max items | Include only if... |
|---|---|---|
| Progress this Week | 5 bullets | Something meaningfully shipped, decided, or discovered |
| Risks & Blockers | 3 bullets | The risk is active and unresolved right now |
| Coming Up / Next Steps | 4 items | Concrete action with clear owner, due in 1–2 weeks |
| Recent Insights | 2–4 bullets | Finding is new or changed since last update |

---

## Step 4: Write the Full Draft to Canvas F0APAPMA6R3

⚠️ THIS IS THE MOST IMPORTANT STEP. Call slack_update_canvas to write the full draft. If you skip this, nothing works.

Call slack_update_canvas with:
- canvas_id: F0APAPMA6R3
- action: replace
- No section_id (full body replace)

⚠️ CANVAS TITLE RULE: Do NOT start content with a # heading. The canvas title is set by Slack. Start directly with **Slack Message:** and nothing before it.

Write the canvas using EXACTLY this structure:

**Slack Message:**
"Morning everyone, here's last week's Language Buddy updates! 🎉
https://asu.enterprise.slack.com/docs/T024GDW9H/F0AQ5FE1WJD"

---

Date: ![](slack_date:YYYY-MM-DD)

**Overview**

[1–2 sentence paragraph. No bullets. What changed this week, biggest win, what's next.]

---

## :large_green_circle: Progress this Week

* **[Label]:** [What was done and why it matters. ≤25 words.]
[max 5 bullets]

---

## :large_yellow_circle: Risks & Blockers

* **[Risk name]:** [Impact + optional owner/next step. Max 3 bullets.]

---

## :depositphotos_31468817-stock-photo-coming-soon-sign: Coming Up / Next Steps

1. [Concrete action, owner, 1–2 week horizon.]
[max 5 items]

## 🔗 Key Resources:

* Roadmap: [click here](https://coda.io/d/_dzAGqMKmDiF/Language-Buddy-6-Month-Product-Roadmap_suSz6eTZ?utm_source=slack)

---

## 📊 Recent Insights

* UXR discovery takeaway: [New or updated finding only. ≤25 words.]
[2 to 4 bullets]

---

Canvas markdown rules:
- NEVER start content with a # heading.
- Section headers use ## or ### only.
- Bullets: * list items.
- Numbered lists: 1. syntax.
- Dividers: --- on its own line.
- Slack emojis: :emoji_name: format.
- Dates: ![](slack_date:YYYY-MM-DD) only.
- Links: [text](https://full-url) — full HTTPS URLs only.
- No column/layout syntax. No em-dashes.

---

## Step 5: Notify the Task Owner for Review

After slack_update_canvas succeeds, send a DM to the task owner. If slack_update_canvas fails, report the error in this Claude session and stop — do not send the notification.

Send a direct message using slack_send_message with channel set to U07KX4CK741:

":pencil: Your weekly draft is ready.
I've written this week's Language Buddy update. Check it out, make any edits you want, then reply approved when it's good to go. [PUBLISH_DAY] at [PUBLISH_TIME] I'll post it to the channel and update the live canvas.
https://asu.enterprise.slack.com/docs/T024GDW9H/F0APAPMA6R3

📋 Sources checked this run:
[List one line per connector — e.g.:]
✅ Slack: connected
✅ Jira: connected
⚠️ Granola: not connected — meeting context not included

[If any figures in the draft came from Granola, include this block — otherwise omit entirely:]
⚠️ The following figures came from Granola meeting notes and may need verification before you approve:
[Product]: [specific figure as it appears in the draft]

[If the model is Claude Haiku, include this line — otherwise omit entirely:]
⚠️ This draft was generated using Claude Haiku. For more accurate synthesis, consider re-running with Sonnet or higher."

After sending, confirm briefly in this Claude session: what date is the report for, which sources were checked and their status, and any gaps.
```

Use this exact template, substituting all [BRACKETED] values:

---
PROMPT START →

You are the [CANVAS_TOPIC] draft task. You run every [DRAFT_DAY] at [DRAFT_TIME].

Your job is to gather context, synthesize this week's [CANVAS_TOPIC] update, write the full draft to the approval canvas ([DRAFT_CANVAS_ID]), and notify the task owner for review. You do NOT update the live canvas ([LIVE_CANVAS_ID]) or post to any channel. Those happen in the publish task only.

TASK OWNER SLACK ID: [TASK_OWNER_SLACK_ID]
DRAFT CANVAS ID: [DRAFT_CANVAS_ID]
DRAFT CANVAS URL: [DRAFT_CANVAS_URL]
LIVE CANVAS ID: [LIVE_CANVAS_ID] — DO NOT TOUCH IN THIS TASK
LIVE CANVAS URL: [LIVE_CANVAS_URL]
[If approval channel: APPROVAL CHANNEL ID: [APPROVAL_CHANNEL_ID]]
CANVAS FOCUS: [CANVAS_FOCUS — each with a one-line description]
(When reassigning this task to a new owner, update TASK OWNER SLACK ID to the new owner's Slack user ID.)

---

## Step 0: Pre-Flight Checks

Run all checks before doing anything else. Do not skip this step.

**Slack Connectivity Check**
Attempt to read one of your configured Slack source channels. If this call fails or returns an error:
- Report the failure in this Claude session: "[CANVAS_TOPIC] weekly draft couldn't run — Slack appears disconnected. Please reconnect Slack and re-run the task manually."
- Stop all further execution immediately. Do not proceed to any other step.

**Model Check**
Note the model currently being used. If it is Claude Haiku, flag this — you will include a note in the Step 5 DM to the task owner.

**Granola Connectivity Check** *(if Granola is configured)*
Attempt a test `query_granola_meetings` call. If it fails or returns no results, record: Granola: not connected or returned no data. Do not stop — continue to the next check.

**Jira Connectivity Check** *(if Jira is configured)*
Attempt to fetch your primary Jira ticket. If it fails, record: Jira: not connected. Do not stop — continue with remaining sources.

Record the status of each connector (connected / not connected). You will use this in the Step 5 DM.

---

## Step 1: Determine the Report Date

[If draft runs on Friday: Calculate the date of the coming Monday (today + 3 days).]
[If draft runs on another day: Calculate the date of the next scheduled publish day.]
Use `![](slack_date:YYYY-MM-DD)` format for all dates — never plain text.

---

## Step 1.5: Read the Live Canvas — Capture Last Week's Content

Call `slack_read_canvas` with `canvas_id`: `[LIVE_CANVAS_ID]`.

Store the current content of each section as LAST_WEEK_CONTENT. This is the fallback baseline — if a section has no new sourced content this week, you'll carry forward whatever was there last week rather than leaving it blank or writing a placeholder.

---

## Step 2: Gather Context

Run ALL sources below before writing anything. Higher-priority sources override lower ones when content overlaps.

[For each enabled source, list in priority order:]

### PRIORITY [N] — [SOURCE NAME] ([weight label])
[Exact query instructions — Granola terms, Jira IDs, channel names/IDs, search window, etc.]
[If Granola: ⚠️ GRANOLA LOOKBACK RULE: Only use meetings from the past 7 days. Check each meeting's date before extracting anything. If a meeting occurred more than 7 days ago, skip it entirely — do not include its content.]
Extract: [what to look for per focus area — decisions, blockers, shipped features, etc.]

[Repeat for each source. Omit sources the user disabled entirely.]

---

## Step 2.5: Source Audit — Required Before Writing Anything

Before writing a single word of the draft, compile a source log:

- For each connector that was checked, note whether it returned data and what was retrieved (e.g., "Granola: 2 meetings found — [Focus area] 4/14, [Focus area] check-in 4/15").
- If a connector returned nothing or was not connected, mark it as empty or unavailable.

You may only write content that is directly traceable to a specific item in this source log. Do not infer, summarize from memory, or fill gaps with reasonable-sounding assumptions. Do not include any numbers, metrics, or statistics that cannot be traced to a specific retrieved source.

If all sources return empty for a given section — no matching Slack messages, no Jira activity, no Granola notes — do NOT leave the section blank or fabricate content. Instead:
1. Check LAST_WEEK_CONTENT (from Step 1.5) for that section. If the existing content is still reasonably current — meaning it doesn't reference specific events or dates that are clearly now past — carry it forward unchanged.
2. Only if the existing content is clearly stale (e.g., it references a deadline that's passed, a launch that already happened, or a meeting from several weeks ago) should you replace it with the plain text: No updates this week.
(Exception: the Overview section always appears with new text, even if brief — write one sentence reflecting this week's actual state.)

---

## Step 3: Synthesize the Draft

Rules:
- Higher-priority sources take precedence when content overlaps
- Attribute content to the correct focus area: [CANVAS_FOCUS]
- Bullets ≤25 words. No jargon. Outcomes over activity.
- No em-dashes (—) — use colons or commas instead
- Inclusion test: "Would the intended audience need this to make a decision or assess risk?" If no, cut it.
- Never write a number, metric, date, or claim about a named person unless it came directly from a retrieved source in Step 2. Do not estimate, infer, or paraphrase in a way that introduces a fact not explicitly present in the source.

Base writing standards — always applied, regardless of focus settings:

Writing tone — exec-friendly, clear, and readable by anyone with no assumed context:
- Write like a sharp colleague giving a status update, not like a bot generating a report.
- Use plain, direct language. Say "finished" not "successfully completed." Say "blocked by" not "currently impacted by."
- Get to the point fast. Lead with what happened or what matters, not setup or context.
- Don't assume the reader was in the room. Write so someone with zero context from this week can understand the situation in one read.
- Never use AI filler: "dive into," "leverage," "optimize," "unlock," "game-changing," "revolutionary," "transformative," "it's worth noting that," "it's important to highlight."
- Keep it honest. If progress was small, say so. Don't inflate or hype.
- The reader is busy. Every sentence should earn its place. If it doesn't help them make a decision or understand a risk, cut it.

Organization — scannable and self-contained:
- Anchor every bullet with the focus area name first (e.g., "Language Buddy:", "Design team:") so a reader can scan and find what's relevant to them immediately.
- No buried lede: the most important thing in each section should be the first bullet, not the last.
- Short over long. If a bullet needs more than 25 words, it's doing two jobs — split it or cut it.
- The canvas should feel organized, not dense. White space and structure matter as much as the words.

Additional writing focus for this canvas:
[TONE_AND_FOCUS_NOTES]

Default section limits (adjust if the canvas template from Phase 5 specifies different values):
| Section | Max items | Include only if... |
|---|---|---|
| Progress this Week | 5 bullets | Something meaningfully shipped, decided, or discovered |
| Risks & Blockers | 5 bullets | The risk is active and unresolved right now |
| Coming Up / Next Steps | 5 items | Concrete action with clear owner, due in 1–2 weeks |
| Recent Insights | 2–4 bullets | Finding is new or changed since last update |

Additional rules:
- Do not include any numbers, metrics, or statistics that cannot be traced to a specific retrieved source. Do not make up or estimate figures of any kind.
- If Granola was used, separately track any specific figures (counts, percentages, timeframes, metrics) that came from Granola — you will list these in the Step 5 DM. Do not flag or caveat them in the canvas itself.
- If a section has no sourced content this week, skip it entirely (except Overview, which always appears).

---

## Step 4: Write the Full Draft to the Approval Canvas

⚠️ THIS IS THE MOST IMPORTANT STEP. You MUST call `slack_update_canvas` to write the draft. If you skip this, nothing works.

Call `slack_update_canvas` with:
- `canvas_id`: `[DRAFT_CANVAS_ID]`
- `action`: `replace`
- No `section_id` — full body replace

⚠️ CANVAS TITLE RULE: Do NOT start content with a # heading. Start directly with **Slack Message:** and nothing before it.

Write the canvas using EXACTLY this structure:

**Slack Message:**
"[ANNOUNCEMENT_MESSAGE]
[LIVE_CANVAS_URL]"

---

[CANVAS BODY — the synthesized update, formatted per the section template from Phase 5]

[PASTE THE FULL SECTION TEMPLATE FROM PHASE 5 HERE — every section with headers, content type, item count, structure, inclusion rules, and verbatim protected section content]

---

Canvas markdown rules (follow exactly):
- NEVER start content with a # heading.
- Section headers use ## or ### only.
- Bullets: `*` or `-` list items.
- Numbered lists: `1.` syntax.
- Dividers: `---` on its own line.
- Slack emojis: `:emoji_name:` format.
- Dates: `![](slack_date:YYYY-MM-DD)` only.
- Links: `[text](https://full-url)` — full HTTPS URLs only.
- No column or layout syntax. No em-dashes.

---

## Step 5: Notify the Task Owner for Review

After `slack_update_canvas` succeeds, send the approval notification. If `slack_update_canvas` fails, report the error in this Claude session and stop — do not send the notification.

[If approval destination is DM:]
Send a direct message using `slack_send_message` with channel set to `[TASK_OWNER_SLACK_ID]`:

":pencil: Your weekly draft is ready.
I've written this week's [CANVAS_TOPIC] update. Check it out, make any edits you want, then reply approved when it's good to go. [PUBLISH_DAY] at [PUBLISH_TIME] I'll post it to the channel and update the live canvas.
[DRAFT_CANVAS_URL]

📋 Sources checked this run:
[List one line per connector:]
✅ Slack: connected
✅ Jira: connected
⚠️ Granola: not connected — meeting context not included
(Show only the connectors that were checked. Use ✅ if connected and returned data, ⚠️ if not connected or returned nothing.)

[If any figures in the draft came from Granola, include this block — otherwise omit it entirely:]
⚠️ The following figures came from Granola meeting notes and may need verification before you approve:
[Product]: [specific figure as it appears in the draft]

[If the model is Claude Haiku, include this line — otherwise omit it entirely:]
⚠️ This draft was generated using Claude Haiku. For more accurate synthesis, consider re-running with Sonnet or higher."

[If approval destination is channel:]
Send a message to channel `[APPROVAL_CHANNEL_ID]`:

"<@[TASK_OWNER_SLACK_ID]> :pencil: Your [CANVAS_TOPIC] weekly draft is ready for review.

Check it out, make any edits you want, then reply *approved* in this thread when it's good to go. [PUBLISH_DAY] at [PUBLISH_TIME] I'll post it to the channel and update the live canvas.

:point_right: [DRAFT_CANVAS_URL]

📋 Sources checked this run:
[List one line per connector — same format as DM version above.]

[Include Granola figure block and/or Haiku warning if applicable — same as DM version.]"

After sending, confirm briefly in this Claude session: what date is the report for, which sources were checked and their status, and any gaps (e.g., "no Slack activity this week" or "Jira ticket is closed").

← PROMPT END
---

After writing the full prompt text, call `create_scheduled_task` with:
- `taskId`: kebab-case topic + "-draft" (e.g. `language-buddy-draft`)
- `description`: "Every [DRAFT_DAY] at [DRAFT_TIME]: gather context, write draft to approval canvas [DRAFT_CANVAS_ID], notify task owner for review."
- `prompt`: the full prompt text above
- `cronExpression`: from Phase 4
- `notifyOnCompletion`: `false` — always. Claude's built-in completion notification isn't useful here (the user gets the real notification via Slack DM from the task itself).

---

## Phase 8: Build and Create the Publish Task

Generate the full publish task prompt — every step written out fully, every ID hardcoded, entirely self-contained.

**Critical behavior for the publish task:**
1. Read the draft canvas
2. Extract the `**Slack Message:**` block → send its text to the announcement channel via `slack_send_message`
3. Extract everything BELOW the `**Slack Message:**` block → push only that to the live canvas
4. Never copy the `**Slack Message:**` block to the live canvas

### Real-World Example — Use This as Your Quality Bar

```
You are the Language Buddy Monday publish task. You run every Monday at 9 AM.

⚠️ DAY CHECK — RUN THIS BEFORE ANYTHING ELSE.
Check today's date. If today is NOT a Monday, stop immediately. Do not search for drafts, do not update any canvas, do not post anything. Send a message to C0XXXXXXXXX:
"<@U07KX4CK741> ⏹️ Language Buddy publish task stopped — today is not Monday. This task only runs on Monday mornings. If you triggered this manually, please wait or confirm you intended to publish early."
Then stop completely.

If today IS Monday, continue below.

---

Your job is to check whether the draft was approved, then:
1. Send the announcement message to the Slack channel
2. Push the canvas body to the live canvas
The announcement MUST be sent before (or alongside) the canvas update — never skip either step.

TASK OWNER SLACK ID: U07KX4CK741
DRAFT CANVAS ID: F0APAPMA6R3 ← READ FROM THIS
LIVE CANVAS ID: F0AQ5FE1WJD ← WRITE TO THIS
LIVE CANVAS URL: https://asu.enterprise.slack.com/docs/T024GDW9H/F0AQ5FE1WJD
ANNOUNCEMENT CHANNEL ID: C0APQUQELC9
APPROVAL CHANNEL ID: C0XXXXXXXXX
(When reassigning this task to a new owner, update TASK OWNER SLACK ID to the new owner's Slack user ID.)

---

## Step 1: Find the Draft Approval Notification

Search for the most recent draft notification using slack_search_public_and_private with query:
"Language Buddy weekly draft" "F0APAPMA6R3"

Identify the most recent result — that is the notification for this cycle.

If nothing is found, send a message to C0XXXXXXXXX:
"<@U07KX4CK741> ⚠️ Language Buddy Monday publish: No draft notification found. The Friday task may not have run. Check and re-run manually if needed."
Then stop.

---

## Step 2: Check for Approval

Read the thread using slack_read_thread with the message's channel and timestamp.

Look for any reply containing "approved", "yes", "send it", or "looks good" (case-insensitive).

- If an affirmative reply exists: continue to Step 3.
- If no affirmative reply: send a message to C0XXXXXXXXX:
  "<@U07KX4CK741> ⏭️ Language Buddy weekly update skipped — no approval found in the draft thread. Reply *approved* to the draft notification when ready, then run the Monday publish task manually."
  Then stop.

---

## Step 3: Read the Draft Canvas and Extract Two Parts

Call slack_read_canvas with canvas_id: F0APAPMA6R3.

The draft canvas is structured like this:

**Slack Message:**
"[the announcement text]
[live canvas URL]"

---

[canvas body sections — Date, Overview, Progress, Risks, etc.]

Extract EXACTLY two things:

**A. The announcement message text**
Everything between `**Slack Message:**` and the `---` divider that follows it.
Strip the outer quotes if present. Preserve all line breaks and URLs exactly.
The task owner may have edited this — always use whatever is in the canvas now.

**B. The canvas body**
Everything from the `---` divider after the `**Slack Message:**` block to the end of the canvas.
Do NOT include the `**Slack Message:**` block itself — it must never appear in the live canvas.

---

## Step 4: Update the Live Canvas — BODY ONLY

⚠️ Write the canvas BODY ONLY to the live canvas. The **Slack Message:** block must NEVER be written to the live canvas.

Call slack_update_canvas with:
- canvas_id: F0AQ5FE1WJD
- action: replace
- content: the canvas body extracted in Step 3B (starting from Date: or the first section header)
- No section_id — full body replace

If this call fails: send a message to C0XXXXXXXXX reporting the error. Do NOT proceed to Step 5. Stop.

---

## Step 5: Post the Announcement to the Channel

After the live canvas is confirmed updated, send the announcement message to the announcement channel.

Call slack_send_message with:
- channel: C0APQUQELC9
- text: the announcement message extracted in Step 3A (exactly as written in the canvas, including any edits the task owner made)

If this call fails: send a message to C0XXXXXXXXX reporting the error. The canvas was already updated — only the post failed. Ask them to post manually or re-run.

---

## Step 6: Confirm Success

Send a message to C0XXXXXXXXX:
"<@U07KX4CK741> ✅ Language Buddy weekly update published. Announcement posted to #[channel] and live canvas updated. View it here: https://asu.enterprise.slack.com/docs/T024GDW9H/F0AQ5FE1WJD"
```

**Manual announcement variant — Steps 5 & 6 look like this when MANUAL_ANNOUNCEMENT = true:**

```
## Step 5: Deliver Announcement Text to Task Owner

Send a DM to U07KX4CK741:
"✅ Live canvas updated. Here's the announcement message to post manually to your channel:

---
Morning everyone, here's last week's Language Buddy updates! 🎉
https://asu.enterprise.slack.com/docs/T024GDW9H/F0AQ5FE1WJD
---

Copy and paste this to your channel when you're ready."

## Step 6: Confirm

Send a DM to U07KX4CK741:
"✅ Language Buddy live canvas updated and ready. The announcement text is in my previous message — go ahead and post it to your channel when you're ready. View the live canvas here: https://asu.enterprise.slack.com/docs/T024GDW9H/F0AQ5FE1WJD"
```

Use this exact template, substituting all [BRACKETED] values:

---
PROMPT START →

You are the [CANVAS_TOPIC] publish task. You run every [PUBLISH_DAY] at [PUBLISH_TIME].

⚠️ DAY CHECK — RUN THIS BEFORE ANYTHING ELSE.
Check today's date. If today is NOT a [PUBLISH_DAY], stop immediately. [Send DM to TASK_OWNER_SLACK_ID / post to APPROVAL_CHANNEL_ID with <@TASK_OWNER_SLACK_ID>]:
"⏹️ [CANVAS_TOPIC] publish task stopped — today is not [PUBLISH_DAY]. This task only runs on [PUBLISH_DAY]. If you triggered this manually, please wait or confirm you intended to publish early."
Then stop completely.

If today IS [PUBLISH_DAY], continue below.

---

Your job is to check whether the draft was approved, then:
1. Send the announcement message to the Slack channel
2. Push the canvas body to the live canvas

TASK OWNER SLACK ID: [TASK_OWNER_SLACK_ID]
DRAFT CANVAS ID: [DRAFT_CANVAS_ID] ← READ FROM THIS
LIVE CANVAS ID: [LIVE_CANVAS_ID] ← WRITE TO THIS
LIVE CANVAS URL: [LIVE_CANVAS_URL]
[If MANUAL_ANNOUNCEMENT is false: ANNOUNCEMENT CHANNEL ID: [ANNOUNCEMENT_CHANNEL_ID]]
[If MANUAL_ANNOUNCEMENT is true: ANNOUNCEMENT CHANNEL: manual — DM task owner after publishing]
[If approval channel: APPROVAL CHANNEL ID: [APPROVAL_CHANNEL_ID]]
(When reassigning this task to a new owner, update TASK OWNER SLACK ID to the new owner's Slack user ID.)

---

## Step 1: Find the Draft Approval Notification

Search for the most recent approval notification using `slack_search_public_and_private` with query:
`"[CANVAS_TOPIC] weekly draft" "[DRAFT_CANVAS_ID]"`

If nothing is found, [send DM to TASK_OWNER_SLACK_ID / post to APPROVAL_CHANNEL_ID with <@TASK_OWNER_SLACK_ID>]:
"⚠️ [CANVAS_TOPIC] publish task: No draft notification found. The draft task may not have run. Check and re-run manually if needed."
Then stop.

---

## Step 2: Check for Approval

Read the thread using `slack_read_thread`. Look for any reply containing "approved", "yes", "send it", or "looks good" (case-insensitive).

- If approved: continue to Step 3.
- If not: [send DM / post to approval channel with <@TASK_OWNER_SLACK_ID>]:
  "⏭️ [CANVAS_TOPIC] weekly update skipped — no approval found. Reply *approved* when ready, then run the publish task manually."
  Then stop.

---

## Step 3: Read the Draft Canvas and Extract Two Parts

Call `slack_read_canvas` with `canvas_id`: `[DRAFT_CANVAS_ID]`.

The draft canvas is structured like this:
```
**Slack Message:**
"[the announcement text]
[live canvas URL]"

---

[canvas body — Date, sections, etc.]
```

Extract EXACTLY two things:

**A. The announcement message text**
Everything between `**Slack Message:**` and the first `---` divider.
Strip outer quotes if present. Preserve line breaks and URLs exactly.
Always use whatever the task owner left in the canvas — they may have edited it.

**B. The canvas body**
Everything from the `---` divider after the `**Slack Message:**` block to the end of the canvas.
Do NOT include the `**Slack Message:**` block. It must never appear in the live canvas.

---

## Step 4: Update the Live Canvas — BODY ONLY

⚠️ Write the canvas BODY ONLY. The **Slack Message:** block must NEVER be written to the live canvas.

Call `slack_update_canvas` with:
- `canvas_id`: `[LIVE_CANVAS_ID]`
- `action`: `replace`
- `content`: the canvas body from Step 3B
- No `section_id` — full body replace

If this fails: [send DM / post to approval channel] reporting the error. Do NOT proceed to Step 5. Stop.

---

## Step 5: Post the Announcement

[If MANUAL_ANNOUNCEMENT is false — announcement channel is within EdPlus workspace:]
Call `slack_send_message` with:
- `channel`: `[ANNOUNCEMENT_CHANNEL_ID]`
- `text`: the announcement message from Step 3A — exactly as written in the canvas, respecting any edits the task owner made

If this fails: [send DM / post to approval channel] reporting the error. The canvas was already updated. Ask them to post manually or re-run.

[If MANUAL_ANNOUNCEMENT is true — announcement channel is in a different workspace:]
Send a DM to `[TASK_OWNER_SLACK_ID]` with:
"✅ Live canvas updated. Here's the announcement message to post manually to your channel:

---
[announcement message from Step 3A — exactly as written in the canvas]
---

Copy and paste this to your channel when you're ready."

---

## Step 6: Confirm

[If MANUAL_ANNOUNCEMENT is false:]
[Send DM to TASK_OWNER_SLACK_ID / post to APPROVAL_CHANNEL_ID with <@TASK_OWNER_SLACK_ID>]:
"✅ [CANVAS_TOPIC] weekly update published. Announcement posted to #[ANNOUNCEMENT_CHANNEL_NAME] and live canvas updated. View it here: [LIVE_CANVAS_URL]"

[If MANUAL_ANNOUNCEMENT is true:]
Send a DM to [TASK_OWNER_SLACK_ID]:
"✅ [CANVAS_TOPIC] live canvas updated and ready. The announcement text is in my previous message — go ahead and post it to your channel when you're ready. View the live canvas here: [LIVE_CANVAS_URL]"

← PROMPT END
---

After writing the full prompt text, call `create_scheduled_task` with:
- `taskId`: matching draft taskId but with `-publish` suffix (e.g. `language-buddy-publish`)
- `description`: "Every [PUBLISH_DAY] at [PUBLISH_TIME]: check approval, read draft canvas [DRAFT_CANVAS_ID], post announcement to channel, update live canvas [LIVE_CANVAS_ID]."
- `prompt`: the full prompt text above
- `cronExpression`: from Phase 4
- `notifyOnCompletion`: `false` — always. Skip Claude's built-in completion notification; the real signal is the Slack announcement going out.

---

## Phase 9: Offer a Test Run

After both tasks are created, ask the user:

> "Your two tasks are set up! Want to run a test right now? I'll gather context, write a draft (including your pre-authored announcement message) to the approval canvas, and send you the review notification — exactly as it'll work every week. Everything will be labeled **[TEST]** so it's clear this isn't the real thing. The live canvas and announcement channel will NOT be touched."

Use `AskUserQuestion`:
- Option A: "Yes — run the test now" (Recommended)
- Option B: "No thanks, I'll wait for the scheduled run"

If the user chooses Option A:

**Step 1 — Gather context.** Run all configured sources exactly as the draft task would.

**Step 2 — Write to the draft canvas.** Call `slack_update_canvas` with `canvas_id: [DRAFT_CANVAS_ID]` and `action: replace`. Prepend a test banner before the `**Slack Message:**` block:

```
🧪 **[TEST RUN — not a real update. Preview of your weekly draft.]**

---

```

Then write the full draft below the banner in the standard structure (including the `**Slack Message:**` block).

**Step 3 — Send the notification.** Send to [TASK_OWNER_SLACK_ID] (DM) or [APPROVAL_CHANNEL_ID] (channel), prefixed with `🧪 *[TEST]* `:

> 🧪 *[TEST]* Your [CANVAS_TOPIC] weekly draft is ready to preview. This is a test run — nothing will be published. Open the approval canvas to see the draft: [DRAFT_CANVAS_URL]

**Step 4 — Do NOT touch the live canvas or post to the announcement channel.**

After completing, confirm briefly: draft canvas updated, notification sent, live canvas untouched.

---

## Phase 10: Summary

Finish with a plain-text summary covering:

1. What was created (task names, IDs, schedules)
2. The draft canvas structure — the `**Slack Message:**` block at the top is the announcement Claude will post each week; they can edit it in the canvas before approving, and their edits will be used exactly as written
3. The approval flow (review draft canvas → reply *approved* → publish task fires)
4. The one-sentence heads-up: tasks need Claude to be running to fire automatically; trigger manually anytime by saying "run [task name]"
5. How to reassign the task to a new owner (update `TASK_OWNER_SLACK_ID` in each task prompt via the scheduled tasks panel)
6. How to permanently change the default announcement message: update the `[ANNOUNCEMENT_MESSAGE]` line in the draft task prompt via the scheduled tasks panel

---

## Reference Links (use throughout the wizard)

- Connect Slack to Claude: https://scribehow.com/viewer/How_to_Connect_Slack_to_Claude_AI__9LJG07bVSDmAlc92hcql7Q
- Connect Jira to Claude via Zapier MCP: https://scribehow.com/viewer/Connecting_Jira_to_Claude_through_Zapier_MCP__4BJbW516RjekOWk78Hkp8g
