# Snapshot Beyond Temporal Contradiction/<LabFolder>/research/* into research/archive/snapshot_<UTC>/
# Excludes the archive folder itself. Use before redoing phases or materialization.
#
# Example:
#   .\archive_btc_lab_research.ps1 -LabFolder trusted-adr-lab
#   .\archive_btc_lab_research.ps1 -LabFolder real-data-lab

param(
    [Parameter(Mandatory = $false)]
    [string]$LabFolder = "trusted-adr-lab"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$btc = (Resolve-Path (Join-Path $here "..")).Path
$research = Join-Path (Join-Path $btc $LabFolder) "research"

if (-not (Test-Path -LiteralPath $research)) {
    throw "Missing research folder: $research"
}

$archiveRoot = Join-Path $research "archive"
New-Item -ItemType Directory -Force -Path $archiveRoot | Out-Null
$stamp = Get-Date -Format "yyyy-MM-dd_HHmmssZ"
$dest = Join-Path $archiveRoot "snapshot_$stamp"
New-Item -ItemType Directory -Force -Path $dest | Out-Null

Get-ChildItem -LiteralPath $research -Force | Where-Object { $_.Name -ne "archive" } | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $dest -Recurse -Force
}

Write-Host "Archived to: $dest"
