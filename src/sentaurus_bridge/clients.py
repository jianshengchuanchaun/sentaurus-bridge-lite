"""Generate reviewable client configuration without editing user settings."""
from __future__ import annotations
import json
from pathlib import Path
import sys


CLIENTS = ('codex', 'codebuddy', 'claude', 'minimax', 'kimi-code', 'kimi',
           'deepseek-harness', 'generic', 'opencode')


def client_config(client: str, env_path: str | Path, local_root: str | Path,
                  python: str | None = None) -> str:
    if client not in CLIENTS:
        raise ValueError('Unknown MCP client')
    command = python or sys.executable
    args = ['-m', 'sentaurus_bridge', '--env', str(Path(env_path).expanduser().resolve()),
            'mcp', '--local-root', str(Path(local_root).expanduser().resolve())]
    if client == 'deepseek-harness':
        # JSON strings/arrays are valid YAML scalars/flow sequences. This avoids
        # a runtime YAML dependency and safely escapes Windows paths.
        return '\n'.join([
            '# DeepSeek Harness Cordis overlay; pass to dsh web --patch <file>',
            '- insert:',
            '    - id: sentaurus-bridge',
            "      name: '@deepseek-ai/dsh-mcp-client'",
            '      config:',
            '        serverName: sentaurus',
            '        transport: stdio',
            '        command: ' + json.dumps(command, ensure_ascii=False),
            '        args: ' + json.dumps(args, ensure_ascii=False),
            '        cwd: ' + json.dumps(str(Path(local_root).expanduser().resolve()), ensure_ascii=False),
            '        env: {}', '',
        ])
    if client == 'codex':
        return '\n'.join([
            '[mcp_servers.sentaurus]',
            'command = ' + json.dumps(command, ensure_ascii=False),
            'args = ' + json.dumps(args, ensure_ascii=False),
            'startup_timeout_sec = 30', 'tool_timeout_sec = 360', '',
        ])
    if client == 'opencode':
        data = {'mcp': {'sentaurus': {'type': 'local', 'command': [command, *args], 'enabled': True}}}
    elif client in ('kimi-code', 'kimi'):
        # Kimi infers stdio from command; its per-server timeouts use milliseconds.
        data = {'mcpServers': {'sentaurus': {
            'command': command, 'args': args,
            'cwd': str(Path(local_root).expanduser().resolve()),
            'startupTimeoutMs': 30000, 'toolTimeoutMs': 360000,
        }}}
    else:
        data = {'mcpServers': {'sentaurus': {'type': 'stdio', 'command': command, 'args': args}}}
    return json.dumps(data, ensure_ascii=False, indent=2) + '\n'
