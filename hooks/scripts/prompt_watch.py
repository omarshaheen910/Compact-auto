#!/usr/bin/env python3
"""UserPromptSubmit watcher.

Two jobs:
  * count user messages, which is what the "remind me in 5 messages" snooze
    measures itself against;
  * when a snooze has run out and the context is still above the threshold,
    put a short note in front of Claude so the question gets asked again even
    if Claude Code does not re-fire auto-compact on its own.

Stays silent the rest of the time. A hook that talks on every turn is a hook
the user turns off.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ctx_lib as cl  # noqa: E402


def main() -> None:
    data = cl.read_input()
    session_id = data.get("session_id", "")
    state = cl.load_state(session_id)
    state["prompt_count"] = int(state.get("prompt_count", 0)) + 1

    used, window, pct = cl.context_usage(data.get("transcript_path", ""))
    state["last_pct"] = pct

    note = None
    if (
        state.get("mode") == "snoozed"
        and pct >= cl.ask_pct()
        and cl.snooze_expired(state, pct)
    ):
        state["mode"] = "idle"
        state["snooze"] = None
        note = (
            f"[compact-auto] The compaction the user postponed is due again. "
            f"Context is now at {pct}% ({used:,} of {window:,} tokens). "
            "After answering this message, ask the user whether to compact now, "
            "following the compact-auto skill."
        )

    cl.save_state(session_id, state)

    if note:
        cl.emit({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": note,
            }
        })


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
