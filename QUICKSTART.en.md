# Quick start: terminal and AI clients

[简体中文](QUICKSTART.md) | **English** · [Home](README.en.md)

## 1. Install

```bash
git clone https://github.com/jianshengchuanchaun/sentaurus-bridge-lite.git
cd sentaurus-bridge-lite
python -m pip install -e ".[mcp]"
sentaurus-bridge init
```

For standalone CLI use, `python -m pip install -e .` is sufficient. If `sentaurus-bridge` is not on your PATH, use `python -m sentaurus_bridge` instead.

## 2. Configure SSH and Sentaurus

Edit `.env` with your host, user, key path, project directory, and environment initialization. For example:

```dotenv
SB_REMOTE_HOST=sentaurus-vm
SB_REMOTE_WORKDIR=~/sentaurus-work
SB_SENTAURUS_ROOT=/opt/synopsys/sentaurus/your-version
SB_SENTAURUS_SETUP=source /path/to/site-setup.sh
SB_LOGIN_SHELL=0
```

First run `ssh sentaurus-vm` to verify the host fingerprint and complete key-based login. Then check the connection:

```bash
sentaurus-bridge doctor --batch
sentaurus-bridge doctor --json
```

MCP and background jobs use non-interactive SSH. If your installation can only be initialized through a login shell, set `SB_LOGIN_SHELL=1`. If an old CentOS profile references missing paths, use `0` and explicitly set `SB_SENTAURUS_SETUP`.

## 3. Choose an entry point

**Terminal / direct command execution in Codex:**

```bash
sentaurus-bridge push my-nmos ~/sentaurus-work
sentaurus-bridge job submit -w my-nmos -- sde -e -l sde.scm
sentaurus-bridge job status <JOB_ID>
sentaurus-bridge job logs <JOB_ID>
```

Replace `<JOB_ID>` with the actual ID. Confirm that the mesh exists before submitting SDevice.

**Codex MCP:**

```bash
sentaurus-bridge --env /absolute/path/.env client-config codex --local-root /absolute/path/project
```

Merge the output into your Codex MCP settings. Windows paths can use the form `C:/TCAD/project/.env`. See [AI client setup](docs/AI_CLIENTS.en.md).

**Kimi Code CLI / desktop app:**

```bash
sentaurus-bridge --env /absolute/path/.env client-config kimi-code --local-root /absolute/path/project
```

Merge the output into `mcpServers` in the project's `.kimi-code/mcp.json`, using UTF-8 and preserving other servers. Open the project, start a new Kimi session, check the connection with `/mcp`, and ask it to call `mcp__sentaurus__bridge_doctor`. Select K3.1 Pro with `/model` in the CLI or the desktop model selector; keep thinking mode enabled. Kimi manages models and accounts. See [Kimi setup](docs/AI_CLIENTS.en.md#kimi-code-cli--desktop-app-and-k31-pro).

**Official DeepSeek Harness:**

```bash
sentaurus-bridge --env /absolute/path/.env client-config deepseek-harness --local-root /absolute/path/project
```

Save the output as `sentaurus.cordis.yml` in UTF-8, then start:

```bash
dsh web --patch /absolute/path/sentaurus.cordis.yml
```

Configure the model and API key in the official Harness under Settings → Models. The bridge provides the Sentaurus tools.

## 4. View and download results

```bash
sentaurus-bridge desktop list
sentaurus-bridge desktop open my-nmos/nmos_msh.tdr
sentaurus-bridge pull ~/sentaurus-work/my-nmos sentaurus-results
```

The structure window opens on the VM's desktop. Switch to VMware or your remote desktop viewer to see it. See [Troubleshooting](docs/TROUBLESHOOTING.en.md).
