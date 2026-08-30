# compact-auto

Claude Code auto-compacts on its own schedule and keeps whatever it thinks is
important. This plugin holds that compaction back, asks you first, and carries a
handoff note you approved across the compaction boundary.

## What happens

1. Context crosses your threshold (40% once configured) and Claude Code starts an
   automatic compaction.
2. A `PreCompact` hook blocks it and hands Claude a note.
3. Claude asks you: compact now, or keep going?
   - **Yes** → Claude asks what to keep in focus, writes a handoff note, records
     the approval. The next compaction goes through, and the note is injected
     into the fresh context afterwards, outranking the auto-summary.
   - **No** → pick one: remind me in 5 messages, remind me at 50%, or not again
     this session.
4. Above 85% the gate steps aside and compaction runs regardless, so a
   postponement can never strand you at a full window.

Typing `/compact` yourself is never blocked.

## Install

Inside Claude Code:

```
/plugin marketplace add omarshaheen910/Compact-auto
/plugin install compact-auto@compact-auto
```

Or clone it yourself:

```bash
git clone https://github.com/omarshaheen910/Compact-auto ~/.claude/plugins/compact-auto
```

then `/reload-plugins` inside Claude Code.

## First run — required

Installing the plugin is not enough on its own. The gate only runs when Claude
Code decides to auto-compact, and out of the box that happens around 95%, long
past the point you wanted to be asked. Set the threshold once:

```bash
python3 ~/.claude/plugins/compact-auto/hooks/scripts/setup_threshold.py --set 40
```

That writes `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` into `~/.claude/settings.json`
(keeping a `.bak`) and needs a Claude Code restart. Skip it and the plugin looks
like it does nothing.

Check it took:

```bash
python3 ~/.claude/plugins/compact-auto/hooks/scripts/setup_threshold.py
```

A plugin cannot edit your settings for you, which is why this is a manual step.

Alternatively, drop the folder in `~/.claude/skills/compact-auto/` — any folder
there with a `.claude-plugin/plugin.json` loads as a plugin with no install step.

## Layout

```
compact-auto/
├── .claude-plugin/plugin.json
├── skills/compact-auto/SKILL.md     the ask-the-user flow
└── hooks/
    ├── hooks.json                   PreCompact + UserPromptSubmit + SessionStart
    └── scripts/
        ├── ctx_lib.py               transcript reading, % maths, state
        ├── precompact_gate.py       the gate
        ├── prompt_watch.py          message counter + snooze expiry
        ├── session_restore.py       re-injects the handoff after compaction
        ├── compact_state.py         CLI Claude uses to record your answer
        └── setup_threshold.py       sets the auto-compact threshold
```

## Requirements

Python 3.8+ on `PATH` as `python3`. On Windows without a `python3` alias, change
`python3` to `python` in `hooks/hooks.json`.

## Settings

| Variable | Default | Meaning |
| --- | --- | --- |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Claude Code default | When auto-compact fires — the real trigger |
| `COMPACT_AUTO_ASK_PCT` | `40` | When the reminder logic considers a compaction due |
| `COMPACT_AUTO_HARD_PCT` | `85` | Above this the gate stops blocking |
| `COMPACT_AUTO_CONTEXT_WINDOW` | inferred | Window size for custom gateways or 1M models |
| `COMPACT_AUTO_HOME` | `~/.claude/compact-auto` | State and handoff notes |

## Notes and limits

- The percentage is derived from the last assistant message's token usage in the
  session transcript, because hooks are not given a context percentage the way
  status lines are. It tracks `/context` closely but is not the same counter.
- Claude cannot run `/compact` itself — built-in slash commands are not available
  to the model. Approval lets the *next* automatic compaction through; you can
  also type `/compact` to trigger it immediately.
- Every hook fails open. If a script errors, Claude Code behaves exactly as it
  would without this plugin.
- State and handoff notes are plain files under `COMPACT_AUTO_HOME`. Consumed
  notes are kept as `.md.consumed` — delete them whenever you like.
