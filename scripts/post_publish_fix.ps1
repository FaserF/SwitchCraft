#!/usr/bin/env pwsh
# post_publish_fix.ps1
# Run this AFTER flet publish to patch the generated web_entry.py for Pyodide SSL compatibility

param(
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "docs/public/demo"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$FixedWebEntry = Join-Path $RepoRoot "build_web/web_entry.py"
$TargetWebEntry = Join-Path $RepoRoot $OutputDir "web_entry.py"

Write-Host "=== SwitchCraft Post-Publish Fix ===" -ForegroundColor Cyan

# Check if the fixed web_entry.py exists
if (-not (Test-Path $FixedWebEntry)) {
    Write-Host "ERROR: Fixed web_entry.py not found at: $FixedWebEntry" -ForegroundColor Red
    exit 1
}

# Check if target exists (flet publish output)
if (-not (Test-Path $TargetWebEntry)) {
    Write-Host "ERROR: Target web_entry.py not found at: $TargetWebEntry" -ForegroundColor Red
    Write-Host "       Did you run 'flet publish' first?" -ForegroundColor Yellow
    exit 1
}

# Backup original
$BackupPath = "$TargetWebEntry.bak"
Copy-Item $TargetWebEntry $BackupPath -Force
Write-Host "Backed up original to: $BackupPath" -ForegroundColor Gray

# Copy fixed version
Copy-Item $FixedWebEntry $TargetWebEntry -Force
Write-Host "Patched web_entry.py with SSL fix!" -ForegroundColor Green

Write-Host ""
Write-Host "Done! You can now deploy the '$OutputDir' folder." -ForegroundColor Cyan
