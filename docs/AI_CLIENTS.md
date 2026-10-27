# AI 客户端接入

**简体中文** | [English](AI_CLIENTS.en.md) · [首页](../README.md)

本项目的 MCP 服务运行在你的电脑上，经 SSH 连接 Sentaurus。AI 客户端负责模型推理、API 密钥和权限审批；桥接提供文件、任务与可视化工具。无需把模型服务部署到虚拟机。

## 共同准备

1. 安装 `python -m pip install -e ".[mcp]"`。
2. 用 `.env` 配置 SSH 与 Sentaurus，完成 `doctor --json` 检查。
3. 使用绝对路径指定 `--env` 和 `--local-root`，避免客户端从别的目录启动时读错配置。
4. 将 `client-config` 的输出合并进客户端配置，保留原有服务器。不要把模型 API key 填入桥接配置。

`mcp` 是 stdio 服务，启动后没有普通交互提示是正常现象。不要用 `echo`、shell banner 或调试输出污染它的 stdout。

## Codex

生成 TOML：

```bash
sentaurus-bridge --env /absolute/path/.env client-config codex --local-root /absolute/path/project
```

合并到 Codex 的 `config.toml`，或通过 CLI 添加服务器：

```bash
codex mcp add sentaurus -- /absolute/path/to/python -m sentaurus_bridge --env /absolute/path/.env mcp --local-root /absolute/path/project
```

Python 必须是安装了桥接与 MCP extra 的解释器。桌面客户端重新载入 MCP 设置后，请实际调用 `bridge_info` 和 `bridge_doctor`。若当前会话不能动态加载新工具，可以先直接运行桥接 CLI，并在新会话启用 MCP。

官方配置依据：[Codex MCP](https://developers.openai.com/codex/mcp)。不需要 VS Code 插件或 Remote - SSH 扩展。

## CodeBuddy Code

```bash
sentaurus-bridge --env /absolute/path/.env client-config codebuddy --local-root /absolute/path/project
```

输出为带 `mcpServers.sentaurus` 的 stdio JSON。按客户端所选作用域合并，启动后实际调用 `bridge_doctor`。作用域与文件位置以 [CodeBuddy MCP 文档](https://www.codebuddy.cn/docs/cli/mcp) 为准。

## MiniMax Code / MiniMax 模型

```bash
sentaurus-bridge --env /absolute/path/.env client-config minimax --local-root /absolute/path/project
```

将生成的 JSON 合并到 MiniMax Code 工作目录的 `.mcp.json`。模型、账号及 API 配置仍在 MiniMax Code 中完成。在 `/mcp` 中查看配置，再要求模型调用 `bridge_doctor` 验证；仅出现配置条目不代表连接成功。

MiniMax 也可以作为其他兼容客户端的模型后端。此时应生成**对应客户端**的桥接配置，例如 Claude Code 用 `client-config claude`，OpenCode 用 `client-config opencode`。

依据：[MiniMax Code 项目 MCP](https://github.com/MiniMax-AI/minimax-code/blob/main/packages/local-runtime-v2/docs/project-mcp.md)、[MiniMax 接入 Claude Code](https://platform.minimax.io/docs/coding-plan/claude-code)。模型 ID 和服务地址可能更新，应使用提供商当前文档与账户可用值。

## Kimi Code CLI / 桌面端与 K3.1 Pro

Kimi Code 通过本地 stdio MCP 使用这套桥接，CLI 和桌面端共用 MCP 配置，不需要 VS Code。

```bash
sentaurus-bridge --env /absolute/path/.env client-config kimi-code --local-root /absolute/path/project
```

`client-config kimi` 是同一入口的别名。使用安装了 `[mcp]` 的 Python 环境生成配置。输出包含 `mcpServers.sentaurus`，以 UTF-8 合并到以下任一位置，并保留其他服务器：

- 当前项目：工作目录下的 `.kimi-code/mcp.json`。
- 用户级：`~/.kimi-code/mcp.json`；设置了 `KIMI_CODE_HOME` 时，使用 `$KIMI_CODE_HOME/mcp.json`。

项目同名服务器优先于用户级配置。也可在 Kimi 中通过 `/mcp-config` 管理配置。生成器使用绝对 `command`、`.env` 和 `cwd`，避免桌面启动时工作目录或 PATH 不同；Kimi 从 `command` 推断 stdio，超时字段使用毫秒：

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

工具调用超时与仿真运行时间分别管理。`submit_tool` 返回任务 ID 后，SDE / SDevice 在虚拟机后台运行；用 `job_status`、`job_logs` 查询。仿真自身的期限由 `submit_tool` 的 `timeout_seconds` 参数指定。

保存配置后，在项目目录中启动 Kimi 并新建会话（已有会话不会自动注册刚添加的服务器）。按客户端提示信任自己的工作目录，用 `/mcp` 检查连接，再发送：

> 调用 mcp__sentaurus__bridge_info 和 mcp__sentaurus__bridge_doctor，报告版本、连接状态及远程工具检查结果。

**选择 K3.1 Pro**：CLI 输入 `/model`，桌面端使用输入框中的模型选择器。官方模型 ID 为 `k3.1-pro`，高速版为 `k3.1-pro-highspeed`；账号需具备相应权限，K3.1 Pro 系列必须开启思考模式。建议为新模型新建会话。桥接配置不固定模型 ID，也不存储 Kimi 的账号或模型密钥；以后换模型无需修改 SSH 工具。

使用 Kimi 作为其他客户端的模型后端时，按 Kimi 官方说明配置该客户端的模型，再生成它对应的 MCP 配置（如 `client-config opencode`）。本项目没有另行实现 Kimi API 推理循环。

核对日期：2026-10-24。依据：[Kimi MCP 配置](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/mcp.html)、[桌面端 MCP](https://www.kimi.com/code/docs/en/kimi-code-desktop/settings-and-extensions.html)、[模型选择与 K3.1 Pro](https://www.kimi.com/code/docs/kimi-code/models.html)。旧版 Kimi CLI 的配置目录和命令可能不同，应以已安装版本的官方文档为准。配置生成和标准 MCP 握手已验证，未使用 Kimi 账号执行模型请求。

## 官方 DeepSeek Harness（dsh）

这里接入的是 [DeepSeek 官方开源 Harness](https://github.com/deepseek-ai/deepseek-harness)。它使用 Cordis 插件配置；本项目通过官方 `@deepseek-ai/dsh-mcp-client` 连接，不自建 DeepSeek API 推理循环。

生成配置：

```bash
sentaurus-bridge --env /absolute/path/.env client-config deepseek-harness --local-root /absolute/path/project
```

把输出以 UTF-8 保存为 `sentaurus.cordis.yml`。结构如下，真实路径由生成器填入：

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

安装官方 Harness 后启动：

```bash
dsh web --patch /absolute/path/sentaurus.cordis.yml
```

也可以按官方发布方式使用 `npx @deepseek-ai/dsh web --patch ...`。在 Web UI 的 Settings → Models 设置模型，在工作区选择器中选择项目。等待 MCP 工具完成发现后，要求调用 `mcp__sentaurus__bridge_doctor`。

Harness 会过滤部分敏感环境变量，因此这里显式传入桥接 `.env` 的绝对路径。SSH 私钥仍通过本机路径访问，不需要把私钥内容或模型密钥放入 YAML。

官方 Harness 目前处于 developer preview，可能出现不兼容更新。接入格式核对日期为 2026-10-23，依据：[通用 MCP 插件与 Cordis overlay](https://deepseek-harness.github.io/deepseek-harness/en/guide/mcp-memory)、[Web UI](https://deepseek-harness.github.io/deepseek-harness/en/guide/quickstart)。

## 其他国产模型与 OpenCode

支持工具调用、能接入本地 MCP 的客户端可以使用这套工具。模型提供商由该客户端配置；不需要为每个模型复制 SSH 逻辑。

OpenCode 的配置使用 `mcp.sentaurus` 和 `type: local`，由 `client-config opencode` 生成。依据：[OpenCode MCP servers](https://opencode.ai/docs/mcp-servers/)。只有 OpenAI-compatible 文本接口、没有工具调用执行循环的普通 API 客户端，不能仅凭 API 兼容性完成仿真。

## 工具与验证

| 工具 | 用途 |
| --- | --- |
| `bridge_info` / `bridge_doctor` | 版本配置 / SSH 与远程程序诊断 |
| `list_remote_files` / `read_remote_text` | 查看输入、文本结果与日志 |
| `upload_file` / `download_file` | 单文件传输，默认不覆盖 |
| `submit_tool` | 提交配置允许的程序和字面值参数 |
| `list_jobs` / `job_status` / `job_logs` | 恢复任务 ID、检查退出状态与日志 |
| `cancel_job` | 请求停止一个受管理的任务 |
| `desktop_sessions` / `open_structure` | 找到 X11 桌面并启动 TDR 查看器 |

建议首次只执行 `bridge_info` 和 `bridge_doctor`，再用一个小型、可信模型验证完整流程。任务完成必须同时检查状态、返回码、日志和期望输出文件；模型回复“已完成”不构成执行证据。

MCP 文件路径检查是减少误操作的保护，不是操作系统沙箱。调用 SDE 脚本相当于授权该 SSH 账户执行脚本。保持客户端正常的工具审批设置，并使用权限合适的账户。
