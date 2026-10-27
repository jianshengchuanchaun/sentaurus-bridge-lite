# Troubleshooting

[简体中文](TROUBLESHOOTING.md) | **English** · [Home](../README.en.md)

## SSH works, but MCP fails to connect

- Generate the configuration using the absolute path to a Python interpreter with `[mcp]` installed.
- Point `--env` to an absolute path and `--local-root` to an existing local project directory.
- MCP uses `BatchMode=yes`. Complete key authentication and host fingerprint verification in a terminal first.
- Run `python -m sentaurus_bridge --env /path/.env doctor --json` to check remote Python and executable paths.
- The remote worker requires Linux and Python 3.6+. Set `SB_REMOTE_PYTHON=/path/to/python3` to select an interpreter.

## Sentaurus tools do not appear in Kimi Code

- Generate settings with `client-config kimi-code` and merge them into `.kimi-code/mcp.json` in the working directory or user-level `~/.kimi-code/mcp.json`. If `KIMI_CODE_HOME` is set, check `mcp.json` in that directory.
- Enter the correct project, create a new Kimi session, and follow the working-directory trust prompt. Existing sessions do not automatically load newly added MCP servers.
- Check status with `/mcp` and settings with `/mcp-config`. A project server overrides the user-level server of the same name; check for outdated paths.
- If `kimi-code` is reported as an unknown client, upgrade the bridge to 0.2.1 or later. Consult the corresponding documentation for older Kimi CLI versions.
- Select K3.1 Pro through Kimi's `/model` command or desktop model selector. Resolve model access or thinking-mode errors using the [official model documentation](https://www.kimi.com/code/docs/kimi-code/models.html); model account settings do not belong in the bridge's `.env`.

## Profile errors on old CentOS installations

Some environments reference deleted software paths in `/etc/profile`. Set `SB_LOGIN_SHELL=0` and explicitly initialize the environment using `SB_SENTAURUS_ROOT`, `SB_SENTAURUS_INIT`, or `SB_SENTAURUS_SETUP`. The bridge does not modify the system profile.

## Chinese filenames and spaces

MCP requests use UTF-8 JSON sent over SSH stdin; file contents are transferred through SCP. If remote Python 3.6 starts with ASCII encoding, the worker tries an installed UTF-8 locale and restarts only itself, without changing the system locale. On an old system without a suitable UTF-8 locale, install one or upgrade remote Python.

The single-string CLI command `run "..."` retains shell semantics. MCP and `job submit` quote arguments as literal values. Keep this distinction in mind.

## Executables exist, but the simulation fails

`doctor` does not check out a license. Inspect `job logs <id>` for license, input syntax, and solver errors. `completed` only means the process returned 0; verify expected outputs and physical convergence as well. The bridge does not automatically restart license services or retry simulations.

## A job cannot be found / the client disconnected

Run `job list` using the same `.env` and workspace. Logs are stored in `<workspace>/.sbridge/jobs/`; job IDs are tied to that workspace.

Job states are `queued`, `running`, `completed`, `failed`, `cancelled`, `timed_out`, and `unknown`. After a VM restart or unexpected supervisor exit, a job may be marked `unknown`. Inspect logs and remaining processes before deciding to rerun it, to avoid using licenses for duplicate jobs.

`cancel` returns a cancellation request; confirm the final state with `status`. Normal child processes are terminated with the job's process group. Independent daemons that deliberately detach from the session are outside the bridge's supervision.

## The structure window is not visible

1. Log in to the VM's graphical desktop, then run `desktop list`.
2. For multiple desktop users, select one with `SB_DESKTOP_USER`. The bridge does not bypass X11 authorization.
3. If the SSH and desktop users differ, appropriate system permissions are required. When SSH uses root, the bridge uses `runuser` to launch as the desktop user.
4. The desktop user must be able to read the full path. Use a shared project directory instead of putting files for regular users under `/root`.
5. Inspect the `log_path` returned by `desktop open`. License or rendering errors can occur after launch.
6. Mesa is used by default; try `--no-mesa` if appropriate. Automatic discovery currently targets X11 desktops; native Wayland compatibility has not been verified.

`desktop open` launches on the VM's existing desktop. To forward a GUI to Windows over X11, use the original `gui --x11` command with a local X Server.

## Upgrading from 0.1

- The minimum local Python version is now 3.10; the remote worker supports Python 3.6.
- Process environment variables now take precedence over `.env`, allowing client-specific overrides.
- Four actual tool names are checked by default: `sde,sdevice,svisual,swb`. Configure additional tools through `SB_SENTAURUS_TOOLS`.
- Existing `run`, `push`, `pull`, `gui`, `ssh-config`, and optional `code` commands remain available.
