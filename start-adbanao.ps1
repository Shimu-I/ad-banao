# One command to run AdBanao on Windows. Run in PowerShell:  .\start-adbanao.ps1   (Ctrl+C to stop)
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "Run .\apply-fix.ps1 first."; exit 1 }
New-Item -ItemType Directory -Force .run-logs | Out-Null
$h = "127.0.0.1"

function Free-Port($p) {
  Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Host "Port $p was busy, freeing it."; Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
  Start-Sleep -Milliseconds 800
}
function Db-Ok {
  Push-Location backend
  & $py -c "from app.db.session import engine; engine.connect().close()" 2>$null | Out-Null
  $ok = ($LASTEXITCODE -eq 0); Pop-Location; return $ok
}

Free-Port 8000; Free-Port 5173

if (-not (Db-Ok)) {
  if ((Select-String -Path .env -Pattern '^DATABASE_URL=postgres' -Quiet) -and (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Starting the database container..."; docker compose up -d db 2>$null | Out-Null
    1..30 | ForEach-Object { if (-not (Db-Ok)) { Start-Sleep 1 } }
  }
  if (-not (Db-Ok)) { Write-Host "ERROR: cannot reach the database. For a no-Docker setup run: .\apply-fix.ps1 -Sqlite"; exit 1 }
}

Push-Location backend; & $py -m alembic upgrade head | Out-Null; $m = $LASTEXITCODE; Pop-Location
if ($m -ne 0) { Write-Host "ERROR: migration failed."; exit 1 }
& $py scripts\fix_frontend.py
& $py scripts\setup_admin.py; if ($LASTEXITCODE -ne 0) { exit 1 }

$api = Start-Process $py -ArgumentList "-m","uvicorn","app.main:app","--host",$h,"--port","8000" -WorkingDirectory (Join-Path $PSScriptRoot "backend") -WindowStyle Hidden -PassThru -RedirectStandardOutput .run-logs\api.log -RedirectStandardError .run-logs\api.err
$web = Start-Process $py -ArgumentList "scripts\serve_frontend.py","5173",$h -WindowStyle Hidden -PassThru -RedirectStandardOutput .run-logs\web.log -RedirectStandardError .run-logs\web.err

$up = $false
1..30 | ForEach-Object { if (-not $up) { try { Invoke-WebRequest "http://${h}:8000/health" -UseBasicParsing | Out-Null; $up = $true } catch { Start-Sleep 1 } } }
if (-not $up) { Write-Host "API did not start. See .run-logs\api.err"; Stop-Process $api.Id,$web.Id -Force -ErrorAction SilentlyContinue; exit 1 }

$email = & $py -c "import sys;sys.path.insert(0,'scripts');import _admin_creds as c;print(c.EMAIL)"
Write-Host "`nAdBanao is running. Use ONLY these links (127.0.0.1):"
Write-Host "  App:    http://${h}:5173/"
Write-Host "  Admin:  http://${h}:5173/admin-login.html"
Write-Host "  Email:  $email"
Write-Host "  Password and secret word: see scripts\_admin_creds.py"
Write-Host "Press Ctrl+C or close this window to stop."
try { while ($true) { Start-Sleep 2 } }
finally { Stop-Process $api.Id,$web.Id -Force -ErrorAction SilentlyContinue; Free-Port 8000; Free-Port 5173; Write-Host "Stopped." }
