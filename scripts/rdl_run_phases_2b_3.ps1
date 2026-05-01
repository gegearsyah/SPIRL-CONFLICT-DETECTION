# Phase 2b (benign) then Phase 3 — same project in .spirl/config.json; Phase 2 must be complete.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
$log = Join-Path $here "..\real-data-lab\research\rdl_phase2b_phase3_chain.log"
function W($m) { Add-Content -Path $log -Value ("[{0}] {1}" -f (Get-Date -Format "o"), $m) }
W "=== Phase 2b (benign) ==="
python real_data_lab_benign_mcp_run.py --ignore-pipeline-lock 2>&1 | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) { W "Phase 2b failed exit=$LASTEXITCODE"; exit $LASTEXITCODE }
W "=== Phase 3 ==="
python real_data_lab_phase3_mcp_run.py --ignore-pipeline-lock 2>&1 | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) { W "Phase 3 failed exit=$LASTEXITCODE"; exit $LASTEXITCODE }
W "=== Phase 2b + 3 complete ==="
