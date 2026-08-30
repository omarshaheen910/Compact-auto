"""Shared helpers for the compact-auto hooks.

Design rule: never break the user's session. Every public helper degrades to a
safe default instead of raising, and every hook entry point wraps its work in a
try/except that exits 0 on failure (fail open = let Claude Code do its normal
thing).
"""

import json
import os
import sys
import time
from pathlib import Path

DEFAULT_WINDOW = 200_000
DEFAULT_ASK_PCT = 40.0
DEFAULT_HARD_PCT = 85.0
TAIL_BYTES = 2_000_000  # how much of the transcript tail we scan for usage data


def home() -> Path:
    """Directory holding per-session state and handoff notes."""
    p = Path(os.environ.get("COMPACT_AUTO_HOME", Path.home() / ".claude" / "compact-auto"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def env_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except Exception:
        return default


def ask_pct() -> float:
    return env_float("COMPACT_AUTO_ASK_PCT", DEFAULT_ASK_PCT)


def hard_pct() -> float:
    return env_float("COMPACT_AUTO_HARD_PCT", DEFAULT_HARD_PCT)


def read_input() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


# --------------------------------------------------------------------------- #
# state
# --------------------------------------------------------------------------- #

def _state_file(session_id: str) -> Path:
    safe = "".join(c for c in (session_id or "unknown") if c.isalnum() or c in "-_")[:80]
    return home() / f"state-{safe or 'unknown'}.json"


def load_state(session_id: str) -> dict:
    default = {
        "mode": "idle",          # idle | asking | approved | snoozed
        "prompt_count": 0,
        "snooze": None,          # {"kind": "prompts"|"pct"|"session", "value": N, "start_prompt": N}
        "focus": None,
        "handoff": None,
        "last_pct": 0.0,
        "updated_at": 0,
    }
    try:
        data = json.loads(_state_file(session_id).read_text(encoding="utf-8"))
        default.update({k: v for k, v in data.items() if k in default})
    except Exception:
        pass
    return default


def save_state(session_id: str, state: dict) -> None:
    try:
        state["updated_at"] = int(time.time())
        _state_file(session_id).write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def snooze_expired(state: dict, pct: float) -> bool:
    """A snooze that has run its course means we are allowed to ask again."""
    sn = state.get("snooze")
    if not sn:
        return True
    kind = sn.get("kind")
    if kind == "session":
        return False
    if kind == "prompts":
        start = int(sn.get("start_prompt", 0))
        return int(state.get("prompt_count", 0)) - start >= int(sn.get("value", 5))
    if kind == "pct":
        return pct >= float(sn.get("value", 50))
    return True


def describe_snooze(state: dict) -> str:
    sn = state.get("snooze") or {}
    kind = sn.get("kind")
    if kind == "prompts":
        done = int(state.get("prompt_count", 0)) - int(sn.get("start_prompt", 0))
        return f"postponed for {sn.get('value')} messages ({done} elapsed)"
    if kind == "pct":
        return f"postponed until context reaches {sn.get('value')}%"
    if kind == "session":
        return "postponed for the rest of this session"
    return "postponed"


# --------------------------------------------------------------------------- #
# context measurement
# --------------------------------------------------------------------------- #

def _tail_lines(path: Path):
    with path.open("rb") as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        fh.seek(max(0, size - TAIL_BYTES))
        chunk = fh.read()
    text = chunk.decode("utf-8", errors="ignore")
    return text.splitlines()


def _window_for(model: str) -> int:
    override = os.environ.get("COMPACT_AUTO_CONTEXT_WINDOW")
    if override:
        try:
            return int(override)
        except Exception:
            pass
    m = (model or "").lower()
    if "[1m]" in m or "1m" == m.split("-")[-1]:
        return 1_000_000
    return DEFAULT_WINDOW


def context_usage(transcript_path: str):
    """Return (used_tokens, window, pct).

    Claude Code does not hand hooks a context percentage, so we take it from the
    most recent assistant message in the transcript: its input tokens plus both
    cache buckets are, by definition, everything that was in the window on that
    request, and its output tokens are already part of the next one. Returns
    (0, window, 0.0) when the transcript is unreadable, which makes every caller
    fail open.
    """
    used, model = 0, ""
    try:
        p = Path(transcript_path)
        if p.is_file():
            for line in reversed(_tail_lines(p)):
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    continue
                msg = entry.get("message") or {}
                usage = msg.get("usage") or entry.get("usage") or {}
                if not usage:
                    continue
                total = (
                    int(usage.get("input_tokens", 0) or 0)
                    + int(usage.get("cache_read_input_tokens", 0) or 0)
                    + int(usage.get("cache_creation_input_tokens", 0) or 0)
                    + int(usage.get("output_tokens", 0) or 0)
                )
                if total > 0:
                    used = total
                    model = msg.get("model") or entry.get("model") or ""
                    break
    except Exception:
        pass
    window = _window_for(model)
    pct = round(used * 100.0 / window, 1) if used else 0.0
    return used, window, pct


def emit(payload: dict) -> None:
    """Hook stdout must contain the JSON object and nothing else."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()


def scripts_dir() -> str:
    return str(Path(__file__).resolve().parent)
