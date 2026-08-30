#!/usr/bin/env python3
"""Set the auto-compact threshold in ~/.claude/settings.json.

Claude Code decides when to auto-compact from CLAUDE_AUTOCOMPACT_PCT_OVERRIDE
(default behaviour is roughly 95%). This plugin's gate only ever runs when that
threshold is crossed, so the threshold is what makes "ask me at 40%" real.

    setup_threshold.py            # show the current value
    setup_threshold.py --set 40
    setup_threshold.py --unset    # back to Claude Code's default

Writes the existing file back untouched apart from env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE,
and keeps a .bak copy of whatever was there before.
"""

import argparse
import json
import sys
from pathlib import Path

KEY = "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"


def settings_file() -> Path:
    return Path.home() / ".claude" / "settings.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="value", type=int)
    ap.add_argument("--unset", action="store_true")
    ap.add_argument("--file", default="")
    args = ap.parse_args()

    path = Path(args.file) if args.file else settings_file()
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError as exc:
            print(f"{path} is not valid JSON ({exc}); fix it first.", file=sys.stderr)
            return 1

    env = data.get("env") or {}

    if args.value is None and not args.unset:
        print(env.get(KEY, "(not set — Claude Code default applies)"))
        return 0

    if args.value is not None and not 1 <= args.value <= 100:
        print("--set takes a percentage between 1 and 100", file=sys.stderr)
        return 1

    if path.is_file():
        path.with_suffix(".json.bak").write_text(
            path.read_text(encoding="utf-8"), encoding="utf-8"
        )

    if args.unset:
        env.pop(KEY, None)
    else:
        env[KEY] = str(args.value)

    if env:
        data["env"] = env
    else:
        data.pop("env", None)

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{KEY} = {env.get(KEY, '(removed)')} in {path}")
    print("Restart Claude Code for the change to take effect.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
