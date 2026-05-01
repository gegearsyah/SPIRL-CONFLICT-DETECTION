# Chains Phase 2 -> 2b -> 3 after a full reset (same project in .spirl/config.json).
# Logs to ../real-data-lab/research/rdl_redo_phases_2_2b_3.log
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
$log = Join-Path $here "..\real-data-lab\research\rdl_redo_phases_2_2b_3.log"
function W($m) { Add-Content -Path $log -Value ("[{0}] {1}" -f (Get-Date -Format "o"), $m) }
W "=== Phase 2 ==="
python real_data_lab_phase2_mcp_run.py 2>&1 | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) { W "Phase 2 failed exit=$LASTEXITCODE"; exit $LASTEXITCODE }
W "=== Phase 2b (benign) ==="
python real_data_lab_benign_mcp_run.py 2>&1 | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) { W "Phase 2b failed exit=$LASTEXITCODE"; exit $LASTEXITCODE }
W "=== Phase 3 ==="
python real_data_lab_phase3_mcp_run.py 2>&1 | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) { W "Phase 3 failed exit=$LASTEXITCODE"; exit $LASTEXITCODE }
W "=== All done ==="
