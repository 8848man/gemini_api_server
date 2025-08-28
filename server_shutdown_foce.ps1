 Get-Process | Where-Object { $_.ProcessName -like "python*" } | Stop-Process -Force
