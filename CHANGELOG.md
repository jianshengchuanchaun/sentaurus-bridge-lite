# Changelog

## 0.2.1 — 2026-10-24

- 新增 `client-config kimi-code`（别名 `kimi`），生成 Kimi Code CLI / 桌面端使用的 stdio MCP JSON。
- Kimi 配置显式设置项目目录、30 秒启动超时及 360 秒工具超时；不写入模型或 API 密钥。
- 补充 K3.1 Pro / Highspeed 的模型选择、思考模式、MCP 配置位置与连接验证步骤。
- 使用生成的 Kimi 配置测试真实 stdio MCP 握手、工具发现及调用；更新首页、快速开始和故障排查。

## 0.2.0 — 2026-10-23

- 将项目定位改为独立 CLI / MCP 的远程 Sentaurus 桥接，VS Code 为可选入口。
- 增加可选官方 MCP Python SDK 集成，提供结构化诊断、文件传输、任务管理和桌面可视化工具。
- 新增 Codex、CodeBuddy、MiniMax Code、官方 DeepSeek Harness、Claude Code、OpenCode 的配置生成。
- 新增持久后台任务：列表、状态、退出码、日志、超时、取消；断开客户端后继续执行。
- 自动发现虚拟机 X11 桌面会话，使用桌面账户打开 `.tdr`，默认 Mesa 渲染。
- MCP 文件操作检查本地与远程项目边界，默认拒绝覆盖，下载中断保留原文件。
- 修复 `.env` BOM、环境变量优先级、SCP 额外参数、初始化文件错误信息引用和远程 UTF-8 兼容。
- 增加 `SB_LOGIN_SHELL`、`SB_REMOTE_PYTHON`、`SB_DESKTOP_USER`。
- 本机最低 Python 版本改为 3.10；远程 worker 仅依赖 Python 3.6+ 标准库。
- 重写中文 README、快速开始、客户端接入与故障排查，明确配置适配和实测的区别。

## 0.1.0

- 初始 OpenSSH 桥接：配置、诊断、远程运行、文件同步和可选 VS Code 启动。
