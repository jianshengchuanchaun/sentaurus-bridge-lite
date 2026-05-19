# Quick Start

`sentaurus-bridge-lite` is a small SSH wrapper for using Synopsys Sentaurus TCAD
from VS Code while the actual tools run inside a Linux VM or remote server.

## Install

```bash
python -m pip install -e .
sentaurus-bridge --version
```

## Configure

```bash
sentaurus-bridge init
```

Edit `.env`:

```dotenv
SB_REMOTE_HOST=192.168.56.101
SB_REMOTE_USER=eda
SB_REMOTE_WORKDIR=~/sentaurus-work
SB_SENTAURUS_SETUP=source /opt/synopsys/sentaurus/V-2023.09/settings.sh
```

Use the setup command that works on your machine. Common alternatives:

```dotenv
SB_SENTAURUS_SETUP=module load sentaurus
```

```dotenv
SB_SENTAURUS_ROOT=/opt/synopsys/sentaurus/V-2023.09
```

## Check

```bash
sentaurus-bridge doctor
```

## Run

```bash
sentaurus-bridge push . ~/sentaurus-work/my-project
sentaurus-bridge run -w ~/sentaurus-work/my-project -- sdevice diode_des.cmd
sentaurus-bridge pull ~/sentaurus-work/my-project sentaurus-results/my-project
```

## VS Code Remote - SSH

```bash
sentaurus-bridge ssh-config --write
sentaurus-bridge code
```

Then connect to the generated host alias, usually `sentaurus-vm`.

## GUI

For X11 forwarding, start a local X server first, then set:

```dotenv
SB_ENABLE_X11=1
SB_DISPLAY=localhost:0.0
```

Launch Sentaurus Workbench:

```bash
sentaurus-bridge gui swb
```
