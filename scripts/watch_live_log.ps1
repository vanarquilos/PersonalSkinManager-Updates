param(
    [int]$Tail = 120
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$logDir = Join-Path $env:LOCALAPPDATA "Rose\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

Write-Host "Waiting for the latest PSM log in:" -ForegroundColor Cyan
Write-Host "  $logDir"
Write-Host ""

$latest = $null
while (-not $latest) {
    $latest = Get-ChildItem -LiteralPath $logDir -Filter "rose_*.log*" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $latest) {
        Start-Sleep -Milliseconds 500
    }
}

Write-Host "Watching: $($latest.FullName)" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop watching." -ForegroundColor Yellow
Write-Host ""

Get-Content -LiteralPath $latest.FullName -Tail $Tail -Wait
