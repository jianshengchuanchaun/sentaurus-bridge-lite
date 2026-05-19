# sentaurus-bridge-lite

一个给 VS Code 使用的轻量 Sentaurus TCAD 虚拟机连接工具。它不绑定你的虚拟机 IP、账号或 Synopsys 安装路径，核心配置都放在本地 `.env`，所以后面可以直接放到 GitHub 给别人复用。

English quick start: see [`QUICKSTART.md`](QUICKSTART.md).

它适合两种工作方式：

- 在本机 VS Code 里写文件，通过 SSH 把工程推到虚拟机，远程运行 `sdevice`、`sde`、`swb`、`svisual`，再把结果拉回来。
- 生成 SSH config，让 VS Code 的 Remote - SSH 直接打开虚拟机里的 Sentaurus 工作目录。

## 功能

- `sentaurus-bridge doctor`：检查 SSH、远程 Sentaurus 环境和常用命令。
- `sentaurus-bridge ssh`：进入虚拟机 shell，并加载 Sentaurus 环境。
- `sentaurus-bridge run -- ...`：从 VS Code 终端远程运行任意 Sentaurus 命令。
- `sentaurus-bridge push/pull`：上传工程、下载结果。
- `sentaurus-bridge gui swb`：通过 SSH/X11 启动 Sentaurus Workbench 或其他 GUI 工具。
- `sentaurus-bridge ssh-config --write`：为 VS Code Remote - SSH 写入一个可连接的 host alias。

## 安装

先确认本机已经有 Python 3.9+ 和 OpenSSH。Windows 10/11 一般自带 `ssh.exe`，可以在 PowerShell 里测试：

```powershell
ssh -V
python --version
```

安装本工具：

```powershell
cd D:\vscode\sentaurus-bridge-lite
python -m pip install -e .
sentaurus-bridge --version
```

初始化本地配置：

```powershell
sentaurus-bridge init
notepad .env
```

至少填写这几项：

```dotenv
SB_REMOTE_HOST=192.168.56.101
SB_REMOTE_USER=你的虚拟机用户名
SB_REMOTE_WORKDIR=~/sentaurus-work
SB_SENTAURUS_SETUP=source /opt/synopsys/sentaurus/V-2023.09/settings.sh
```

`SB_SENTAURUS_SETUP` 要写成“在虚拟机新开的 SSH shell 里能让 Sentaurus 上 PATH 的命令”。如果你的虚拟机里是通过 module 管理软件，可以写：

```dotenv
SB_SENTAURUS_SETUP=module load sentaurus
```

如果你还不知道 setup 脚本路径，先手动 SSH 进去查：

```powershell
ssh 用户名@虚拟机IP
which sdevice
which swb
env | grep -E 'STROOT|SENTAURUS|SNPS|PATH'
```

## 第一次检查

```powershell
sentaurus-bridge doctor
```

成功时会看到类似：

```text
[ok] ssh connection
[ok] Sentaurus tools: all found
OK sdevice /opt/synopsys/...
OK swb /opt/synopsys/...
```

如果 SSH 可以连，但工具找不到，通常是 `.env` 里的 `SB_SENTAURUS_SETUP` 没有覆盖非交互 shell。很多 EDA 工具在图形终端里能用，但 SSH 直接执行命令时 PATH 不完整，`doctor` 就是专门抓这个问题的。

## 在 VS Code 里使用

这个仓库自带 `.vscode/tasks.json`。安装后，在 VS Code 里打开命令面板：

```text
Tasks: Run Task
```

可用任务包括：

- `Sentaurus: doctor`
- `Sentaurus: SSH shell`
- `Sentaurus: run command`
- `Sentaurus: launch Workbench`
- `Sentaurus: push workspace`
- `Sentaurus: pull results`

也可以直接在 VS Code 终端运行：

```powershell
sentaurus-bridge ssh
sentaurus-bridge run -- sdevice nmos_des.cmd
sentaurus-bridge gui swb
```

## 让 VS Code Remote - SSH 直接连接虚拟机

先写入 SSH config：

```powershell
sentaurus-bridge ssh-config --write
```

然后在 VS Code 中安装或启用 `Remote - SSH` 扩展，选择 host：

```text
sentaurus-vm
```

也可以让工具尝试直接打开远程窗口：

```powershell
sentaurus-bridge code
```

这等价于打开 `SB_REMOTE_WORKDIR`。如果你想打开别的远程目录：

```powershell
sentaurus-bridge code ~/my-tcad-project
```

## 运行一个工程

把本地目录推到虚拟机：

```powershell
sentaurus-bridge push . ~/sentaurus-work/my-project
```

远程运行：

```powershell
sentaurus-bridge run -w ~/sentaurus-work/my-project -- sdevice diode_des.cmd
```

拉回结果：

```powershell
sentaurus-bridge pull ~/sentaurus-work/my-project sentaurus-results/my-project
```

也可以一次完成“上传、运行、下载”：

```powershell
sentaurus-bridge run --push --pull --local-dir . -w ~/sentaurus-work/my-project -- sdevice diode_des.cmd
```

## GUI：Workbench、SVisual、SDE

如果你用的是 Windows 本机 VS Code，并希望 GUI 窗口显示在 Windows 上，需要先启动 X server，例如 VcXsrv 或 Xming。然后在 `.env` 中启用：

```dotenv
SB_ENABLE_X11=1
SB_DISPLAY=localhost:0.0
```

启动 Workbench：

```powershell
sentaurus-bridge gui swb
```

打开 SVisual 文件：

```powershell
sentaurus-bridge gui -- svisual result.tdr
```

如果你通过虚拟机桌面本身使用 GUI，而不是 X11 转发，可以保持 `SB_ENABLE_X11=0`，再用 `sentaurus-bridge ssh` 进入远程 shell 手动启动，或继续使用虚拟机图形桌面。

## 配置项

常用 `.env` 变量：

| 变量 | 说明 |
| --- | --- |
| `SB_REMOTE_HOST` | 虚拟机 IP、主机名，或 SSH config alias |
| `SB_REMOTE_USER` | 虚拟机用户名 |
| `SB_REMOTE_PORT` | SSH 端口，默认 `22` |
| `SB_SSH_KEY` | 可选，SSH 私钥路径 |
| `SB_JUMP_HOST` / `SB_JUMP_USER` | 可选，跳板机 |
| `SB_REMOTE_WORKDIR` | 默认远程工作目录 |
| `SB_SENTAURUS_SETUP` | 每次运行前加载 Sentaurus 环境的 shell 片段 |
| `SB_SENTAURUS_INIT` | 可选，bash 兼容的 setup 文件路径 |
| `SB_SENTAURUS_ROOT` | 可选，自动加入 `$STROOT/bin` 到 PATH |
| `SB_SENTAURUS_TOOLS` | `doctor` 检查的命令列表 |
| `SB_ENABLE_X11` | 是否默认启用 `ssh -Y` |
| `SB_DISPLAY` | GUI 转发时的 DISPLAY |

## GitHub 发布建议

可以提交：

- `src/`
- `tests/`
- `.env.example`
- `.vscode/tasks.json`
- `README.md`
- `pyproject.toml`
- `LICENSE`

不要提交：

- `.env`
- 真实 IP、账号、license server 地址
- Synopsys 安装包、官方 examples、工艺文件、仿真结果大文件

本项目默认 `.gitignore` 已经忽略 `.env`、常见 Python 产物和一些 Sentaurus 结果文件。

## 故障排查

SSH 连不上：

```powershell
ssh 用户名@虚拟机IP
```

如果手动 SSH 也失败，先检查虚拟机网络模式、IP、`sshd` 服务和防火墙。

SSH 能连但 `doctor` 找不到 `sdevice`：

```powershell
sentaurus-bridge ssh
which sdevice
```

如果交互 shell 里能找到，但 `doctor` 找不到，把交互 shell 中加载 Sentaurus 的命令写进 `.env` 的 `SB_SENTAURUS_SETUP`。

GUI 没有窗口：

- Windows 上先启动 VcXsrv/Xming。
- `.env` 设置 `SB_ENABLE_X11=1`。
- 测试 `sentaurus-bridge run --x11 -- xclock`，如果虚拟机有 `xclock`，能弹窗说明 X11 基本通。
- 如果学校/实验室环境禁用 X11，可以用 VS Code Remote - SSH 做文件和命令，GUI 继续通过虚拟机桌面打开。
