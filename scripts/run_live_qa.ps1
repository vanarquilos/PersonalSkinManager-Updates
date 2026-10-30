param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

Write-Host ""
Write-Host "=== Personal Skin Manager - Live Source QA ===" -ForegroundColor Cyan
Write-Host "Root: $Root"

try {
    $branchName = (git branch --show-current).Trim()
    $headSha = (git rev-parse HEAD).Trim()
    Write-Host "Branch: $branchName"
    Write-Host "HEAD:   $headSha"
}
catch {
    Write-Warning "Git metadata could not be read: $($_.Exception.Message)"
}

$pythonVersion = & python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
if ($LASTEXITCODE -ne 0) {
    throw "Python is not available on PATH."
}
Write-Host "Python: $pythonVersion"

$LegacyState = Join-Path $Root "injection\tools\_v105_rose_legacy_local_state.json"
if (Test-Path -LiteralPath $LegacyState -PathType Leaf) {
    Write-Host "PRIVATE SOURCE QA: verifying selected LTK v1.28.1 host/DLL pair." -ForegroundColor Cyan
    $Pinned = Join-Path $Root "installer\candidates\v1.0.5\audit-only-ltk-v1.28.1"
    foreach ($Name in @("ltk_patcher_host.exe", "ltk_patcher_dll.dll")) {
        $ActiveFile = Join-Path $Root ("injection\tools\" + $Name)
        $PinnedFile = Join-Path $Pinned $Name
        if (-not (Test-Path -LiteralPath $ActiveFile -PathType Leaf) -or
            -not (Test-Path -LiteralPath $PinnedFile -PathType Leaf) -or
            (Get-FileHash -LiteralPath $ActiveFile -Algorithm SHA256).Hash -ne
            (Get-FileHash -LiteralPath $PinnedFile -Algorithm SHA256).Hash) {
            throw "Active $Name differs from the Rose-reported tested pair. Close PSM/League and run use_rose_legacy_runtime_local.ps1 -Action Status."
        }
        Write-Host "Verified active original LTK v1.28.1 file: $Name" -ForegroundColor Green
    }
    Write-Warning "Keep this source test pair if it works. The separate release installer uses independently staged unsigned copies."
}

$requiredRuntime = @(
    "injection\tools\mod-tools.exe",
    "injection\tools\ltk_patcher_host.exe",
    "injection\tools\ltk_patcher_dll.dll"
)

$missing = @()
foreach ($relativePath in $requiredRuntime) {
    $fullPath = Join-Path $Root $relativePath
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        $missing += $relativePath
    }
}

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "Missing runtime files:" -ForegroundColor Red
    foreach ($item in $missing) {
        Write-Host "  - $item" -ForegroundColor Red
    }
    throw "Live QA cannot start until the local runtime trio is present."
}

$running = Get-Process -Name "PersonalSkinManager" -ErrorAction SilentlyContinue
if ($running) {
    Write-Host ""
    Write-Host "PersonalSkinManager.exe is already running." -ForegroundColor Yellow
    Write-Host "Close the installed/build copy first so the source run can own the singleton."
    exit 2
}

if (-not $SkipTests) {
    Write-Host ""
    Write-Host "Running focused source checks..." -ForegroundColor Cyan
    & python -m unittest tests.test_release_skin_routing tests.test_ltk_host_protocol tests.test_ltk_qa_runtime_selector tests.test_v105_skin_wad_inspection tests.test_v105_diagnostic_contract tests.test_ltk_v1281_compatibility_audit tests.test_rose_legacy_review_contract tests.test_rose_legacy_local_runtime_contract tests.test_v105_distribution_contract tests.test_v105_distribution_tree_audit tests.test_v105_launch_privilege_contract tests.test_v105_exe_manifest tests.test_v105_publish_contract tests.test_ltk_countdown_prearm tests.test_overlay_cleanup tests.test_lcu_put_reconnect tests.test_game_monitor_vanishing_process tests.test_runtime_failure_reporting tests.test_runtime_audit_v105 tests.test_patcher_eol tests.test_swiftplay_runtime tests.test_patch_2619_wad_headers tests.test_psm_ui_polish_release tests.test_release_packaging

    if ($LASTEXITCODE -ne 0) {
        throw "Focused source checks failed. Fix them before live League QA."
    }
}

$logDir = Join-Path $env:LOCALAPPDATA "Rose\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

Write-Host ""
Write-Host "Preflight passed." -ForegroundColor Green
Write-Host "Run League normally, then test PSM from this source session."
Write-Host "Use Practice Tool for the first live skin test."
Write-Host "Logs: $logDir"
Write-Host ""
Write-Host "Starting: python .\main.py --dev --debug --logs" -ForegroundColor Cyan
Write-Host "Keep this PowerShell window open during the entire test." -ForegroundColor Yellow
Write-Host ""

& python .\main.py --dev --debug --logs
$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "PSM source process exited with code $exitCode"

$latest = Get-ChildItem -LiteralPath $logDir -Filter "rose_*.log*" -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($latest) {
    Write-Host "Latest log: $($latest.FullName)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Last 120 lines:" -ForegroundColor Cyan
    Get-Content -LiteralPath $latest.FullName -Tail 120
}
else {
    Write-Warning "No PSM log file was found in $logDir"
}

exit $exitCode
