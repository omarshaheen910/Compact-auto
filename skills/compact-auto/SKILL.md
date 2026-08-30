---
name: compact-auto
description: Runs the ask-before-compacting flow for Claude Code. Use this skill whenever a [compact-auto] system reminder says automatic compaction was held back or is due again, whenever the user asks to compact, postpone compacting, change the compaction threshold, or asks how full the context window is, and whenever the user says something like "you're about to forget", "don't compact yet", or "compact but keep X". Also use it when setting up or troubleshooting the compact-auto plugin itself.
---

# compact-auto

Claude Code compacts on its own when the context window crosses a threshold, and
it decides what to keep with no idea what the user is actually working on. This
plugin moves that decision to the user: automatic compaction is held back, the
user is asked, and whatever they say matters gets written down and carried
across the compaction boundary.

The gate lives in a `PreCompact` hook. This skill is the half that talks to the
user.

## Trigger

A blocked compaction arrives as a system reminder starting with `[compact-auto]`.
It carries the current percentage and the absolute path to `compact_state.py`.
Use that path verbatim in the commands below — do not guess it.

## The flow

### 1. Ask, and stop

Drop the current task mid-step if you have to. Report the number and ask one
short question, in the language the user has been writing in:

> Context is at 41% (82k of 200k). Compact now, or keep going?

Nothing else. No summary of the session, no list of options, no preamble. If the
user is clearly mid-thought on something urgent, still ask — but keep it to one
line so it costs them a second.

Then stop and wait. Do not start the next step of the task while the question is
open; anything you do now is work that compaction may swallow.

### 2a. If they say yes — write the handoff before approving

Ask what to keep in focus, unless they already said. Then write a handoff note.
This note is re-injected into the fresh context after compaction and outranks
Claude Code's own summary, so it is the only thing you can count on surviving.

Write it to the path from `compact_state.py handoff-path`, using this shape:

```markdown
# Handoff — <short task name>

## Focus
<what the user asked to keep, in their words>

## Where we are
<the current state of the task in 3-6 lines: what is done, what is half-done>

## Files and locations
<paths touched, with the function or line that matters — not a directory listing>

## Decisions already made
<choices that must not be relitigated, and why>

## Next steps
<the concrete next action, then the one after it>

## Open questions
<anything waiting on the user>
```

Fill it from the actual conversation, not from a template. Specifics that cost
tokens to rediscover — a file path, an error string, a version number, a
rejected approach — earn their place. Restating what the code obviously does
does not. Aim for under 400 words unless the task genuinely needs more.

Then record the approval:

```bash
python3 <scripts>/compact_state.py approve --focus "the auth refactor" --handoff <path>
```

Tell the user it is recorded and that compaction will run on the next turn, or
that they can type `/compact` now to do it immediately. Then stop — do not
resume the task, since it is about to be compacted anyway.

### 2b. If they say no — offer the three ways to postpone

Ask which one, in one line:

- remind me in 5 messages → `--until prompts:5`
- remind me at 50% → `--until pct:50`
- not again this session → `--until session`

```bash
python3 <scripts>/compact_state.py snooze --until prompts:5
```

If they just say "no" or "later" without picking, default to `prompts:5` and say
which default you used in half a sentence. Then go straight back to the task
with no further comment.

## Rules that keep this bearable

- **Ask once per crossing.** After a snooze is recorded, say nothing about
  context until the reminder fires again. A gate that nags gets uninstalled.
- **Never announce the postponement twice.** The hook already tells you it is
  holding compaction back; that is not news to repeat to the user.
- **Match the user's language.** The hook messages are English; the user's may
  not be. Answer in theirs.
- **Above 85% the gate steps aside** and compaction runs unasked, because a
  postponed compaction that meets a full window costs the whole session. If you
  notice this happened, mention it in one line afterwards.
- **Manual `/compact` is never blocked.** If the user types it themselves, that
  is their call — but offer to write a handoff note first if the session holds
  state worth keeping.

## Setup and tuning

The gate only ever runs when Claude Code decides to auto-compact, so the
threshold is what makes "ask me at 40%" real:

```bash
python3 <scripts>/setup_threshold.py --set 40     # ask at 40%
python3 <scripts>/setup_threshold.py             # show the current value
python3 <scripts>/setup_threshold.py --unset     # back to the default
```

This writes `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` in `~/.claude/settings.json`
and keeps a `.bak`. Ask before running it — it edits the user's settings — and
tell them Claude Code needs a restart afterwards.

Other knobs, all environment variables:

| Variable | Default | What it does |
| --- | --- | --- |
| `COMPACT_AUTO_ASK_PCT` | `40` | The percentage the reminder logic treats as "due" |
| `COMPACT_AUTO_HARD_PCT` | `85` | Above this the gate stops blocking |
| `COMPACT_AUTO_CONTEXT_WINDOW` | inferred | Window size, for gateways or 1M models |
| `COMPACT_AUTO_HOME` | `~/.claude/compact-auto` | Where state and handoff notes live |

Keep `COMPACT_AUTO_ASK_PCT` and `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` at the same
number. They are separate settings for the same intent, and they drift apart
silently if only one is changed.

## Troubleshooting

- **Nothing ever asks.** The threshold is probably unset — run
  `setup_threshold.py` with no arguments to check. Plugin hook changes also need
  `/reload-plugins` or a restart.
- **Percentages look wrong.** The number comes from the last assistant message's
  token usage in the transcript, against a 200k window unless the model is a 1M
  variant. On a custom gateway, set `COMPACT_AUTO_CONTEXT_WINDOW`.
- **`python3` not found on Windows.** Change `python3` to `python` in
  `hooks/hooks.json`.
- **Check what the gate thinks:** `python3 <scripts>/compact_state.py status`.
