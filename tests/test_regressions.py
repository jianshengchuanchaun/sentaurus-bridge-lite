import ast
import os
from pathlib import Path
import shlex

from sentaurus_bridge.config import BridgeConfig, load_config, parse_env_file
from sentaurus_bridge.ssh import build_remote_command, build_scp_base, ssh_config_block, subprocess_environment


def test_environment_overrides_env_file(monkeypatch, tmp_path):
    env = tmp_path / '.env'
    env.write_text('SB_REMOTE_HOST=file-vm\nSB_REMOTE_WORKDIR=~/file-work\n')
    monkeypatch.setenv('SB_REMOTE_HOST', 'process-vm')
    monkeypatch.delenv('SB_REMOTE_WORKDIR', raising=False)
    config = load_config(env)
    assert config.remote_host == 'process-vm'
    assert config.remote_workdir == '~/file-work'


def test_bom_file_is_supported(tmp_path):
    env = tmp_path / '.env'
    env.write_text('SB_REMOTE_HOST=vm\n', encoding='utf-8-sig')
    assert parse_env_file(env)['SB_REMOTE_HOST'] == 'vm'


def test_login_shell_is_optional():
    cfg = BridgeConfig(remote_host='vm', login_shell=False)
    assert shlex.split(build_remote_command(cfg, 'echo ok'))[:2] == ['bash', '-c']


def test_scp_inherits_ssh_options():
    cfg = BridgeConfig(remote_host='vm', ssh_extra_args=('-o', 'ServerAliveInterval=30'))
    assert build_scp_base(cfg)[-2:] == ['-o', 'ServerAliveInterval=30']


def test_init_path_does_not_inject_error_message():
    path = "/missing/a' ; touch PWNED ; echo '"
    cfg = BridgeConfig(remote_host='vm', sentaurus_init=path)
    payload = shlex.split(build_remote_command(cfg, ':'))[-1]
    assert shlex.quote('Sentaurus init file not found: ' + path) in payload


def test_remote_worker_keeps_python36_syntax():
    source = Path(__file__).parents[1] / 'src/sentaurus_bridge/resources/remote_worker.py'
    ast.parse(source.read_text(encoding='utf-8'), feature_version=(3, 6))


def test_ssh_config_preserves_key_path_spaces_and_x11_preference():
    config = BridgeConfig(remote_host='vm', ssh_key='C:/Users/A B/.ssh/id_ed25519')
    block = ssh_config_block(config)
    assert 'IdentityFile "C:/Users/A B/.ssh/id_ed25519"' in block
    assert 'ForwardX11 no' in block


def test_subprocess_environment_preserves_existing_settings(monkeypatch):
    monkeypatch.setenv('SB_TEST_SENTINEL', 'keep')
    assert subprocess_environment()['SB_TEST_SENTINEL'] == 'keep'


def test_windows_mcp_environment_recovers_programdata(monkeypatch):
    import pytest
    if os.name != 'nt':
        pytest.skip('Windows OpenSSH regression')
    monkeypatch.delenv('PROGRAMDATA', raising=False)
    env = subprocess_environment()
    assert Path(env['PROGRAMDATA']).is_dir()
