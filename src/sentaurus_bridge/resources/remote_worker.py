"""Private remote worker; Python 3.6+ standard library only, Linux required."""
import json
import os
from pathlib import Path
import pwd
import re
import signal
import subprocess
import sys
import time
import uuid


def save_json(path, value):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
    os.replace(str(temporary), str(path))


def confined(root, value):
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError('Path is outside SB_REMOTE_WORKDIR')
    if '.sbridge' in candidate.relative_to(root).parts:
        raise ValueError('The .sbridge job metadata directory is reserved')
    return candidate


def job_directory(root, job_id):
    if not re.fullmatch(r'[0-9a-f]{32}', job_id):
        raise ValueError('Invalid job ID')
    jobs = root / '.sbridge' / 'jobs'
    if root not in jobs.resolve().parents:
        raise ValueError('Job directory resolves outside the workspace')
    directory = jobs / job_id
    if directory.is_symlink():
        raise ValueError('Job directory must not be a symlink')
    return directory


def process_token(pid):
    try:
        # A start-time token prevents a reused PID from looking like our worker.
        return Path('/proc/{}/stat'.format(pid)).read_text().rsplit(')', 1)[1].split()[19]
    except (OSError, IndexError):
        return None


def stop_group(child):
    """Keep the leader unreaped until its process group has been terminated."""
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        exited = os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        if exited is not None:
            break
        time.sleep(0.1)
    # A zombie leader still owns its PID, so this cannot target a reused group.
    # Also stop descendants that ignored TERM after their parent exited.
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait()


def supervise(directory):
    request = json.loads((directory / 'request.json').read_text())
    status = json.loads((directory / 'status.json').read_text())
    child = None
    try:
        status.update(state='running', started_at=time.time(), runner_pid=os.getpid(),
                      runner_token=process_token(os.getpid()))
        save_json(directory / 'status.json', status)
        if (directory / 'cancel').exists():
            status.update(state='cancelled', returncode=None)
            return
        with (directory / 'stdout.log').open('wb') as stdout, (directory / 'stderr.log').open('wb') as stderr:
            child = subprocess.Popen(request['argv'], cwd=request['cwd'],
                                     stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                     start_new_session=True)
            started = time.monotonic()
            state = None
            while child.poll() is None:
                if (directory / 'cancel').exists():
                    state = 'cancelled'
                elif time.monotonic() - started > request['timeout']:
                    state = 'timed_out'
                if state:
                    # This live child's session belongs to this runner. No external PID kill API.
                    stop_group(child)
                    break
                time.sleep(0.2)
            status.update(state=state or ('completed' if child.returncode == 0 else 'failed'),
                          returncode=child.returncode)
    except Exception as exc:
        status.update(state='failed', error=str(exc), returncode=None)
    finally:
        status['finished_at'] = time.time()
        save_json(directory / 'status.json', status)


def read_status(directory):
    status = json.loads((directory / 'status.json').read_text())
    if status['state'] == 'running':
        if process_token(status['runner_pid']) != status.get('runner_token'):
            status.update(state='unknown', error='Job supervisor is no longer running; inspect logs before resubmitting')
    elif status['state'] == 'queued' and time.time() - status['created_at'] > 30:
        status.update(state='unknown', error='Job supervisor did not report startup; inspect runner.log')
    return status


def desktops():
    found = {}
    names = {'xfce4-session', 'gnome-session-binary', 'gnome-session', 'mate-session',
             'ksmserver', 'plasmashell', 'cinnamon-session'}
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            command = (proc / 'cmdline').read_bytes().split(b'\0')[0].decode()
            if Path(command).name not in names:
                continue
            uid = proc.stat().st_uid
            account = pwd.getpwuid(uid)
            env = dict(part.decode(errors='replace').split('=', 1)
                       for part in (proc / 'environ').read_bytes().split(b'\0') if b'=' in part)
            if not env.get('DISPLAY'):
                continue
            authority = env.get('XAUTHORITY') or str(Path(account.pw_dir) / '.Xauthority')
            found[(uid, env['DISPLAY'])] = {
                'user': account.pw_name, 'uid': uid, 'display': env['DISPLAY'],
                'xauthority': authority, 'home': account.pw_dir,
                'runtime_dir': env.get('XDG_RUNTIME_DIR', '/run/user/{}'.format(uid)),
                'dbus': env.get('DBUS_SESSION_BUS_ADDRESS', ''),
                'authority_exists': Path(authority).is_file(),
            }
        except (OSError, KeyError, ValueError):
            continue
    return list(found.values())


def dispatch(request, source):
    root = Path(request['root']).expanduser().resolve()
    operation = request['operation']
    if operation == 'doctor':
        result = subprocess.run(request['argv'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=20, universal_newlines=True)
        paths = {}
        for line in result.stdout.splitlines():
            if line.startswith('SB_TOOL\t'):
                _, tool, path = line.split('\t', 2)
                paths[tool] = path
        return {'ok': result.returncode == 0 and all(paths.values()) and bool(paths),
                'tools': paths, 'python': sys.version.split()[0], 'workspace': str(root),
                'setup_returncode': result.returncode, 'stderr': result.stderr[-8192:],
                'license_checked': False}
    if operation == 'desktops':
        return {'sessions': [{k: v for k, v in session.items() if k != 'dbus'} for session in desktops()]}
    if operation == 'jobs':
        jobs = job_directory(root, '0' * 32).parent
        if not jobs.exists():
            return {'jobs': [], 'truncated': False}
        directories = sorted((p for p in jobs.iterdir() if re.fullmatch(r'[0-9a-f]{32}', p.name)
                              and p.is_dir() and not p.is_symlink()),
                             key=lambda p: p.stat().st_mtime, reverse=True)
        results = []
        for directory in directories[:100]:
            try:
                results.append(read_status(directory))
            except (OSError, ValueError, KeyError) as exc:
                results.append({'job_id': directory.name, 'state': 'unknown', 'error': str(exc)})
        return {'jobs': results, 'truncated': len(directories) > 100}
    if operation in ('list', 'read', 'resolve'):
        path = confined(root, request.get('path', '.'))
        if operation == 'resolve':
            if request.get('mkdir'):
                path.mkdir(parents=True, exist_ok=True)
            if request.get('must_exist') and not path.exists():
                raise FileNotFoundError(str(path))
            if request.get('exclusive') and path.exists():
                raise FileExistsError('Destination exists; use overwrite=True explicitly')
            return {'path': str(path), 'exists': path.exists()}
        if operation == 'list':
            entries = []
            for entry in sorted(path.iterdir(), key=lambda p: p.name):
                if entry.name == '.sbridge':
                    continue
                if len(entries) == 200:
                    return {'entries': entries, 'truncated': True}
                entries.append({'name': entry.name, 'is_dir': entry.is_dir(),
                                'is_symlink': entry.is_symlink(), 'bytes': entry.lstat().st_size})
            return {'entries': entries, 'truncated': False}
        limit = max(1, min(65536, int(request.get('max_bytes', 32768))))
        with path.open('rb') as stream:
            data = stream.read(limit + 1)
        return {'path': str(path), 'text': data[:limit].decode('utf-8', errors='replace'),
                'truncated': len(data) > limit}
    if operation == 'submit':
        cwd = confined(root, request.get('workdir', '.'))
        if not cwd.is_dir():
            raise NotADirectoryError(str(cwd))
        job_id = uuid.uuid4().hex
        directory = job_directory(root, job_id)
        directory.mkdir(parents=True, mode=0o700)
        request['cwd'] = str(cwd)
        (directory / 'worker.py').write_text(source, encoding='utf-8')
        save_json(directory / 'request.json', request)
        status = {'job_id': job_id, 'state': 'queued', 'created_at': time.time(),
                  'workdir': str(cwd), 'tool': request['tool'], 'arguments': request['arguments'],
                  'timeout_seconds': request['timeout']}
        save_json(directory / 'status.json', status)
        with (directory / 'runner.log').open('wb') as log:
            subprocess.Popen([sys.executable, str(directory / 'worker.py'), '--job', str(directory)],
                             stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        return status
    if operation in ('status', 'logs', 'cancel'):
        directory = job_directory(root, request['job_id'])
        status = read_status(directory)
        if operation == 'cancel':
            if status['state'] in ('queued', 'running'):
                (directory / 'cancel').touch()
                return {'job_id': request['job_id'], 'state': status['state'], 'cancel_requested': True}
            return dict(status, cancel_requested=False)
        if operation == 'logs':
            result = {'job_id': request['job_id'], 'state': status['state']}
            limit = max(1, min(65536, int(request.get('max_bytes', 16384))))
            for name in ('stdout', 'stderr', 'runner'):
                path = directory / (name + '.log')
                if path.exists():
                    with path.open('rb') as log:
                        size = log.seek(0, 2)
                        log.seek(max(0, size - limit))
                        result[name] = log.read(limit).decode('utf-8', errors='replace')
                    result[name + '_truncated'] = size > limit
                else:
                    result[name] = ''
                    result[name + '_truncated'] = False
            return result
        return status
    if operation == 'open_visual':
        path = confined(root, request['path'])
        if not path.is_file() or path.suffix.lower() != '.tdr':
            raise ValueError('Open an existing .tdr structure or solution file')
        sessions = [s for s in desktops() if s['authority_exists']]
        if request.get('desktop_user'):
            sessions = [s for s in sessions if s['user'] == request['desktop_user']]
        if len(sessions) != 1:
            raise ValueError('Expected one readable X11 desktop session; log in to the VM and set SB_DESKTOP_USER if needed')
        session = sessions[0]
        env = os.environ.copy()
        env.update(HOME=session['home'], USER=session['user'], LOGNAME=session['user'],
                   DISPLAY=session['display'], XAUTHORITY=session['xauthority'],
                   XDG_RUNTIME_DIR=session['runtime_dir'])
        if session['dbus']:
            env['DBUS_SESSION_BUS_ADDRESS'] = session['dbus']
        prefix = []
        if os.getuid() != session['uid']:
            if os.getuid() != 0:
                raise PermissionError('SSH user cannot launch on another user desktop; connect as the desktop user')
            prefix = ['runuser', '-u', session['user'], '--']
        check = subprocess.run(prefix + ['test', '-r', str(path)], env=env)
        if check.returncode:
            raise PermissionError('Desktop user cannot read this file. Use a workspace accessible to both SSH and desktop users')
        logs = root / '.sbridge' / 'gui'
        if root not in logs.resolve().parents:
            raise ValueError('GUI log directory is outside the workspace')
        logs.mkdir(parents=True, exist_ok=True)
        logfile = logs / (uuid.uuid4().hex + '.log')
        with logfile.open('wb') as log:
            process = subprocess.Popen(prefix + request['argv'], cwd=session['home'], env=env,
                                       stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                       start_new_session=True)
        time.sleep(1)
        code = process.poll()
        if code is not None and code != 0:
            raise RuntimeError('Viewer startup failed: ' + logfile.read_text(errors='replace')[-4096:])
        return {'state': 'launched', 'pid': process.pid, 'path': str(path),
                'desktop_user': session['user'], 'display': session['display'],
                'log_path': str(logfile), 'window_verified': False}
    raise ValueError('Unsupported operation: ' + operation)


def main(request, source):
    try:
        response = {'ok': True, 'result': dispatch(request, source)}
    except Exception as exc:
        response = {'ok': False, 'error': str(exc), 'error_type': type(exc).__name__}
    print('SB_RESULT=' + json.dumps(response, ensure_ascii=True))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--job':
        supervise(Path(sys.argv[2]))
