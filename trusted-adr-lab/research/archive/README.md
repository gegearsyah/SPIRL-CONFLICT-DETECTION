# Archive

Store snapshots of `../` (the active `research/` tree) here before large reruns, using:

```powershell
cd "Beyond Temporal Contradiction/scripts"
.\archive_btc_lab_research.ps1 -LabFolder trusted-adr-lab
```

Each run creates `research/archive/snapshot_<timestamp>/` with copies of logs, reports, and `trusted_adr/` at that moment.
