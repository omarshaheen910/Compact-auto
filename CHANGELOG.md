# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- `session_restore.py` used a PEP 604 annotation (`Path | None`) that is
  evaluated at definition time, so the module failed to import on Python 3.8 and
  3.9 despite those versions being listed as supported. Added
  `from __future__ import annotations`.

### Documentation

- Corrected the manual install path: a plugin auto-loads from
  `~/.claude/skills/<name>/`, not `~/.claude/plugins/<name>/`.
- Made the Windows `python3` caveat a first-class requirement rather than a
  footnote, with the symptom to look for.
- Added a Development section covering `--plugin-dir`, `claude plugin validate`,
  and driving a hook from the shell.
- Corrected the `context_usage` docstring, which described the token total as
  input plus cache buckets while the code also counts output tokens.

## [0.1.0] - 2026-08-30

### Added

- `PreCompact` gate that holds automatic compaction until the user approves it,
  with a hard ceiling at 85% so a postponement can never strand a full window.
- Handoff notes written before compaction and re-injected by a `SessionStart`
  hook afterwards, taking priority over the auto-generated summary.
- Three ways to postpone — N messages, a percentage, or the rest of the session —
  tracked by a `UserPromptSubmit` watcher.
- `setup_threshold.py` for setting `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`, which is
  what makes "ask me at 40%" actually fire.

[Unreleased]: https://github.com/omarshaheen910/Compact-auto/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/omarshaheen910/Compact-auto/releases/tag/v0.1.0
