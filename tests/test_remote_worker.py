"""Real supervisor lifecycle tests, run on Linux CI without Sentaurus or SSH."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

import pytest

if sys.platform != 'linux':
    pytest.skip('Remote supervisor targets Linux', allow_module_level=True)

SOURCE = Path(__file__).parents[1] / 'src/sentaurus_bridge/resources/remote_worker.py'
spec = importlib.util.spec_from_file_location('worker', SOURCE)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


def request(root, operation, **kwargs):
    return worker.dispatch({'root': str(root), 'operation': operation, **kwargs}, SOURCE.read_text())


def submit(root, code, timeout=10):
    return request(root, 'submit', tool='python', arguments=['-c', code],
                   argv=[sys.executable, '-c', code], timeout=timeout, workdir='.')


def terminal(root, job):
    for _ in range(100):
        status = request(root, 'status', job_id=job['job_id'])
        if status['state'] not in ('queued', 'running'):
            return status
        time.sleep(0.1)
    request(root, 'cancel', job_id=job['job_id'])
    pytest.fail('Supervisor did not finish in time')


def test_success_failed_and_persistent_logs(tmp_path):
    assert request(tmp_path, 'jobs')['jobs'] == []
    job = submit(tmp_path, "import sys;print('stdout marker');print('stderr marker',file=sys.stderr)")
    assert terminal(tmp_path, job)['state'] == 'completed'
    logs = request(tmp_path, 'logs', job_id=job['job_id'])
    assert 'stdout marker' in logs['stdout']
    assert 'stderr marker' in logs['stderr']
    failed = submit(tmp_path, 'import sys;sys.exit(7)')
    status = terminal(tmp_path, failed)
    assert status['state'] == 'failed' and status['returncode'] == 7
    assert {row['job_id'] for row in request(tmp_path, 'jobs')['jobs']} == {job['job_id'], failed['job_id']}


def test_timeout_and_cancel(tmp_path):
    job = submit(tmp_path, 'import time;time.sleep(30)', timeout=1)
    assert terminal(tmp_path, job)['state'] == 'timed_out'
    job = submit(tmp_path, 'import time;time.sleep(30)')
    assert request(tmp_path, 'cancel', job_id=job['job_id'])['cancel_requested']
    assert terminal(tmp_path, job)['state'] == 'cancelled'
    assert not request(tmp_path, 'cancel', job_id=job['job_id'])['cancel_requested']


def test_paths_and_symlinks_cannot_escape_workspace(tmp_path):
    (tmp_path / 'outside').symlink_to(tmp_path.parent)
    for path in ('../secret', 'outside/secret', '.sbridge/jobs/x'):
        with pytest.raises(ValueError):
            request(tmp_path, 'resolve', path=path)
    with pytest.raises(ValueError):
        request(tmp_path, 'status', job_id='../../etc/passwd')


def test_partial_logs_and_bounded_reads(tmp_path):
    (tmp_path / 'text').write_text('a' * 100)
    result = request(tmp_path, 'read', path='text', max_bytes=10)
    assert result['text'] == 'a' * 10 and result['truncated']
    job = submit(tmp_path, "print('a'*100)")
    terminal(tmp_path, job)
    result = request(tmp_path, 'logs', job_id=job['job_id'], max_bytes=10)
    assert len(result['stdout']) == 10 and result['stdout_truncated']


def test_stale_runner_is_unknown_not_success(tmp_path):
    job_id = 'a' * 32
    directory = worker.job_directory(tmp_path, job_id)
    directory.mkdir(parents=True)
    worker.save_json(directory / 'status.json', {'state': 'running', 'runner_pid': os.getpid(),
                                               'runner_token': 'wrong-start-time'})
    assert request(tmp_path, 'status', job_id=job_id)['state'] == 'unknown'


def test_missing_executable_reports_failure(tmp_path):
    job = request(tmp_path, 'submit', tool='missing', arguments=[], argv=['/no/such/tool'], timeout=5)
    assert terminal(tmp_path, job)['state'] == 'failed'


def test_cancel_stops_descendant_which_ignores_term(tmp_path):
    code = "import signal,time,os,pathlib;signal.signal(signal.SIGTERM,signal.SIG_IGN);pathlib.Path('child.pid').write_text(str(os.getpid()));time.sleep(60)"
    parent = 'import subprocess,sys,time;subprocess.Popen([sys.executable,"-c",' + repr(code) + ']);time.sleep(60)'
    job = submit(tmp_path, parent)
    for _ in range(50):
        if (tmp_path / 'child.pid').exists():
            break
        time.sleep(0.1)
    assert (tmp_path / 'child.pid').exists()
    pid = int((tmp_path / 'child.pid').read_text())
    request(tmp_path, 'cancel', job_id=job['job_id'])
    assert terminal(tmp_path, job)['state'] == 'cancelled'
    proc = Path('/proc/{}/stat'.format(pid))
    assert not proc.exists() or proc.read_text().rsplit(')', 1)[1].split()[0] == 'Z'
