#!/usr/bin/env python3
"""SessionStart (matcher: compact) — re-inject the handoff note.

Compaction summarises the conversation with no idea what the user cares about.
The handoff note written just before compacting is the part that must survive,
so it goes straight back into the fresh context here.
"""

from __future__ import annotations  # keeps `Path | None` working on Python 3.8/3.9

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ctx_lib as cl  # noqa: E402

MAX_CHARS = 9_000  # hook output is capped at 10k; leave room for the wrapper
STALE_SECONDS = 3 * 60 * 60


def _pick_handoff(session_id: str) -> Path | None:
    safe = "".join(c for c in (session_id or "") if c.isalnum() or c in "-_")[:80]
    exact = cl.home() / f"handoff-{safe}.md"
    if exact.is_file():
        return exact
    # The session id can change across a compaction boundary, so fall back to
    # the most recent unconsumed note, as long as it is fresh.
    notes = sorted(
        (p for p in cl.home().glob("handoff-*.md") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for p in notes:
        if time.time() - p.stat().st_mtime < STALE_SECONDS:
            return p
    return None


def main() -> None:
    session_id = ""
    data = cl.read_input()
    session_id = data.get("session_id", "")

    note = _pick_handoff(session_id)
    if not note:
        return

    body = note.read_text(encoding="utf-8").strip()
    if len(body) > MAX_CHARS:
        body = body[:MAX_CHARS] + "\n...(truncated)"

    note.rename(note.with_suffix(".md.consumed"))

    state = cl.load_state(session_id)
    state["mode"] = "idle"
    state["snooze"] = None
    state["handoff"] = None
    cl.save_state(session_id, state)

    if not body:
        return

    cl.emit({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": (
                "[compact-auto] The conversation was just compacted. These are the "
                "handoff notes written before compaction, at the user's request. "
                "They take priority over the auto-generated summary wherever the two "
                "disagree.\n\n" + body
            ),
        }
    })


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
