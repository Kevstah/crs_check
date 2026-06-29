```powershell
$ports = Get-NetTCPConnection -State Listen | Where-Object { $_.LocalAddress -eq "127.0.0.1" } | Select-Object -ExpandProperty LocalPort -Unique | Sort-Object
foreach ($p in $ports) {
  curl.exe -s -I --connect-timeout 2 --max-time 6 --proxy "http://127.0.0.1:$p" https://github.com > $null 2>&1
  if ($LASTEXITCODE -eq 0) { Write-Host "[OK ] $p" } else { Write-Host "[FAIL] $p" }
}
```