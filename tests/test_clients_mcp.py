import asyncio
import json
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import pytest
import yaml
try:
    import tomllib
except ImportError:
    import tomli as tomllib

from sentaurus_bridge.clients import CLIENTS, client_config


@pytest.mark.parametrize('client', CLIENTS)
def test_client_config_round_trip(client, tmp_path):
    env = tmp_path / '配置 with spaces.env'
    executable = 'C:/Program Files/Python/python.exe'
    text = client_config(client, env, tmp_path, executable)
    if client == 'deepseek-harness':
        row = yaml.safe_load(text)[0]['insert'][0]
        assert row['name'] == '@deepseek-ai/dsh-mcp-client'
        assert row['config']['serverName'] == 'sentaurus'
        assert row['config']['command'] == executable
        assert str(env.resolve()) in row['config']['args']
        return
    parsed = tomllib.loads(text) if client == 'codex' else json.loads(text)
    if client == 'codex':
        entry = parsed['mcp_servers']['sentaurus']
    elif client == 'opencode':
        assert parsed['mcp']['sentaurus']['command'][0] == executable
        return
    else:
        entry = parsed['mcpServers']['sentaurus']
    assert entry['command'] == executable
    assert str(env.resolve()) in entry['args']
    assert '--local-root' in entry['args']


def test_real_stdio_mcp_handshake_tools_and_error_result(tmp_path):
    env_file = tmp_path / 'bridge.env'
    env_file.write_text('SB_REMOTE_HOST=not-connected.invalid\n', encoding='utf-8')

    async def exercise():
        parameters = StdioServerParameters(command=sys.executable, args=[
            '-m', 'sentaurus_bridge', '--env', str(env_file), 'mcp', '--local-root', str(tmp_path)])
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                names = {tool.name for tool in tools}
                assert {'bridge_info', 'submit_tool', 'job_status', 'job_logs',
                        'cancel_job', 'open_structure', 'upload_file'} <= names
                info = await session.call_tool('bridge_info', {})
                assert not info.isError
                assert info.structuredContent['editor_required'] is False
                result = await session.call_tool('submit_tool', {'tool': 'bash', 'arguments': []})
                assert result.isError  # refusal must be an MCP tool error, not a successful dict
                assert all(tool.inputSchema['type'] == 'object' for tool in tools)
    asyncio.run(exercise())
