# 快速开始：终端和 AI 客户端

## 1. 安装

```bash
git clone https://github.com/jianshengchuanchaun/sentaurus-bridge-lite.git
cd sentaurus-bridge-lite
python -m pip install -e ".[mcp]"
sentaurus-bridge init
```

只用普通命令行时可安装 `python -m pip install -e .`。找不到 `sentaurus-bridge` 时，使用 `python -m sentaurus_bridge` 代替。

## 2. 配置 SSH 和 Sentaurus

编辑 `.env`，填写主机、用户、密钥路径、项目目录和环境初始化。例如：

```dotenv
SB_REMOTE_HOST=sentaurus-vm
SB_REMOTE_WORKDIR=~/sentaurus-work
SB_SENTAURUS_ROOT=/opt/synopsys/sentaurus/your-version
SB_SENTAURUS_SETUP=source /path/to/site-setup.sh
SB_LOGIN_SHELL=0
```

先执行 `ssh sentaurus-vm` 核对主机指纹并完成密钥登录。然后检查：

```bash
sentaurus-bridge doctor --batch
sentaurus-bridge doctor --json
```

MCP 和后台任务使用非交互 SSH。如果安装环境只能通过 login shell 加载，使用 `SB_LOGIN_SHELL=1`；旧 CentOS profile 有失效路径时，用 `0` 并显式设置 `SB_SENTAURUS_SETUP`。

## 3. 选择入口

**终端 / Codex 直接执行命令**：

```bash
sentaurus-bridge push my-nmos ~/sentaurus-work
sentaurus-bridge job submit -w my-nmos -- sde -e -l sde.scm
sentaurus-bridge job status <JOB_ID>
sentaurus-bridge job logs <JOB_ID>
```

把 `<JOB_ID>` 替换为实际 ID；确认网格生成后再提交 SDevice。

**Codex MCP**：

```bash
sentaurus-bridge --env /absolute/path/.env client-config codex --local-root /absolute/path/project
```

把输出合并到 Codex MCP 设置。Windows 路径可以写成 `C:/TCAD/project/.env`。详见 [客户端接入](docs/AI_CLIENTS.md)。

**官方 DeepSeek Harness**：

```bash
sentaurus-bridge --env /absolute/path/.env client-config deepseek-harness --local-root /absolute/path/project
```

将输出以 UTF-8 保存为 `sentaurus.cordis.yml`，启动：

```bash
dsh web --patch /absolute/path/sentaurus.cordis.yml
```

模型和 API 密钥在官方 Harness 的 Settings → Models 配置。桥接仅负责 Sentaurus 工具。

## 4. 查看和下载

```bash
sentaurus-bridge desktop list
sentaurus-bridge desktop open my-nmos/nmos_msh.tdr
sentaurus-bridge pull ~/sentaurus-work/my-nmos sentaurus-results
```

结构窗口位于虚拟机桌面，请切换 VMware / 远程桌面查看。详见 [故障排查](docs/TROUBLESHOOTING.md)。
