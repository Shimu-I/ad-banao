foreach ($p in 8000,5173) {
  Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force; Write-Host "Freed port $p" }
}
Write-Host "Done."
