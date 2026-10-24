# 故障排查

## SSH 成功，但 MCP 连接失败

- 生成配置时使用安装了 `[mcp]` 的 Python 绝对路径。
- `--env` 指向绝对路径，`--local-root` 指向存在的本地项目。
- MCP 采用 `BatchMode=yes`，先在终端完成密钥认证与主机指纹确认。
- 用 `python -m sentaurus_bridge --env /path/.env doctor --json` 检查远程 Python 与程序路径。
- 远程 worker 需要 Linux/Python 3.6+；可用 `SB_REMOTE_PYTHON=/path/to/python3` 指定解释器。

## Kimi Code 中看不到 Sentaurus 工具

- 用 `client-config kimi-code` 生成配置，合并到工作目录的 `.kimi-code/mcp.json` 或用户级 `~/.kimi-code/mcp.json`；设置 `KIMI_CODE_HOME` 时检查该目录中的 `mcp.json`。
- 进入正确项目，新建 Kimi 会话，并按提示确认工作目录信任；旧会话不会自动加载新加的 MCP 服务器。
- 用 `/mcp` 查看状态、`/mcp-config` 检查配置。同名项目配置会覆盖用户配置，注意旧路径。
- 若提示未知客户端 `kimi-code`，先升级桥接到 0.2.1 或更新版本；旧版 Kimi CLI 的配置方式请查其对应文档。
- K3.1 Pro 的选择在 Kimi `/model` 或桌面模型选择器中完成。模型权限或思考模式错误应按 [官方模型文档](https://www.kimi.com/code/docs/kimi-code/models.html) 处理；桥接 `.env` 不配置模型账号。

## 旧 CentOS 的 profile 报错

某些环境在 `/etc/profile` 中引用已删除的软件路径。设置 `SB_LOGIN_SHELL=0`，并通过 `SB_SENTAURUS_ROOT`、`SB_SENTAURUS_INIT` 或 `SB_SENTAURUS_SETUP` 显式初始化。桥接不会修改系统 profile。

## 中文文件名与空格

MCP 请求使用 UTF-8 JSON，通过 SSH stdin 传输；文件内容通过 SCP。远程 Python 3.6 若启动为 ASCII 编码，worker 会尝试本机已安装的 UTF-8 locale，仅重新启动当前 worker，不修改系统区域设置。没有可用 UTF-8 locale 的旧系统应安装 locale 或升级远程 Python。

普通 CLI 的单字符串 `run "..."` 保留 shell 语义；MCP / `job submit` 的参数则按字面值引用。两者不要混淆。

## 程序存在但仿真失败

`doctor` 不检出许可证。查看 `job logs <id>` 中的许可证、输入语法和求解错误。`completed` 只表示进程返回 0；仍须确认期望的输出和物理收敛。程序不会自动重启许可服务或重试仿真。

## 找不到任务 / 客户端已断开

使用同一 `.env` 和工作目录执行 `job list`。日志保存在 `<workspace>/.sbridge/jobs/`，任务 ID 与工作目录绑定。

任务状态包括 `queued`、`running`、`completed`、`failed`、`cancelled`、`timed_out`、`unknown`。虚拟机重启或 supervisor 意外退出时可能显示 `unknown`；此时先检查日志与残留进程，再决定重跑，避免重复消耗许可证。

`cancel` 返回的是取消请求；通过 `status` 确认最终状态。普通子进程会随任务进程组终止。主动脱离会话的独立守护进程不属于本程序的监管范围。

## 结构窗口没有显示

1. 在虚拟机图形桌面完成登录，然后执行 `desktop list`。
2. 多用户桌面用 `SB_DESKTOP_USER` 选择用户。程序不替用户绕过 X11 授权。
3. SSH 用户与桌面用户不同，需要足够的正常系统权限；root 会用 `runuser` 以桌面用户身份启动。
4. 桌面用户必须能读取完整路径。不要把普通用户要看的文件放在 `/root`，改用共享项目目录。
5. 查看 `desktop open` 返回的 `log_path`。许可证和渲染失败可能在启动后才出现。
6. 默认使用 Mesa；可尝试 `--no-mesa`。目前自动发现针对 X11 桌面，不承诺原生 Wayland 会话兼容。

`desktop open` 是打开虚拟机已有桌面，不是把 GUI 转发到 Windows。需要 X11 转发时使用原有 `gui --x11` 和本地 X Server。

## 0.1 升级注意

- 本机最低 Python 版本改为 3.10；远程 worker 兼容 Python 3.6。
- 进程环境变量现在优先于 `.env`，便于客户端覆盖配置。
- 默认检查四个真实工具名：`sde,sdevice,svisual,swb`。环境中额外工具可通过 `SB_SENTAURUS_TOOLS` 配置。
- 已有 `run`、`push`、`pull`、`gui`、`ssh-config` 和可选 `code` 命令继续保留。
