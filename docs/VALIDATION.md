# 验证记录

日期：2026-10-23 至 2026-10-24。基础桥接与虚拟机验收版本：0.2.0；Kimi 接入更新：0.2.1。

## 本地自动化

使用 Windows / Python 3.10 / MCP Python SDK 1.30.0，测试包括：

- 原有配置解析与 SSH 参数构建。
- `.env` BOM、环境变量覆盖、非 login shell、初始化路径引用。
- Windows MCP 精简环境下恢复 OpenSSH 所需的 ProgramData 路径。
- 路径越界拒绝、默认拒绝覆盖、下载失败保留原文件。
- Codex TOML、CodeBuddy/MiniMax/Kimi Code/Claude/OpenCode JSON、DeepSeek Harness Cordis YAML 解析。
- Kimi Code / `kimi` 别名的绝对路径、毫秒超时配置，以及从生成配置启动的真实 stdio MCP 握手、工具发现和调用。
- 真实 stdio MCP initialize、tools/list、tools/call、结构化返回和错误返回。

Linux 专用测试覆盖真实后台进程的正常退出、失败、超时、取消、日志截断、任务恢复、失效 supervisor、路径穿越和 symlink，以及忽略 TERM 的子进程清理。CI 在 Ubuntu / Windows、Python 3.10 / 3.12 上执行，不需要 Sentaurus 许可证。

## 真实虚拟机验收

使用现有 Linux 虚拟机、远程 Python 3.6.8 和 Sentaurus W-2024.09-SP1。输入为用户私有二维 NMOS 项目，未随源码上传。

| 检查 | 结果 |
| --- | --- |
| SSH、远程 Python、SDE/SDevice/SVisual/SWB 路径 | 通过 |
| 含中文、空格、单引号及 shell 标点的文件上传 / 读取 | 通过 |
| 下载后的 SHA-256 与原文件一致 | 通过 |
| 返回码 7 的任务 | 正确记录 `failed` 和退出码 |
| 超过执行期限的任务 | 正确记录 `timed_out` |
| 主动取消任务 | 正确记录 `cancelled` |
| SDE + Mesh 后台任务 | 返回 0，生成 10,543 个网格点的 TDR |
| SDevice 后台任务 | 返回 0，日志确认曲线追踪结束，生成求解 TDR 和电流文件 |
| 客户端断开后重新查询 | 可通过任务 ID / `list_jobs` 恢复状态和日志 |
| 结构查看 | 发现已有 tcad X11 桌面，并以该用户启动 SVisual |
| 实际 stdio MCP 到 SSH 的调用 | `bridge_doctor`、`list_jobs`、结果文件检查通过 |

图形启动接口明确返回 `window_verified: false`，不以进程启动代替可视窗口验证。程序目录可用性与许可证可用性也分开判断；本次实际 SDE/SDevice 执行使用了远程已有授权。

## 验证范围

- **已实测**：桥接 CLI / Python API、官方 SDK 的 stdio MCP 协议调用、真实 SSH 文件往返和 Sentaurus 执行。
- **已适配并检查配置格式**：Codex、CodeBuddy、MiniMax Code、Kimi Code CLI / 桌面端、官方 DeepSeek Harness、Claude Code、OpenCode。
- **未声称验证**：每个客户端版本的完整 UI 工作流、每个模型服务的实际 API 账号、模型生成 TCAD 输入的物理正确性、原生 Wayland、其他 Sentaurus 版本。

没有使用 MiniMax、Kimi 或 DeepSeek API 密钥做付费模型调用，未将标准 MCP SDK 握手等同于这些客户端的完整 UI 或模型调用验证。它们的账号与模型配置由对应客户端管理。官方 DeepSeek Harness 仍在 developer preview，升级客户端后应再次执行实际 MCP 工具调用检查。
