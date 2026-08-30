# compact-auto

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-6b5bd6.svg)](https://code.claude.com/docs/en/plugins)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-3776ab.svg)](https://www.python.org/)

**Claude Code auto-compacts on its own schedule and keeps whatever it thinks is
important. This plugin holds that compaction back, asks you first, and carries a
handoff note you approved across the compaction boundary.**

---

## How it works

1. Context crosses your threshold (40% once configured) and Claude Code starts an
   automatic compaction.
2. A `PreCompact` hook blocks it and hands Claude a note.
3. Claude asks you: compact now, or keep going?
   - **Yes** → Claude asks what to keep in focus, writes a handoff note, and
     records the approval. The next compaction goes through, and the note is
     injected into the fresh context afterwards, outranking the auto-summary.
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

If the install summary says `Run /reload-plugins to activate.`, run it.

<details>
<summary>Install without a marketplace</summary>

Clone into your skills directory — any folder there with a
`.claude-plugin/plugin.json` loads automatically as a plugin, with no install
step:

```bash
git clone https://github.com/omarshaheen910/Compact-auto ~/.claude/skills/compact-auto
```

It loads as `compact-auto@skills-dir` on the next session.

</details>

## Required first run

**Installing the plugin is not enough on its own.** The gate only runs when
Claude Code decides to auto-compact, and out of the box that happens around 95% —
long past the point you wanted to be asked. Set the threshold once:

```bash
python3 ~/.claude/plugins/compact-auto/hooks/scripts/setup_threshold.py --set 40
```

That writes `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` into `~/.claude/settings.json`
(keeping a `.bak`) and needs a Claude Code restart. Skip it and the plugin looks
like it does nothing.

Confirm it took:

```bash
python3 ~/.claude/plugins/compact-auto/hooks/scripts/setup_threshold.py
```

To undo it: `setup_threshold.py --unset`.

> A plugin cannot edit your settings for you, which is why this step is manual.

## Requirements

Python 3.8 or newer, reachable on `PATH` as `python3`.

**On Windows**, `python3` often does not exist — the python.org installer
provides `python` and `py` instead. Check with `python3 --version`; if it fails,
replace `"command": "python3"` with `"command": "python"` in
[`hooks/hooks.json`](hooks/hooks.json) (three occurrences) and restart Claude
Code. Symptom if you skip this: the hooks silently do nothing.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Claude Code default | When auto-compact fires — the real trigger |
| `COMPACT_AUTO_ASK_PCT` | `40` | When the reminder logic considers a compaction due |
| `COMPACT_AUTO_HARD_PCT` | `85` | Above this the gate stops blocking |
| `COMPACT_AUTO_CONTEXT_WINDOW` | inferred | Window size for custom gateways or 1M models |
| `COMPACT_AUTO_HOME` | `~/.claude/compact-auto` | State and handoff notes |

## Layout

```
compact-auto/
├── .claude-plugin/
│   ├── plugin.json                  plugin manifest
│   └── marketplace.json             single-plugin marketplace
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

## Development

Load a working copy without installing it:

```bash
claude --plugin-dir ./compact-auto
```

Validate the manifest before publishing:

```bash
claude plugin validate ./compact-auto
```

Exercise a hook directly — each one reads its event JSON on stdin:

```bash
export COMPACT_AUTO_HOME=/tmp/compact-auto-test
echo '{"trigger":"auto","session_id":"s1","transcript_path":"/path/to/transcript.jsonl"}' \
  | python3 hooks/scripts/precompact_gate.py
```

`/reload-plugins` picks up edits without restarting Claude Code — except changes
to `settings.json`, which need a restart.

## Design notes and limits

- **The percentage is an estimate.** Hooks are not given a context percentage the
  way status lines are, so it is derived from the last assistant message's token
  usage in the session transcript. It tracks `/context` closely but is not the
  same counter.
- **Claude cannot run `/compact` itself** — built-in slash commands are not
  available to the model. Approval lets the *next* automatic compaction through;
  you can also type `/compact` to trigger it immediately.
- **Every hook fails open.** If a script errors, Claude Code behaves exactly as
  it would without this plugin. That rule is why the gate can afford to block.
- **State is plain files** under `COMPACT_AUTO_HOME`. Consumed handoff notes are
  kept as `.md.consumed` — delete them whenever you like.

## License

MIT © Omar Shaheen. See [LICENSE](LICENSE).
