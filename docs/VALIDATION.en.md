# Validation record

[简体中文](VALIDATION.md) | **English** · [Home](../README.en.md)

Dates: 2026-10-23 to 2026-10-24. Core bridge and VM acceptance testing: version 0.2.0. Kimi integration update: version 0.2.1.

## Local automated checks

Tests on Windows / Python 3.10 / MCP Python SDK 1.30.0 covered:

- Existing configuration parsing and SSH argument construction.
- `.env` BOM handling, environment-variable overrides, non-login shells, and quoting of initialization paths.
- Recovery of the ProgramData path required by OpenSSH in a minimal Windows MCP environment.
- Rejection of paths outside configured roots, no overwrite by default, and preservation of existing files when a download fails.
- Parsing Codex TOML, CodeBuddy/MiniMax/Kimi Code/Claude/OpenCode JSON, and DeepSeek Harness Cordis YAML.
- Absolute paths and millisecond timeout settings for Kimi Code and its `kimi` alias, plus a real stdio MCP handshake, tool discovery, and calls launched from the generated configuration.
- Real stdio MCP `initialize`, `tools/list`, `tools/call`, structured results, and error responses.

Linux-specific tests exercise actual background processes: normal exit, failure, timeout, cancellation, bounded log output, job recovery, stale supervisors, path traversal and symlinks, and cleanup of child processes that ignore TERM. CI runs on Ubuntu / Windows with Python 3.10 / 3.12 and does not require a Sentaurus license.

## Real VM acceptance testing

Testing used an existing Linux VM, remote Python 3.6.8, and Sentaurus W-2024.09-SP1. The input was the user's private two-dimensional NMOS project and was not uploaded with the source code.

| Check | Result |
| --- | --- |
| SSH, remote Python, and SDE/SDevice/SVisual/SWB paths | Passed |
| Upload / read filenames containing Chinese characters, spaces, single quotes, and shell punctuation | Passed |
| Downloaded SHA-256 matches the original file | Passed |
| Job returning exit code 7 | Correctly recorded `failed` and the exit code |
| Job exceeding its time limit | Correctly recorded `timed_out` |
| Explicitly cancelled job | Correctly recorded `cancelled` |
| SDE + Mesh background job | Returned 0 and generated a TDR with 10,543 mesh vertices |
| SDevice background job | Returned 0; logs confirmed completion of curve tracing; generated solution TDR and current files |
| Query after client disconnection | Recovered status and logs through the job ID / `list_jobs` |
| Structure viewer | Discovered the existing tcad X11 desktop and launched SVisual as that user |
| Actual stdio MCP calls through SSH | `bridge_doctor`, `list_jobs`, and result-file inspection passed |

The graphical launch interface explicitly returns `window_verified: false`; starting a process is not treated as proof of a visible window. Executable availability and license availability are also assessed separately. The actual SDE/SDevice runs used the remote machine's existing license.

## Scope of validation

- **Tested directly:** the bridge CLI / Python API, stdio MCP protocol calls through the official SDK, real SSH file transfers, and Sentaurus execution.
- **Configuration adapted and checked:** Codex, CodeBuddy, MiniMax Code, Kimi Code CLI / desktop app, official DeepSeek Harness, Claude Code, and OpenCode.
- **Not claimed as verified:** the complete UI workflow of every client version, actual API accounts for every model service, the physical correctness of model-generated TCAD inputs, native Wayland, or other Sentaurus versions.

No paid model calls were made using MiniMax, Kimi, or DeepSeek API keys. A standard MCP SDK handshake is not considered full validation of those clients' UI or model workflows. Accounts and model settings are managed by the respective clients. DeepSeek Harness was in developer preview at the time of these checks; after upgrading a client, repeat actual MCP tool calls to verify the connection.
