"""OpenSSH based transport helpers."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .config import BridgeConfig


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def quote_remote(value: str) -> str:
    return shlex.quote(value)


def quote_remote_path(value: str) -> str:
    """Quote a remote shell path while preserving leading tilde expansion."""
    if value == "~":
        return value
    if value.startswith("~/"):
        rest = value[2:]
        if not rest:
            return "~/"
        return "~/" + quote_remote(rest)
    return quote_remote(value)


def command_from_args(args: Sequence[str]) -> str:
    cleaned = list(args)
    if cleaned and cleaned[0] == "--":
        cleaned = cleaned[1:]
    if not cleaned:
        raise ValueError("missing remote command")
    if len(cleaned) == 1:
        return cleaned[0]
    return " ".join(shlex.quote(item) for item in cleaned)


def local_tool_path(tool: str) -> str | None:
    expanded = os.path.expanduser(os.path.expandvars(tool))
    if Path(expanded).is_file():
        return expanded
    return shutil.which(tool)


def subprocess_environment() -> dict[str, str]:
    """Windows OpenSSH exits 255 silently when an MCP host removes ProgramData."""
    env = dict(os.environ)
    if os.name == 'nt' and not any(key.upper() == 'PROGRAMDATA' for key in env):
        import ctypes
        directory = ctypes.create_unicode_buffer(32768)
        # Ask Windows for Common AppData; do not assume a C: drive or path.
        if ctypes.windll.shell32.SHGetFolderPathW(None, 0x23, None, 0, directory) == 0:
            env['PROGRAMDATA'] = directory.value
    return env


def build_ssh_base(
    config: BridgeConfig,
    *,
    x11: bool = False,
    tty: bool = False,
    batch: bool = False,
    connect_timeout: int | None = 10,
) -> list[str]:
    cmd = [config.ssh_cmd]
    if config.remote_port and config.remote_port != 22:
        cmd += ["-p", str(config.remote_port)]
    if config.ssh_key:
        cmd += ["-i", os.path.expanduser(os.path.expandvars(config.ssh_key))]
    if config.ssh_config:
        cmd += ["-F", os.path.expanduser(os.path.expandvars(config.ssh_config))]
    if config.jump_target:
        cmd += ["-J", config.jump_target]
    if x11:
        cmd += ["-Y"]
    if tty:
        cmd += ["-tt"]
    if batch:
        cmd += ["-o", "BatchMode=yes"]
    if connect_timeout is not None:
        cmd += ["-o", f"ConnectTimeout={connect_timeout}"]
    cmd += list(config.ssh_extra_args)
    cmd += ["--"]
    cmd.append(config.target)
    return cmd


def build_scp_base(config: BridgeConfig) -> list[str]:
    cmd = [config.scp_cmd]
    if config.remote_port and config.remote_port != 22:
        cmd += ["-P", str(config.remote_port)]
    if config.ssh_key:
        cmd += ["-i", os.path.expanduser(os.path.expandvars(config.ssh_key))]
    if config.ssh_config:
        cmd += ["-F", os.path.expanduser(os.path.expandvars(config.ssh_config))]
    if config.jump_target:
        cmd += ["-J", config.jump_target]
    cmd += list(config.ssh_extra_args)
    return cmd


def _is_csh(shell: str) -> bool:
    name = Path(shell).name.lower()
    return name in {"csh", "tcsh"}


def build_remote_payload(
    config: BridgeConfig,
    command: str,
    *,
    workdir: str | None = None,
    include_setup: bool = True,
    include_display: bool = False,
    interactive_shell: bool = False,
) -> str:
    shell_is_csh = _is_csh(config.remote_shell)
    parts: list[str] = []

    if not shell_is_csh:
        parts.append("set -e")
        if include_display and config.display:
            parts.append(f"export DISPLAY={quote_remote(config.display)}")
        if include_setup and config.sentaurus_root:
            root = config.sentaurus_root.rstrip("/")
            parts.append(f"export STROOT={quote_remote(root)}")
            parts.append(f"export PATH={quote_remote(root + '/bin')}:$PATH")
        if include_setup and config.sentaurus_init:
            init = quote_remote(config.sentaurus_init)
            parts.append(
                f"if [ -f {init} ]; then source {init}; "
                f"else printf '%s\\n' {quote_remote('Sentaurus init file not found: ' + config.sentaurus_init)} >&2; exit 86; fi"
            )
        if include_setup and config.sentaurus_setup:
            parts.append(config.sentaurus_setup)
        if workdir:
            q_workdir = quote_remote_path(workdir)
            parts.append(f"mkdir -p {q_workdir}")
            parts.append(f"cd {q_workdir}")
        if interactive_shell:
            parts.append('exec "${SHELL:-bash}" -l')
        else:
            parts.append(command)
        return "\n".join(parts)

    if include_display and config.display:
        parts.append(f"setenv DISPLAY {quote_remote(config.display)}")
    if include_setup and config.sentaurus_root:
        root = config.sentaurus_root.rstrip("/")
        parts.append(f"setenv STROOT {quote_remote(root)}")
        parts.append(f"setenv PATH {quote_remote(root + '/bin')}:$PATH")
    if include_setup and config.sentaurus_setup:
        parts.append(config.sentaurus_setup)
    elif include_setup and config.sentaurus_init:
        parts.append(f"source {quote_remote(config.sentaurus_init)}")
    if workdir:
        q_workdir = quote_remote_path(workdir)
        parts.append(f"mkdir -p {q_workdir}")
        parts.append(f"cd {q_workdir}")
    if interactive_shell:
        parts.append("exec $SHELL -l")
    else:
        parts.append(command)
    return "\n".join(parts)


def build_remote_command(
    config: BridgeConfig,
    command: str,
    *,
    workdir: str | None = None,
    include_setup: bool = True,
    include_display: bool = False,
    interactive_shell: bool = False,
) -> str:
    payload = build_remote_payload(
        config,
        command,
        workdir=workdir,
        include_setup=include_setup,
        include_display=include_display,
        interactive_shell=interactive_shell,
    )
    shell = config.remote_shell or "bash"
    flag = "-lc" if config.login_shell else "-c"
    return f"{quote_remote(shell)} {flag} {quote_remote(payload)}"


def run_remote(
    config: BridgeConfig,
    command: str,
    *,
    workdir: str | None = None,
    include_setup: bool = True,
    x11: bool = False,
    capture: bool = True,
    timeout: int | None = None,
    batch: bool = False,
) -> CommandResult:
    remote_command = build_remote_command(
        config,
        command,
        workdir=workdir,
        include_setup=include_setup,
        include_display=x11,
    )
    cmd = build_ssh_base(config, x11=x11, batch=batch) + [remote_command]
    proc = subprocess.run(
        cmd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=capture,
        timeout=timeout,
        check=False,
        env=subprocess_environment(),
    )
    return CommandResult(
        proc.returncode,
        proc.stdout or "",
        proc.stderr or "",
    )


def call_remote(
    config: BridgeConfig,
    command: str,
    *,
    workdir: str | None = None,
    include_setup: bool = True,
    x11: bool = False,
) -> int:
    remote_command = build_remote_command(
        config,
        command,
        workdir=workdir,
        include_setup=include_setup,
        include_display=x11,
    )
    cmd = build_ssh_base(config, x11=x11) + [remote_command]
    return subprocess.call(cmd, env=subprocess_environment())


def call_interactive_shell(config: BridgeConfig, *, workdir: str | None = None) -> int:
    if config.has_sentaurus_setup or workdir:
        remote_command = build_remote_command(
            config,
            ":",
            workdir=workdir,
            include_setup=True,
            include_display=False,
            interactive_shell=True,
        )
        return subprocess.call(build_ssh_base(config, tty=True) + [remote_command], env=subprocess_environment())
    return subprocess.call(build_ssh_base(config, tty=True), env=subprocess_environment())


def remote_spec(config: BridgeConfig, remote_path: str) -> str:
    return f"{config.target}:{remote_path}"


def scp_upload(config: BridgeConfig, local_path: str, remote_dir: str) -> int:
    local = str(Path(local_path).expanduser())
    mkdir = run_remote(
        config,
        f"mkdir -p {quote_remote_path(remote_dir)}",
        include_setup=False,
        capture=True,
    )
    if mkdir.returncode != 0:
        if mkdir.stdout:
            print(mkdir.stdout, end="")
        if mkdir.stderr:
            print(mkdir.stderr, end="")
        return mkdir.returncode
    cmd = build_scp_base(config) + ["-r", local, remote_spec(config, remote_dir.rstrip("/") + "/")]
    return subprocess.call(cmd, env=subprocess_environment())


def scp_pull(config: BridgeConfig, remote_path: str, local_dir: str) -> int:
    local = Path(local_dir).expanduser()
    local.mkdir(parents=True, exist_ok=True)
    cmd = build_scp_base(config) + ["-r", remote_spec(config, remote_path), str(local)]
    return subprocess.call(cmd, env=subprocess_environment())


def ssh_config_block(config: BridgeConfig, alias: str | None = None) -> str:
    host_alias = alias or config.ssh_alias
    lines = [
        f"Host {host_alias}",
        f"  HostName {config.remote_host}",
    ]
    if config.remote_user:
        lines.append(f"  User {config.remote_user}")
    if config.remote_port and config.remote_port != 22:
        lines.append(f"  Port {config.remote_port}")
    if config.ssh_key:
        identity = os.path.expanduser(os.path.expandvars(config.ssh_key)).replace('\\', '/')
        lines.append('  IdentityFile "' + identity.replace('"', '\\"') + '"')
    if config.jump_target:
        lines.append(f"  ProxyJump {config.jump_target}")
    lines += [
        f"  ForwardX11 {'yes' if config.enable_x11 else 'no'}",
        f"  ForwardX11Trusted {'yes' if config.enable_x11 else 'no'}",
        "  ServerAliveInterval 30",
    ]
    return "\n".join(lines) + "\n"
