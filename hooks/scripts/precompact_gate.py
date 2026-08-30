#!/usr/bin/env python3
"""PreCompact gate (matcher: auto).

Holds an automatic compaction until the user has said yes. Blocking here is
cheap because the threshold that triggers auto-compact is low (40%), so the
session has plenty of room while the question is being asked.

Outcomes:
  allow  -> exit 0 with no output (user approved, or we hit the safety ceiling)
  block  -> {"decision": "block", "reason": ...}; the reason reaches Claude
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ctx_lib as cl  # noqa: E402


def main() -> None:
    data = cl.read_input()

    # Manual /compact is the user's own decision; never stand in its way.
    if data.get("trigger") == "manual":
        return

    session_id = data.get("session_id", "")
    used, window, pct = cl.context_usage(data.get("transcript_path", ""))
    state = cl.load_state(session_id)
    state["last_pct"] = pct
    ceiling = cl.hard_pct()
    scripts = cl.scripts_dir()

    # Safety valve: past the ceiling, never hold compaction back, whatever the
    # user said earlier. A postponed compaction that runs into a full window
    # costs the whole session.
    if pct and pct >= ceiling:
        state["mode"] = "idle"
        state["snooze"] = None
        cl.save_state(session_id, state)
        return

    if state.get("mode") == "approved":
        state["mode"] = "idle"
        state["snooze"] = None
        cl.save_state(session_id, state)
        return

    if state.get("mode") == "snoozed" and not cl.snooze_expired(state, pct):
        cl.save_state(session_id, state)
        cl.emit({
            "decision": "block",
            "reason": (
                f"[compact-auto] Auto-compact held back: the user {cl.describe_snooze(state)}. "
                "Say nothing about this and carry on with the task."
            ),
        })
        return

    usage_line = (
        f"{pct}% of the context window ({used:,} of {window:,} tokens)"
        if used else "at the auto-compact threshold"
    )
    state["mode"] = "asking"
    state["snooze"] = None
    cl.save_state(session_id, state)

    cl.emit({
        "decision": "block",
        "reason": (
            f"[compact-auto] Automatic compaction was held back. Context is {usage_line}.\n"
            "Pause the current task and follow the compact-auto skill now:\n"
            "1. Tell the user the current percentage and ask, in the user's own language, "
            "whether to compact now.\n"
            "2. If yes, ask what to keep in focus, write the handoff note, then run:\n"
            f"   python3 {scripts}/compact_state.py approve --focus \"...\" --handoff <path>\n"
            "3. If no, offer three ways to postpone and record the choice with:\n"
            f"   python3 {scripts}/compact_state.py snooze --until prompts:5 | pct:50 | session\n"
            "Ask the question and stop. Do not resume the task until the user answers."
        ),
    })


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Fail open: a broken gate must never trap a session below its threshold.
        sys.exit(0)
