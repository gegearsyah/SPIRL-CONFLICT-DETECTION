# Trusted ADR Lab (TAL) end-to-end runner.
#
# Stages:
#   0. Materialize TAL artifacts (66 ADR facts + 8 conflict + 4 ambiguity +
#      6 benign rows) under `../trusted-adr-lab/research/`.
#   1. Phase 1  — import the 66 ADR facts into the TAL Spirl project via MCP.
#   2. Phase 2  — inject 8 typed conflict + 4 ambiguity rows via MCP preflight
#                 + `memory_upsert_fact_v1`, logging the full governance envelope.
#   3. Phase 2b — inject 6 benign rows (FP / `needs_review` precision accounting).
#   4. Phase 3  — compute TAL metrics and write the mixed report, confusion
#                 matrix, and paper3 experiment_D companion report.
#
# Stages 1-4 require a running Spirl backend + a `trusted_adr_lab_project_id`
# (or `projects.trusted_adr_lab_project`) in `.spirl/config.json`.  Pass
# `-MaterializeOnly` to stop after stage 0 (no MCP calls).

[CmdletBinding()]
param(
    [switch]$MaterializeOnly,
    [switch]$SkipMaterialize,
    [switch]$Resume
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

if (-not $SkipMaterialize) {
    Write-Host "=== Stage 0: materialize TAL artifacts (experiment_d_trusted_adr_track.py) ==="
    python experiment_d_trusted_adr_track.py --lab-root ../trusted-adr-lab
} else {
    Write-Host "=== Stage 0 skipped (--SkipMaterialize) ==="
}

if ($MaterializeOnly) {
    Write-Host "Done (materialize-only).  Artifacts under ../trusted-adr-lab/research/"
    exit 0
}

$resumeArg = @()
if ($Resume) { $resumeArg = @("--resume") }

Write-Host "=== Stage 1: TAL Phase 1 - ADR fact import via MCP ==="
python trusted_adr_lab_phase1_mcp_run.py @resumeArg

Write-Host "=== Stage 2: TAL Phase 2 - typed + ambiguity injections via MCP ==="
python trusted_adr_lab_phase2_mcp_run.py @resumeArg

Write-Host "=== Stage 3: TAL Phase 2b - benign injections via MCP ==="
python trusted_adr_lab_phase2b_mcp_run.py @resumeArg

Write-Host "=== Stage 4: TAL Phase 3 - scoring + report generation ==="
python trusted_adr_lab_phase3_mcp_run.py

Write-Host "TAL end-to-end complete.  Reports under ../trusted-adr-lab/research/:"
Write-Host "  - trusted_adr_lab_mixed_report.md"
Write-Host "  - trusted_adr_lab_confusion_matrix.md"
Write-Host "  - trusted_adr_lab_phase3_report.md"
Write-Host "  - paper3_phase3_report.experiment_D.md"
