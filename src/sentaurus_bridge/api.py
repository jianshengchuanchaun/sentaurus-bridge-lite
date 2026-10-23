"""Structured bridge operations shared by the CLI and MCP server."""
from __future__ import annotations

import json
import shlex
import subprocess
from importlib import resources
from pathlib import Path, PurePosixPath
from typing import Any

from . import __version__
from .config import BridgeConfig
from .ssh import build_remote_payload, build_scp_base, build_ssh_base, remote_spec, subprocess_environment

_LOADER = "import json,sys;d=json.load(sys.stdin);n={'__name__':'__bridge__'};exec(d['source'],n);n['main'](d['request'],d['source'])"
# Python 3.6 on CentOS can start with an ASCII filesystem encoding even when
# UTF-8 locales exist. Re-exec before reading stdin; never modify system locale.
_BOOTSTRAP = '''import os,sys,locale
if sys.getfilesystemencoding().lower() not in ('utf-8', 'utf8'):
    for candidate in ('C.UTF-8', 'en_US.utf8', 'en_US.UTF-8'):
        try:
            locale.setlocale(locale.LC_CTYPE, candidate)
            if locale.nl_langinfo(locale.CODESET).lower() not in ('utf-8', 'utf8'):
                continue
        except (locale.Error, AttributeError):
            continue
        os.environ['LC_ALL'] = candidate
        os.execv(sys.executable, [sys.executable, '-c', %r])
%s
''' % (_LOADER, _LOADER)


class BridgeError(RuntimeError):
    """A recoverable configuration, transport, or remote-operation error."""


class Bridge:
    def __init__(self, config: BridgeConfig, local_root: str | Path = '.'):
        self.config = config
        self.local_root = Path(local_root).expanduser().resolve()

    def info(self) -> dict[str, Any]:
        return {'version': __version__, 'target': self.config.target,
                'remote_workspace': self.config.remote_workdir,
                'local_workspace': str(self.local_root),
                'tools': list(self.config.sentaurus_tools),
                'transport': 'OpenSSH', 'editor_required': False}

    def _request(self, operation: str, **parameters: Any) -> dict[str, Any]:
        if not self.config.remote_host or self.config.remote_host.startswith('-'):
            raise BridgeError('Set SB_REMOTE_HOST to an SSH host or alias')
        source = resources.files('sentaurus_bridge').joinpath('resources/remote_worker.py').read_text(encoding='utf-8')
        command = 'env PYTHONUTF8=1 ' + shlex.quote(self.config.remote_python) + ' -c ' + shlex.quote(_BOOTSTRAP)
        request = {'root': self.config.remote_workdir, 'operation': operation, **parameters}
        try:
            process = subprocess.run(build_ssh_base(self.config, batch=True) + [command],
                                     input=json.dumps({'request': request, 'source': source}),
                                     text=True, encoding='utf-8', errors='replace',
                                     capture_output=True, timeout=45, check=False, env=subprocess_environment())
        except subprocess.TimeoutExpired as exc:
            raise BridgeError('SSH request timed out. A submitted job may still be running; check its directory before retrying') from exc
        except OSError as exc:
            raise BridgeError('Cannot start SSH: ' + str(exc)) from exc
        for line in reversed(process.stdout.splitlines()):
            if line.startswith('SB_RESULT='):
                response = json.loads(line[len('SB_RESULT='):])
                if not response['ok']:
                    raise BridgeError(response['error_type'] + ': ' + response['error'])
                return response['result']
        raise BridgeError('Remote worker failed (exit {}): {}'.format(
            process.returncode, (process.stderr or process.stdout)[-8192:]))

    def _argv(self, command: str) -> list[str]:
        payload = build_remote_payload(self.config, command)
        return [self.config.remote_shell, '-lc' if self.config.login_shell else '-c', payload]

    def doctor(self) -> dict[str, Any]:
        commands = ['missing=0']
        for tool in self.config.sentaurus_tools:
            q = shlex.quote(tool)
            commands.append("p=$(command -v {} 2>/dev/null) || missing=1; printf 'SB_TOOL\\t%s\\t%s\\n' {} \"$p\"".format(q, q))
        commands.append('exit $missing')
        if Path(self.config.remote_shell).name not in ('bash', 'sh', 'zsh', 'ksh'):
            raise BridgeError('Structured doctor requires a POSIX shell; use SB_REMOTE_SHELL=bash')
        return self._request('doctor', argv=self._argv('\n'.join(commands)))

    def submit(self, tool: str, arguments: list[str], workdir: str = '.', timeout: int = 3600) -> dict[str, Any]:
        if tool not in self.config.sentaurus_tools:
            raise BridgeError('Tool must be listed in SB_SENTAURUS_TOOLS: ' + ', '.join(self.config.sentaurus_tools))
        if not 1 <= timeout <= 604800:
            raise BridgeError('Job timeout must be between 1 and 604800 seconds')
        if len(arguments) > 200 or any('\x00' in value for value in [tool, *arguments]):
            raise BridgeError('Invalid tool arguments')
        return self._request('submit', tool=tool, arguments=arguments, workdir=workdir,
                             timeout=timeout, argv=self._argv(shlex.join([tool, *arguments])))

    def status(self, job_id: str) -> dict[str, Any]:
        return self._request('status', job_id=job_id)

    def jobs(self) -> dict[str, Any]:
        return self._request('jobs')

    def logs(self, job_id: str, max_bytes: int = 16384) -> dict[str, Any]:
        return self._request('logs', job_id=job_id, max_bytes=max_bytes)

    def cancel(self, job_id: str) -> dict[str, Any]:
        return self._request('cancel', job_id=job_id)

    def list_files(self, path: str = '.') -> dict[str, Any]:
        return self._request('list', path=path)

    def read_text(self, path: str, max_bytes: int = 32768) -> dict[str, Any]:
        return self._request('read', path=path, max_bytes=max_bytes)

    def _local_path(self, value: str) -> Path:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = self.local_root / path
        path = path.resolve()
        if path != self.local_root and self.local_root not in path.parents:
            raise BridgeError('Local path is outside --local-root')
        return path

    def _transfer(self, source: str, destination: str) -> None:
        command = build_scp_base(self.config) + ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '--', source, destination]
        try:
            result = subprocess.run(command, text=True, encoding='utf-8', errors='replace',
                                    capture_output=True, timeout=300, check=False, env=subprocess_environment())
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise BridgeError('File transfer failed: ' + str(exc)) from exc
        if result.returncode:
            raise BridgeError('SCP failed: ' + result.stderr[-8192:])

    def upload(self, local_path: str, remote_path: str, overwrite: bool = False) -> dict[str, Any]:
        local = self._local_path(local_path)
        if not local.is_file():
            raise BridgeError('Upload requires one existing local file')
        remote = self._request('resolve', path=remote_path, exclusive=not overwrite)['path']
        self._request('resolve', path=str(PurePosixPath(remote).parent), mkdir=True)
        self._transfer(str(local), remote_spec(self.config, remote))
        return {'uploaded': True, 'remote_path': remote, 'bytes': local.stat().st_size}

    def download(self, remote_path: str, local_path: str, overwrite: bool = False) -> dict[str, Any]:
        local = self._local_path(local_path)
        if local.exists() and not overwrite:
            raise BridgeError('Local destination exists; use overwrite=True explicitly')
        remote = self._request('resolve', path=remote_path, must_exist=True)['path']
        local.parent.mkdir(parents=True, exist_ok=True)
        # Transfer into a sibling temporary file so interrupted downloads do not
        # corrupt an existing result. SCP receives paths as separate argv entries.
        import tempfile
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=local.parent, prefix='.sbridge-', delete=False) as file:
                temporary = Path(file.name)
            self._transfer(remote_spec(self.config, remote), str(temporary))
            temporary.replace(local)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return {'downloaded': True, 'local_path': str(local), 'bytes': local.stat().st_size}

    def desktops(self) -> dict[str, Any]:
        return self._request('desktops')

    def open_visual(self, path: str, mesa: bool = True) -> dict[str, Any]:
        remote = self._request('resolve', path=path, must_exist=True)['path']
        command = shlex.join(['svisual', *(['-mesa'] if mesa else []), remote])
        return self._request('open_visual', path=remote, desktop_user=self.config.desktop_user,
                             argv=self._argv(command))
