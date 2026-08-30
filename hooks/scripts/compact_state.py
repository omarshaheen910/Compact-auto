#!/usr/bin/env python3
"""CLI Claude uses to record the user's answer.

    compact_state.py status
    compact_state.py approve --focus "the auth refactor" [--handoff /path/to/note.md]
    compact_state.py snooze  --until prompts:5 | pct:50 | session
    compact_state.py handoff-path        # where to write the note for this session

The session id is read from CLAUDE_SESSION_ID when set, otherwise from the most
recently touched state file, which is the current session in practice.
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ctx_lib as cl  # noqa: E402


def current_session() -> str:
    sid = os.environ.get("CLAUDE_SESSION_ID")
    if sid:
        return sid
    states = sorted(
        cl.home().glob("state-*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if states:
        return states[0].name[len("state-"):-len(".json")]
    return "unknown"


def handoff_path(session_id: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")[:80] or "unknown"
    return cl.home() / f"handoff-{safe}.md"


def main() -> int:
    ap = argparse.ArgumentParser(prog="compact_state.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")
    sub.add_parser("handoff-path")

    ap_ok = sub.add_parser("approve")
    ap_ok.add_argument("--focus", default="")
    ap_ok.add_argument("--handoff", default="")

    ap_no = sub.add_parser("snooze")
    ap_no.add_argument("--until", required=True, help="prompts:N | pct:N | session")

    args = ap.parse_args()
    sid = current_session()
    state = cl.load_state(sid)

    if args.cmd == "status":
        print(json.dumps({"session": sid, **state}, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "handoff-path":
        print(handoff_path(sid))
        return 0

    if args.cmd == "approve":
        path = Path(args.handoff) if args.handoff else handoff_path(sid)
        if not path.exists():
            body = f"# Handoff\n\nFocus for this compaction: {args.focus or 'not specified'}\n"
            path.write_text(body, encoding="utf-8")
        elif path != handoff_path(sid):
            handoff_path(sid).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        state.update({"mode": "approved", "snooze": None,
                      "focus": args.focus, "handoff": str(handoff_path(sid))})
        cl.save_state(sid, state)
        print(f"approved; handoff saved at {handoff_path(sid)}")
        return 0

    if args.cmd == "snooze":
        raw = args.until.strip().lower()
        if raw == "session":
            snooze = {"kind": "session"}
        elif raw.startswith("prompts:"):
            snooze = {"kind": "prompts", "value": int(raw.split(":", 1)[1]),
                      "start_prompt": int(state.get("prompt_count", 0))}
        elif raw.startswith("pct:"):
            snooze = {"kind": "pct", "value": float(raw.split(":", 1)[1])}
        else:
            print("--until must be prompts:N, pct:N or session", file=sys.stderr)
            return 1
        state.update({"mode": "snoozed", "snooze": snooze})
        cl.save_state(sid, state)
        print(f"snoozed: {cl.describe_snooze(state)}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
