import json
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest

from sentaurus_bridge.api import Bridge, BridgeError
from sentaurus_bridge.config import BridgeConfig


def test_worker_handles_shell_banner_and_uses_stdin_for_large_payload(tmp_path):
    bridge = Bridge(BridgeConfig(remote_host='vm'), tmp_path)
    response = subprocess.CompletedProcess([], 0, 'login banner\nSB_RESULT={"ok":true,"result":{"state":"completed"}}\n', '')
    with patch('sentaurus_bridge.api.subprocess.run', return_value=response) as run:
        assert bridge.status('a' * 32)['state'] == 'completed'
    call = run.call_args
    envelope = json.loads(call.kwargs['input'])
    assert envelope['request']['job_id'] == 'a' * 32
    assert 'BatchMode=yes' in call.args[0]
    assert len(call.args[0][-1]) < 4000  # worker source never exceeds Windows argv limits


def test_remote_error_is_not_reported_as_success(tmp_path):
    bridge = Bridge(BridgeConfig(remote_host='vm'), tmp_path)
    result = subprocess.CompletedProcess([], 0, 'SB_RESULT={"ok":false,"error":"outside workspace","error_type":"ValueError"}', '')
    with patch('sentaurus_bridge.api.subprocess.run', return_value=result):
        with pytest.raises(BridgeError, match='outside workspace'):
            bridge.read_text('../secret')


def test_submit_quotes_literal_arguments(tmp_path):
    bridge = Bridge(BridgeConfig(remote_host='vm', login_shell=False), tmp_path)
    with patch.object(bridge, '_request', return_value={}) as request:
        bridge.submit('sdevice', ['a; touch PWNED.cmd', '$(uname)'], timeout=60)
    payload = request.call_args.kwargs['argv'][-1]
    assert "'a; touch PWNED.cmd'" in payload
    assert "'$(uname)'" in payload
    assert request.call_args.kwargs['argv'][1] == '-c'


@pytest.mark.parametrize('timeout', [0, -1, 604801])
def test_invalid_deadlines_rejected(timeout, tmp_path):
    with pytest.raises(BridgeError, match='timeout'):
        Bridge(BridgeConfig(remote_host='vm'), tmp_path).submit('sdevice', [], timeout=timeout)


def test_unlisted_tool_cannot_be_submitted(tmp_path):
    with pytest.raises(BridgeError, match='SB_SENTAURUS_TOOLS'):
        Bridge(BridgeConfig(remote_host='vm'), tmp_path).submit('bash', ['-c', 'echo no'])


def test_local_path_traversal_and_overwrite_are_rejected(tmp_path):
    bridge = Bridge(BridgeConfig(remote_host='vm'), tmp_path)
    with pytest.raises(BridgeError, match='outside'):
        bridge._local_path('../secret')
    existing = tmp_path / 'result.csv'
    existing.write_text('keep me')
    with pytest.raises(BridgeError, match='exists'):
        bridge.download('result.csv', 'result.csv')
    assert existing.read_text() == 'keep me'


def test_failed_download_preserves_existing_file(tmp_path):
    bridge = Bridge(BridgeConfig(remote_host='vm'), tmp_path)
    target = tmp_path / 'result.csv'
    target.write_text('original')
    with patch.object(bridge, '_request', return_value={'path': '/work/result.csv'}), \
         patch.object(bridge, '_transfer', side_effect=BridgeError('disconnected')):
        with pytest.raises(BridgeError, match='disconnected'):
            bridge.download('result.csv', 'result.csv', overwrite=True)
    assert target.read_text() == 'original'
    assert not list(tmp_path.glob('.sbridge-*'))


def test_timeout_has_actionable_error(tmp_path):
    bridge = Bridge(BridgeConfig(remote_host='vm'), tmp_path)
    with patch('sentaurus_bridge.api.subprocess.run', side_effect=subprocess.TimeoutExpired('ssh', 45)):
        with pytest.raises(BridgeError, match='may still be running'):
            bridge.status('a' * 32)
