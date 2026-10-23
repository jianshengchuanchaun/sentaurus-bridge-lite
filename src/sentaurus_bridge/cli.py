"""Command line interface for sentaurus-bridge-lite."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path

from . import __version__
from .config import BridgeConfig, default_user_env_path, load_config, resolve_env_path
from .ssh import (
    build_ssh_base,
    call_interactive_shell,
    call_remote,
    command_from_args,
    local_tool_path,
    quote_remote,
    run_remote,
    scp_pull,
    scp_upload,
    ssh_config_block,
)


def _print_streams(stdout: str, stderr: str) -> None:
    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, end="", file=sys.stderr)


def _require_host(config: BridgeConfig) -> bool:
    if config.remote_host:
        return True
    print("SB_REMOTE_HOST is empty. Run `sentaurus-bridge init`, edit .env, then retry.", file=sys.stderr)
    return False


def _load(args: argparse.Namespace) -> BridgeConfig:
    return load_config(getattr(args, "env", None))


def _env_template_text() -> str:
    return (
        resources.files("sentaurus_bridge")
        .joinpath("resources")
        .joinpath(".env.example")
        .read_text(encoding="utf-8")
    )


def cmd_init(args: argparse.Namespace) -> int:
    dest = Path(args.path).expanduser() if args.path else Path.cwd() / ".env"
    if dest.exists() and not args.force:
        print(f".env already exists: {dest}")
        print("Use --force to overwrite it.")
        return 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_env_template_text(), encoding="utf-8")
    print(f"Created {dest}")
    print("Next: edit SB_REMOTE_HOST, SB_REMOTE_USER, and SB_SENTAURUS_SETUP, then run `sentaurus-bridge doctor`.")
    return 0


def _doctor_line(ok: bool, label: str, detail: str = "") -> None:
    prefix = "[ok]" if ok else "[!!]"
    if detail:
        print(f"{prefix} {label}: {detail}")
    else:
        print(f"{prefix} {label}")


def cmd_doctor(args: argparse.Namespace) -> int:
    if args.json:
        from .api import Bridge
        result = Bridge(_load(args)).doctor()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['ok'] else 3
    config = _load(args)
    env_path = resolve_env_path(args.env)
    _doctor_line(env_path is not None, "env file", str(env_path) if env_path else "not found; using process environment")

    ssh_path = local_tool_path(config.ssh_cmd)
    scp_path = local_tool_path(config.scp_cmd)
    _doctor_line(bool(ssh_path), "ssh", ssh_path or config.ssh_cmd)
    _doctor_line(bool(scp_path), "scp", scp_path or config.scp_cmd)
    if not ssh_path:
        return 2

    if not _require_host(config):
        return 2

    print(f"Target: {config.target}")
    if config.jump_target:
        print(f"Jump:   {config.jump_target}")

    probe = run_remote(
        config,
        "printf 'ssh-ok\\n'; uname -srm || true",
        include_setup=False,
        capture=True,
        timeout=args.timeout,
        batch=args.batch,
    )
    if probe.returncode != 0:
        _doctor_line(False, "ssh connection", f"failed with exit code {probe.returncode}")
        _print_streams(probe.stdout, probe.stderr)
        return probe.returncode or 1
    _doctor_line(True, "ssh connection")
    if args.verbose:
        _print_streams(probe.stdout, probe.stderr)

    if not config.has_sentaurus_setup:
        _doctor_line(False, "Sentaurus setup", "SB_SENTAURUS_SETUP/SB_SENTAURUS_INIT/SB_SENTAURUS_ROOT is empty")
        print("The SSH connection works, but Sentaurus may not be on PATH in non-interactive shells.")

    tools = " ".join(quote_remote(tool) for tool in config.sentaurus_tools)
    check_cmd = (
        "missing=0; "
        f"for tool in {tools}; do "
        "if command -v \"$tool\" >/dev/null 2>&1; then "
        "printf 'OK %s %s\\n' \"$tool\" \"$(command -v \"$tool\")\"; "
        "else printf 'MISS %s\\n' \"$tool\"; missing=1; fi; "
        "done; exit $missing"
    )
    tool_probe = run_remote(
        config,
        check_cmd,
        include_setup=True,
        capture=True,
        timeout=args.timeout,
        batch=args.batch,
    )
    ok = tool_probe.returncode == 0
    _doctor_line(ok, "Sentaurus tools", "all found" if ok else "some tools are missing")
    _print_streams(tool_probe.stdout, tool_probe.stderr)
    return 0 if ok else 3


def cmd_ssh(args: argparse.Namespace) -> int:
    config = _load(args)
    if not _require_host(config):
        return 2
    return call_interactive_shell(config, workdir=args.workdir)


def cmd_run(args: argparse.Namespace) -> int:
    config = _load(args)
    if not _require_host(config):
        return 2
    try:
        command = command_from_args(args.command)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    workdir = args.workdir or config.remote_workdir
    if args.push:
        local_dir = args.local_dir or "."
        rc = scp_upload(config, local_dir, workdir)
        if rc != 0:
            return rc
    rc = call_remote(config, command, workdir=workdir, include_setup=not args.no_setup, x11=args.x11 or config.enable_x11)
    if rc == 0 and args.pull:
        return scp_pull(config, workdir, args.pull_dir or "sentaurus-results")
    return rc


def cmd_gui(args: argparse.Namespace) -> int:
    config = _load(args)
    if not _require_host(config):
        return 2
    try:
        command = command_from_args(args.command) if args.command else "swb"
    except ValueError:
        command = "swb"
    workdir = args.workdir or config.remote_workdir
    x11 = args.x11 or config.enable_x11
    return call_remote(config, command, workdir=workdir, include_setup=True, x11=x11)


def cmd_which(args: argparse.Namespace) -> int:
    config = _load(args)
    if not _require_host(config):
        return 2
    tools = args.tools or list(config.sentaurus_tools)
    command = "; ".join(f"command -v {quote_remote(tool)} || true" for tool in tools)
    result = run_remote(config, command, include_setup=True, capture=True)
    _print_streams(result.stdout, result.stderr)
    return result.returncode


def cmd_push(args: argparse.Namespace) -> int:
    config = _load(args)
    if not _require_host(config):
        return 2
    remote_dir = args.remote_dir or config.remote_workdir
    return scp_upload(config, args.local_path, remote_dir)


def cmd_pull(args: argparse.Namespace) -> int:
    config = _load(args)
    if not _require_host(config):
        return 2
    remote_path = args.remote_path or config.remote_workdir
    local_dir = args.local_dir or "sentaurus-results"
    return scp_pull(config, remote_path, local_dir)


def _replace_marked_block(text: str, marker: str, block: str) -> str:
    start = f"# >>> sentaurus-bridge: {marker}"
    end = f"# <<< sentaurus-bridge: {marker}"
    wrapped = f"{start}\n{block.rstrip()}\n{end}\n"
    if start in text and end in text:
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        return before.rstrip() + "\n\n" + wrapped + after.lstrip()
    sep = "\n\n" if text.strip() else ""
    return text.rstrip() + sep + wrapped


def cmd_ssh_config(args: argparse.Namespace) -> int:
    config = _load(args)
    if not _require_host(config):
        return 2
    alias = args.alias or config.ssh_alias
    block = ssh_config_block(config, alias=alias)
    if not args.write:
        print(block, end="")
        return 0

    path = Path(args.path).expanduser() if args.path else Path.home() / ".ssh" / "config"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(_replace_marked_block(existing, alias, block), encoding="utf-8")
    print(f"Wrote SSH config block for Host {alias} to {path}")
    print(f"Connect with: ssh {alias} (VS Code Remote - SSH is optional).")
    return 0


def cmd_code(args: argparse.Namespace) -> int:
    config = _load(args)
    if not _require_host(config):
        return 2
    code = shutil.which(args.code_cmd)
    if not code:
        print(f"`{args.code_cmd}` was not found on PATH.", file=sys.stderr)
        return 2
    alias = args.alias or config.ssh_alias
    remote_path = args.remote_path or config.remote_workdir
    cmd = [code, "--remote", f"ssh-remote+{alias}", remote_path]
    return subprocess.call(cmd)


def cmd_info(args: argparse.Namespace) -> int:
    config = _load(args)
    print(f"sentaurus-bridge-lite {__version__}")
    print(f"env:     {config.env_path or '(process environment only)'}")
    print(f"target:  {config.target or '(missing SB_REMOTE_HOST)'}")
    print(f"workdir: {config.remote_workdir}")
    print(f"tools:   {', '.join(config.sentaurus_tools)}")
    print(f"x11:     {'enabled' if config.enable_x11 else 'disabled'}")
    return 0


def cmd_client_config(args: argparse.Namespace) -> int:
    from .clients import client_config
    path = resolve_env_path(args.env) or default_user_env_path()
    print(client_config(args.client, path, args.local_root, args.python), end='')
    return 0


def cmd_mcp(args: argparse.Namespace) -> int:
    from .api import Bridge
    from .mcp_server import create_server
    create_server(Bridge(_load(args), args.local_root)).run(transport='stdio')
    return 0


def cmd_job(args: argparse.Namespace) -> int:
    from .api import Bridge
    bridge = Bridge(_load(args))
    if args.action == 'submit':
        command = args.command[1:] if args.command[:1] == ['--'] else args.command
        if not command:
            raise ValueError('Provide a tool and arguments after --')
        result = bridge.submit(command[0], command[1:], args.workdir, args.timeout)
    elif args.action == 'list':
        result = bridge.jobs()
    elif args.action == 'logs':
        result = bridge.logs(args.job_id, args.max_bytes)
    else:
        result = getattr(bridge, args.action)(args.job_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_desktop(args: argparse.Namespace) -> int:
    from .api import Bridge
    bridge = Bridge(_load(args))
    result = bridge.desktops() if args.action == 'list' else bridge.open_visual(args.path, not args.no_mesa)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentaurus-bridge",
        description="CLI and MCP bridge for remote Sentaurus TCAD. No editor required.",
    )
    parser.add_argument("--env", help="Path to .env file. Default: ./.env, then ~/.sentaurus-bridge/.env")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="Create a local .env template")
    p.add_argument("--path", help="Destination .env path. Default: ./.env")
    p.add_argument("--force", action="store_true", help="Overwrite an existing file")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("doctor", help="Check SSH and Sentaurus command availability")
    p.add_argument("--timeout", type=int, default=30, help="SSH command timeout in seconds")
    p.add_argument("--batch", action="store_true", help="Use BatchMode=yes for key-only SSH checks")
    p.add_argument("--verbose", action="store_true", help="Print remote probe details")
    p.add_argument("--json", action="store_true", help="Structured agent diagnostics; requires remote Python 3.6+")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("ssh", help="Open an interactive SSH shell with Sentaurus setup loaded")
    p.add_argument("-w", "--workdir", help="Remote work directory")
    p.set_defaults(func=cmd_ssh)

    p = sub.add_parser("run", help="Run a command on the Sentaurus VM")
    p.add_argument("-w", "--workdir", help="Remote work directory. Default: SB_REMOTE_WORKDIR")
    p.add_argument("--push", action="store_true", help="Upload --local-dir to the remote workdir before running")
    p.add_argument("--local-dir", help="Local directory used with --push. Default: current directory")
    p.add_argument("--pull", action="store_true", help="Download the remote workdir after a successful command")
    p.add_argument("--pull-dir", help="Local download directory used with --pull. Default: sentaurus-results")
    p.add_argument("--x11", action="store_true", help="Enable SSH trusted X11 forwarding for this command")
    p.add_argument("--no-setup", action="store_true", help="Do not run Sentaurus setup before the command")
    p.add_argument("command", nargs=argparse.REMAINDER, help="Remote command, for example: -- sdevice nmos_des.cmd")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("gui", help="Launch a Sentaurus GUI command, for example: gui swb")
    p.add_argument("-w", "--workdir", help="Remote work directory. Default: SB_REMOTE_WORKDIR")
    p.add_argument("--x11", action="store_true", help="Enable SSH trusted X11 forwarding for this command")
    p.add_argument("command", nargs=argparse.REMAINDER, help="GUI command. Default: swb")
    p.set_defaults(func=cmd_gui)

    p = sub.add_parser("which", help="Show remote Sentaurus tool paths after setup")
    p.add_argument("tools", nargs="*", help="Tool names. Default: SB_SENTAURUS_TOOLS")
    p.set_defaults(func=cmd_which)

    p = sub.add_parser("push", help="Upload a local file or directory to the VM")
    p.add_argument("local_path", help="Local file or directory")
    p.add_argument("remote_dir", nargs="?", help="Remote destination directory. Default: SB_REMOTE_WORKDIR")
    p.set_defaults(func=cmd_push)

    p = sub.add_parser("pull", help="Download a remote file or directory from the VM")
    p.add_argument("remote_path", nargs="?", help="Remote path. Default: SB_REMOTE_WORKDIR")
    p.add_argument("local_dir", nargs="?", help="Local destination directory. Default: sentaurus-results")
    p.set_defaults(func=cmd_pull)

    p = sub.add_parser("ssh-config", help="Print or write an OpenSSH host alias (any SSH client)")
    p.add_argument("--alias", help="Host alias. Default: SB_SSH_ALIAS")
    p.add_argument("--write", action="store_true", help="Write/update the block in ~/.ssh/config")
    p.add_argument("--path", help="SSH config file path used with --write")
    p.set_defaults(func=cmd_ssh_config)

    p = sub.add_parser("code", help="Open a VS Code Remote - SSH window for the VM")
    p.add_argument("remote_path", nargs="?", help="Remote folder to open. Default: SB_REMOTE_WORKDIR")
    p.add_argument("--alias", help="Host alias. Default: SB_SSH_ALIAS")
    p.add_argument("--code-cmd", default="code", help="VS Code command. Default: code")
    p.set_defaults(func=cmd_code)

    p = sub.add_parser("info", help="Print resolved bridge configuration summary")
    p.set_defaults(func=cmd_info)

    from .clients import CLIENTS
    p = sub.add_parser('client-config', help='Print MCP configuration for an AI client; does not overwrite settings')
    p.add_argument('client', choices=CLIENTS)
    p.add_argument('--local-root', default='.', help='Local workspace accessible to MCP file transfers')
    p.add_argument('--python', help='Python executable containing this installation; defaults to current interpreter')
    p.set_defaults(func=cmd_client_config)

    p = sub.add_parser('mcp', help='Serve tools over stdio MCP (install the [mcp] extra)')
    p.add_argument('--local-root', default='.', help='Local workspace for MCP uploads/downloads')
    p.set_defaults(func=cmd_mcp)

    p = sub.add_parser('job', help='Submit, inspect, read logs or cancel a persistent remote job')
    job = p.add_subparsers(dest='action', required=True)
    listing = job.add_parser('list', help='Recover recent job IDs and states')
    listing.set_defaults(func=cmd_job)
    submit = job.add_parser('submit')
    submit.add_argument('-w', '--workdir', default='.', help='Directory relative to SB_REMOTE_WORKDIR')
    submit.add_argument('--timeout', type=int, default=3600, help='Remote execution deadline in seconds (max 7 days)')
    submit.add_argument('command', nargs=argparse.REMAINDER)
    submit.set_defaults(func=cmd_job)
    for action in ('status', 'logs', 'cancel'):
        command = job.add_parser(action)
        command.add_argument('job_id')
        if action == 'logs':
            command.add_argument('--max-bytes', type=int, default=16384)
        command.set_defaults(func=cmd_job)

    p = sub.add_parser('desktop', help='Discover VM X11 sessions and open a TDR on its desktop')
    desktop = p.add_subparsers(dest='action', required=True)
    command = desktop.add_parser('list')
    command.set_defaults(func=cmd_desktop)
    command = desktop.add_parser('open')
    command.add_argument('path', help='.tdr path inside SB_REMOTE_WORKDIR')
    command.add_argument('--no-mesa', action='store_true', help='Use the viewer default driver instead of software rendering')
    command.set_defaults(func=cmd_desktop)

    return parser


def main(argv: list[str] | None = None) -> int:
    # Deterministic UTF-8 for Windows clients, pipes and generated config files.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
