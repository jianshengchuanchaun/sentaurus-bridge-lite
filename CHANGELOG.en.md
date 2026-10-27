# Changelog

[简体中文](CHANGELOG.md) | **English** · [Home](README.en.md)

## 0.2.1 — 2026-10-24

- Added `client-config kimi-code` (alias `kimi`) to generate stdio MCP JSON for Kimi Code CLI / desktop.
- Kimi configuration explicitly sets the project directory, a 30-second startup timeout, and a 360-second tool timeout; it does not include model settings or API keys.
- Documented K3.1 Pro / Highspeed model selection, thinking mode, MCP configuration locations, and connection checks.
- Tested a real stdio MCP handshake, tool discovery, and calls using generated Kimi configuration; updated the homepage, quick start, and troubleshooting guide.

## 0.2.0 — 2026-10-23

- Repositioned the project as a standalone CLI / MCP bridge to remote Sentaurus, with VS Code as an optional entry point.
- Added optional integration with the official MCP Python SDK, providing structured diagnostics, file transfer, job management, and desktop visualization tools.
- Added configuration generators for Codex, CodeBuddy, MiniMax Code, official DeepSeek Harness, Claude Code, and OpenCode.
- Added persistent background jobs with listing, status, exit codes, logs, timeouts, and cancellation; jobs continue after the client disconnects.
- Added automatic discovery of VM X11 desktop sessions and opening of `.tdr` files as the desktop user, using Mesa rendering by default.
- Added local and remote workspace boundary checks for MCP file operations, no overwrite by default, and preservation of existing files when downloads are interrupted.
- Fixed `.env` BOM handling, environment-variable precedence, extra SCP arguments, initialization-file quoting in error messages, and remote UTF-8 compatibility.
- Added `SB_LOGIN_SHELL`, `SB_REMOTE_PYTHON`, and `SB_DESKTOP_USER`.
- Raised the minimum local Python version to 3.10; the remote worker requires only the Python 3.6+ standard library.
- Rewrote the Chinese README, quick start, client setup, and troubleshooting guides, distinguishing configuration compatibility from direct testing.

## 0.1.0

- Initial OpenSSH bridge: configuration, diagnostics, remote execution, file synchronization, and optional VS Code launch.
