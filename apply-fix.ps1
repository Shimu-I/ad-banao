# Run once in PowerShell from the project folder:  .\apply-fix.ps1     (or .\apply-fix.ps1 -Sqlite for the optional no-Docker quick start)
param([switch]$Sqlite, [switch]$Postgres)
Set-Location $PSScriptRoot
if (-not ((Test-Path Makefile) -and (Test-Path backend))) { Write-Host "Run this inside the adbanao project folder."; exit 1 }
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "Creating the virtual environment..."; python -m venv .venv; if ($LASTEXITCODE -ne 0) { exit 1 } }
& $py -m pip install -q -r backend\requirements.txt; if ($LASTEXITCODE -ne 0) { exit 1 }
if ($Sqlite) { & $py scripts\fix_env.py --sqlite } elseif ($Postgres) { & $py scripts\fix_env.py --postgres } else { & $py scripts\fix_env.py }
if ($LASTEXITCODE -ne 0) { exit 1 }
& $py scripts\fix_frontend.py
Write-Host "`nDone. Now run:  .\start-adbanao.ps1"
Write-Host "If PowerShell blocks scripts, run once:  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned"
