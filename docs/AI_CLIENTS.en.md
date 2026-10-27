# AI client setup

[简体中文](AI_CLIENTS.md) | **English** · [Home](../README.en.md)

The MCP server runs on your local computer and connects to Sentaurus over SSH. Your AI client handles model inference, API keys, and permission approvals; the bridge provides file, job, and visualization tools. You do not need to deploy a model service on the VM.

## Common preparation

1. Install with `python -m pip install -e ".[mcp]"`.
2. Configure SSH and Sentaurus in `.env`, then run `doctor --json`.
3. Use absolute paths for `--env` and `--local-root` so clients launched from another directory load the correct configuration.
4. Merge the `client-config` output into your client settings, preserving existing servers. Do not put model API keys in the bridge configuration.

`mcp` is a stdio service. It is normal for it to start without an interactive prompt. Do not write `echo` messages, shell banners, or debugging output to its stdout.

## Codex

Generate TOML:

```bash
sentaurus-bridge --env /absolute/path/.env client-config codex --local-root /absolute/path/project
```

Merge it into Codex's `config.toml`, or add the server through the CLI:

```bash
codex mcp add sentaurus -- /absolute/path/to/python -m sentaurus_bridge --env /absolute/path/.env mcp --local-root /absolute/path/project
```

Use the Python interpreter where the bridge and its MCP extra are installed. After reloading MCP settings in the desktop client, actually call `bridge_info` and `bridge_doctor`. If the current session cannot load new tools dynamically, use the bridge CLI directly and enable MCP in a new session.

Official reference: [Codex MCP](https://developers.openai.com/codex/mcp). No VS Code plugin or Remote - SSH extension is required.

## CodeBuddy Code

```bash
sentaurus-bridge --env /absolute/path/.env client-config codebuddy --local-root /absolute/path/project
```

The output is stdio JSON containing `mcpServers.sentaurus`. Merge it at your chosen configuration scope and call `bridge_doctor` after starting the client. See the [CodeBuddy MCP documentation](https://www.codebuddy.cn/docs/cli/mcp) for scopes and file locations.

## MiniMax Code / MiniMax models

```bash
sentaurus-bridge --env /absolute/path/.env client-config minimax --local-root /absolute/path/project
```

Merge the generated JSON into `.mcp.json` in your MiniMax Code working directory. Configure the model, account, and API settings in MiniMax Code. Inspect the configuration with `/mcp`, then ask the model to call `bridge_doctor`; a listed configuration entry alone does not establish a working connection.

MiniMax can also serve as the model backend for other compatible clients. Generate the bridge configuration for **that client**: for example, `client-config claude` for Claude Code or `client-config opencode` for OpenCode.

References: [MiniMax Code project MCP](https://github.com/MiniMax-AI/minimax-code/blob/main/packages/local-runtime-v2/docs/project-mcp.md) and [MiniMax with Claude Code](https://platform.minimax.io/docs/coding-plan/claude-code). Model IDs and service endpoints can change; use the provider's current documentation and values available to your account.

## Kimi Code CLI / desktop app and K3.1 Pro

Kimi Code connects to the bridge through local stdio MCP. The CLI and desktop app share MCP configuration, with no VS Code requirement.

```bash
sentaurus-bridge --env /absolute/path/.env client-config kimi-code --local-root /absolute/path/project
```

`client-config kimi` is an alias for the same generator. Generate the configuration from a Python environment with `[mcp]` installed. The output contains `mcpServers.sentaurus`. Merge it as UTF-8 into either location below, preserving other servers:

- Project: `.kimi-code/mcp.json` in the working directory.
- User: `~/.kimi-code/mcp.json`, or `$KIMI_CODE_HOME/mcp.json` when `KIMI_CODE_HOME` is set.

A project server overrides a user-level server with the same name. You can also manage settings with `/mcp-config` in Kimi. The generator uses absolute paths for `command`, `.env`, and `cwd` to handle differences in working directory and PATH when launching the desktop app. Kimi infers stdio from `command`; timeout values are in milliseconds:

```json
{
  "mcpServers": {
    "sentaurus": {
      "command": "/absolute/path/to/python",
      "args": ["-m", "sentaurus_bridge", "--env", "/absolute/path/.env", "mcp", "--local-root", "/absolute/path/project"],
      "cwd": "/absolute/path/project",
      "startupTimeoutMs": 30000,
      "toolTimeoutMs": 360000
    }
  }
}
```

Tool-call timeouts and simulation run limits are managed separately. After `submit_tool` returns a job ID, SDE / SDevice runs in the VM's background. Query progress with `job_status` and `job_logs`. Set the simulation's own time limit through the `timeout_seconds` argument to `submit_tool`.

After saving the configuration, launch Kimi in your project directory and create a new session; existing sessions do not automatically register newly added servers. Follow the client's prompt to trust your own working directory, check the connection with `/mcp`, then send:

> Call mcp__sentaurus__bridge_info and mcp__sentaurus__bridge_doctor. Report the version, connection status, and remote tool checks.

**Select K3.1 Pro:** enter `/model` in the CLI or use the model selector in the desktop input box. The official model IDs are `k3.1-pro` and `k3.1-pro-highspeed`. Your account needs access, and thinking mode must be enabled for the K3.1 Pro family. Start a new session when changing to a new model. The bridge configuration does not pin a model ID or store your Kimi account or model API key, so changing models does not require changing the SSH tools.

If you use Kimi as another client's model backend, configure that client's model according to Kimi's official instructions and generate its corresponding MCP configuration, such as `client-config opencode`. This project does not implement a separate Kimi API inference loop.

Last checked: 2026-10-24. References: [Kimi MCP configuration](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/mcp.html), [desktop MCP](https://www.kimi.com/code/docs/en/kimi-code-desktop/settings-and-extensions.html), and [model selection and K3.1 Pro](https://www.kimi.com/code/docs/kimi-code/models.html). Older Kimi CLI versions may use different paths and commands; consult the documentation for your installed version. Configuration generation and a standard MCP handshake were verified; no model request was made using a Kimi account.

## Official DeepSeek Harness (dsh)

This integration targets the [official open-source DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness). It uses Cordis plugin configuration. The bridge connects through the official `@deepseek-ai/dsh-mcp-client` plugin and does not implement its own DeepSeek API inference loop.

Generate the configuration:

```bash
sentaurus-bridge --env /absolute/path/.env client-config deepseek-harness --local-root /absolute/path/project
```

Save the output as `sentaurus.cordis.yml` in UTF-8. Its structure is shown below; the generator inserts your actual paths:

```yaml
- insert:
    - id: sentaurus-bridge
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: sentaurus
        transport: stdio
        command: /absolute/path/to/python
        args: ["-m", "sentaurus_bridge", "--env", "/absolute/path/.env", "mcp", "--local-root", "/absolute/path/project"]
        cwd: /absolute/path/project
        env: {}
```

After installing the official Harness, start it with:

```bash
dsh web --patch /absolute/path/sentaurus.cordis.yml
```

You can also use `npx @deepseek-ai/dsh web --patch ...` as supported by the official distribution. Set the model under Settings → Models in the Web UI and select your project in the workspace selector. Wait for MCP tool discovery to finish, then request a call to `mcp__sentaurus__bridge_doctor`.

Harness filters some sensitive environment variables, so the bridge's `.env` is passed explicitly by absolute path. SSH private keys are still accessed through local paths. You do not need to put private key contents or model API keys in the YAML.

The official Harness was in developer preview when this integration was checked on 2026-10-23 and may introduce incompatible updates. References: [MCP plugin and Cordis overlays](https://deepseek-harness.github.io/deepseek-harness/en/guide/mcp-memory) and [Web UI](https://deepseek-harness.github.io/deepseek-harness/en/guide/quickstart).

## Other model providers and OpenCode

Clients that support tool execution and local MCP can use these tools. Configure the model provider in the client; there is no need to duplicate SSH logic for each model.

OpenCode uses `mcp.sentaurus` with `type: local`, generated by `client-config opencode`. Reference: [OpenCode MCP servers](https://opencode.ai/docs/mcp-servers/). An ordinary API client with only an OpenAI-compatible text interface and no tool-execution loop cannot run simulations through API compatibility alone.

## Tools and verification

| Tool | Purpose |
| --- | --- |
| `bridge_info` / `bridge_doctor` | Version and configuration / SSH and remote executable diagnostics |
| `list_remote_files` / `read_remote_text` | Inspect inputs, text results, and logs |
| `upload_file` / `download_file` | Transfer individual files; no overwrite by default |
| `submit_tool` | Submit an allowed executable with literal arguments |
| `list_jobs` / `job_status` / `job_logs` | Recover job IDs and inspect exit status and logs |
| `cancel_job` | Request cancellation of a managed job |
| `desktop_sessions` / `open_structure` | Discover X11 desktops and launch a TDR viewer |

Start with `bridge_info` and `bridge_doctor`, then validate the complete workflow with a small, trusted model. Check status, exit code, logs, and expected output files before treating a job as successful. A model saying "done" is not evidence of execution.

MCP path checks help prevent file-operation mistakes; they are not an operating-system sandbox. Running an SDE script authorizes script execution as the SSH user. Keep the client's normal tool approval settings and use an account with appropriate permissions.
