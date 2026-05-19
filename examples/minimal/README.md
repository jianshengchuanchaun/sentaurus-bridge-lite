# Minimal Remote Run Folder

Put a small Sentaurus project here, then run it from VS Code or the terminal:

```powershell
sentaurus-bridge push examples/minimal ~/sentaurus-work/minimal
sentaurus-bridge run -w ~/sentaurus-work/minimal -- sdevice your_des.cmd
sentaurus-bridge pull ~/sentaurus-work/minimal sentaurus-results/minimal
```

The bridge intentionally does not ship Synopsys examples or technology files.
Those are normally licensed/proprietary and should stay on your VM or in your
private research repository.
