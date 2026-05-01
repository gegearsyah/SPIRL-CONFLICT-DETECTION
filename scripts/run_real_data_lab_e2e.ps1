# Real Data Lab end-to-end: new project + Phase 1 + Phase 2 (full list_conflict.md) + Phase 2b + Phase 3.
# Prerequisites: Spirl API + MCP on http://localhost:8000 (see .cursor/mcp.json Bearer), models warmed per Spiral docs.
# Run from repo root or any cwd; uses script directory to find Python modules.

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

Write-Host "=== 1. Create project + import SKF (updates .spirl/config.json) ===" 
python import_real_data_lab_skf_mcp.py --write-config --mcp-url http://localhost:8000/mcp --api-base http://localhost:8000

Write-Host "=== 2. Phase 1 (archives prior logs unless --resume on phase1 script) ===" 
python real_data_lab_phase1_mcp_run.py

Write-Host "=== 3. Phase 2 - 110 conflict rows (poll max from config, default 120s) ===" 
python real_data_lab_phase2_mcp_run.py

Write-Host "=== 4. Phase 2b - benign + mixed metrics ===" 
python real_data_lab_benign_mcp_run.py

Write-Host "=== 5. Phase 3 - report + RQ upserts ===" 
python real_data_lab_phase3_mcp_run.py

Write-Host 'Done. Artifacts under ../real-data-lab/research/'
