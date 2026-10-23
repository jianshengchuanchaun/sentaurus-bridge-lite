"""Configuration loading for sentaurus-bridge-lite."""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


DEFAULT_TOOLS = ("sdevice", "sde", "svisual", "swb")


def default_user_env_path() -> Path:
    return Path.home() / ".sentaurus-bridge" / ".env"


def resolve_env_path(explicit: str | Path | None = None, cwd: Path | None = None) -> Path | None:
    base = (cwd or Path.cwd()).resolve()
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_absolute():
            path = base / path
        return path.resolve()

    local_env = base / ".env"
    if local_env.is_file():
        return local_env

    user_env = default_user_env_path()
    if user_env.is_file():
        return user_env

    return None


def _strip_inline_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for i, ch in enumerate(value):
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch in ("'", '"'):
            if quote == ch:
                quote = None
            elif quote is None:
                quote = ch
            continue
        if ch == "#" and quote is None and (i == 0 or value[i - 1].isspace()):
            return value[:i].rstrip()
    return value.strip()


def _unquote(value: str) -> str:
    value = _strip_inline_comment(value.strip())
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_env_file(path: str | Path) -> dict[str, str]:
    env: dict[str, str] = {}
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f".env file not found: {p}")
    for raw_line in p.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        env[key] = _unquote(value)
    return env


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


def _int(value: str | None, default: int) -> int:
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _csv(value: str | None, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    if value is None or value.strip() == "":
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _split(value: str | None) -> tuple[str, ...]:
    if value is None or value.strip() == "":
        return ()
    return tuple(shlex.split(value, posix=os.name != "nt"))


@dataclass(frozen=True)
class BridgeConfig:
    remote_host: str
    remote_user: str = ""
    remote_port: int = 22
    ssh_key: str = ""
    ssh_config: str = ""
    jump_host: str = ""
    jump_user: str = ""
    ssh_alias: str = "sentaurus-vm"
    remote_workdir: str = "~/sentaurus-work"
    sentaurus_setup: str = ""
    sentaurus_init: str = ""
    sentaurus_root: str = ""
    remote_shell: str = "bash"
    sentaurus_tools: tuple[str, ...] = DEFAULT_TOOLS
    enable_x11: bool = False
    display: str = ""
    ssh_cmd: str = "ssh"
    scp_cmd: str = "scp"
    ssh_extra_args: tuple[str, ...] = ()
    login_shell: bool = True
    remote_python: str = "python3"
    desktop_user: str = ""
    env_path: Path | None = None

    @classmethod
    def from_mapping(cls, values: Mapping[str, str], env_path: Path | None = None) -> "BridgeConfig":
        return cls(
            remote_host=values.get("SB_REMOTE_HOST", "").strip(),
            remote_user=values.get("SB_REMOTE_USER", "").strip(),
            remote_port=_int(values.get("SB_REMOTE_PORT"), 22),
            ssh_key=values.get("SB_SSH_KEY", "").strip(),
            ssh_config=values.get("SB_SSH_CONFIG", "").strip(),
            jump_host=values.get("SB_JUMP_HOST", "").strip(),
            jump_user=values.get("SB_JUMP_USER", "").strip(),
            ssh_alias=values.get("SB_SSH_ALIAS", "sentaurus-vm").strip() or "sentaurus-vm",
            remote_workdir=values.get("SB_REMOTE_WORKDIR", "~/sentaurus-work").strip() or "~/sentaurus-work",
            sentaurus_setup=values.get("SB_SENTAURUS_SETUP", "").strip(),
            sentaurus_init=values.get("SB_SENTAURUS_INIT", "").strip(),
            sentaurus_root=values.get("SB_SENTAURUS_ROOT", "").strip(),
            remote_shell=values.get("SB_REMOTE_SHELL", "bash").strip() or "bash",
            sentaurus_tools=_csv(values.get("SB_SENTAURUS_TOOLS"), DEFAULT_TOOLS),
            enable_x11=_bool(values.get("SB_ENABLE_X11"), False),
            display=values.get("SB_DISPLAY", "").strip(),
            ssh_cmd=values.get("SB_SSH_CMD", "ssh").strip() or "ssh",
            scp_cmd=values.get("SB_SCP_CMD", "scp").strip() or "scp",
            ssh_extra_args=_split(values.get("SB_SSH_EXTRA_ARGS")),
            login_shell=_bool(values.get("SB_LOGIN_SHELL"), True),
            remote_python=values.get("SB_REMOTE_PYTHON", "python3").strip() or "python3",
            desktop_user=values.get("SB_DESKTOP_USER", "").strip(),
            env_path=env_path,
        )

    @property
    def target(self) -> str:
        if self.remote_user:
            return f"{self.remote_user}@{self.remote_host}"
        return self.remote_host

    @property
    def jump_target(self) -> str:
        if not self.jump_host:
            return ""
        if self.jump_user:
            return f"{self.jump_user}@{self.jump_host}"
        return self.jump_host

    @property
    def has_sentaurus_setup(self) -> bool:
        return bool(self.sentaurus_setup or self.sentaurus_init or self.sentaurus_root)


def load_config(explicit_env: str | Path | None = None, cwd: Path | None = None) -> BridgeConfig:
    env_path = resolve_env_path(explicit_env, cwd=cwd)
    values = dict(os.environ)
    if env_path is not None:
        # Explicit process settings (including MCP client env) take precedence.
        values = {**parse_env_file(env_path), **values}
    return BridgeConfig.from_mapping(values, env_path=env_path)
