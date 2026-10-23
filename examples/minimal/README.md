# Minimal remote run folder

Place your own trusted SDE/SDevice project in a local folder called `my-nmos`:

```bash
sentaurus-bridge push my-nmos ~/sentaurus-work
sentaurus-bridge job submit -w my-nmos -- sde -e -l sde.scm
sentaurus-bridge job status <SDE_JOB_ID>
sentaurus-bridge job logs <SDE_JOB_ID>
```

After the SDE job succeeds and the mesh exists, submit SDevice:

```bash
sentaurus-bridge job submit -w my-nmos -- sdevice sdevice.cmd
sentaurus-bridge job status <SDEVICE_JOB_ID>
sentaurus-bridge job logs <SDEVICE_JOB_ID>
sentaurus-bridge desktop open my-nmos/nmos_msh.tdr
sentaurus-bridge pull ~/sentaurus-work/my-nmos sentaurus-results
```

Replace filenames with your project files. No editor is required. The bridge does
not ship proprietary Synopsys examples, technology files, licenses or private
measurement data. Keep them in your own project directory.
