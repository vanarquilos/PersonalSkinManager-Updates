# PSM v1.0.5 - elevated, evidence-grounded SOURCE LTK QA.
# Unlike the old source tester, this refuses non-admin PowerShell so PSM
# cannot drop the QA override during its automatic UAC relaunch.
# Never swaps or re-signs vendor files, installs packages or publishes builds.
param(
    [Parameter(Mandatory = $true)][string]$SourceRepo,
    [ValidateSet("Unsigned", "Original")][string]$Variant = "Unsigned"
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if ($env:OS -ne "Windows_NT") { throw "Windows required." }
$Me = [Security.Principal.WindowsIdentity]::GetCurrent()
$Role = [Security.Principal.WindowsPrincipal]::new($Me)
if (-not $Role.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Start an Administrator PowerShell FIRST; source QA cannot use a UAC relaunch."
}
$Root = (Resolve-Path -LiteralPath $SourceRepo).Path
$SourceTools = Join-Path $Root "injection\tools"
$Dir = if ($Variant -eq "Unsigned") {
    Join-Path $Root "installer\candidates\v1.0.5\release-unsigned-ltk"
} else {
    Join-Path $Root "installer\candidates\v1.0.5\audit-only-ltk-v1.28.1"
}
$Signed = @{
    "ltk_patcher_host.exe" = "23FA1AAEDA1A0C743DA44227F179084E1FB81C7CD262144A3C8604FFC49D3BC1"
    "ltk_patcher_dll.dll" = "6D419057E6667994BA752AD0FB089B363DB98267618644D7F7B6632441A21D74"
}
$Unsigned = @{
    "ltk_patcher_host.exe" = "5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9"
    "ltk_patcher_dll.dll" = "B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29"
}
$Expected = if ($Variant -eq "Unsigned") { $Unsigned } else { $Signed }
if (-not (Test-Path -LiteralPath (Join-Path $Root "main.py") -PathType Leaf)) {
    throw "Source repository main.py not found."
}
if (-not (Test-Path -LiteralPath (Join-Path $SourceTools "mod-tools.exe") -PathType Leaf)) {
    throw "Working source overlay builder missing."
}
foreach ($Name in $Signed.Keys) {
    $Source = Join-Path $SourceTools $Name
    $Candidate = Join-Path $Dir $Name
    if (-not (Test-Path -LiteralPath $Source -PathType Leaf) -or
        -not (Test-Path -LiteralPath $Candidate -PathType Leaf)) {
        throw "Required original or QA file missing: $Name"
    }
    if ((Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash -ne $Signed[$Name]) {
        throw "Signed original changed: $Name. No source QA started."
    }
    if ((Get-FileHash -LiteralPath $Candidate -Algorithm SHA256).Hash -ne $Expected[$Name]) {
        throw "Selected QA binary changed: $Name. No source QA started."
    }
}
$Running = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -in @("PersonalSkinManager", "League of Legends",
        "League of Legends (TM) Client", "ltk_patcher_host")
})
if ($Running.Count -gt 0) {
    throw "Close all PSM, League gameplay and LTK host processes before the comparison."
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Python not found." }
$Previous = [Environment]::GetEnvironmentVariable("PSM_LTK_QA_RUNTIME_DIR", "Process")
Push-Location -LiteralPath $Root
try {
    $env:PSM_LTK_QA_RUNTIME_DIR = (Resolve-Path -LiteralPath $Dir).Path
    # This probe runs under the same elevated PowerShell token and environment
    # as main.py, and asks PSM's own patcher selector for its ACTUAL choice.
    $Probe = @'
import os
from pathlib import Path
from injection.tools.patcher import (
    LTK_PATCHER_HOST, LTK_PATCHER_DLL, LTK_QA_ORIGINAL_SHA256,
    LTK_QA_UNSIGNED_SHA256, _hash_file, check_ltk_patcher,
)
status = check_ltk_patcher(Path("injection/tools"))
if status.missing:
    raise SystemExit("QA selector refused runtime: " + str(status.missing))
pair = {LTK_PATCHER_HOST: _hash_file(status.host), LTK_PATCHER_DLL: _hash_file(status.dll)}
expected = os.environ["PSM_EXPECTED_SOURCE_QA_VARIANT"]
label = "unsigned-qa-pair" if pair == LTK_QA_UNSIGNED_SHA256 else (
    "signed-original-pair" if pair == LTK_QA_ORIGINAL_SHA256 else "other-pair")
if label != expected:
    raise SystemExit("Wrong runtime selected: " + label + "; expected " + expected)
if status.host.parent.resolve() != Path(os.environ["PSM_LTK_QA_RUNTIME_DIR"]).resolve():
    raise SystemExit("LTK selector did not use the requested directory")
print("Confirmed selected source runtime: " + label)
print("Source QA override inherited: True")
'@
    $PrevLabel = [Environment]::GetEnvironmentVariable("PSM_EXPECTED_SOURCE_QA_VARIANT", "Process")
    try {
        $env:PSM_EXPECTED_SOURCE_QA_VARIANT = if ($Variant -eq "Unsigned") {
            "unsigned-qa-pair"
        } else { "signed-original-pair" }
        & python -c $Probe
        if ($LASTEXITCODE -ne 0) { throw "Selected LTK provenance verification failed." }
    }
    finally {
        [Environment]::SetEnvironmentVariable("PSM_EXPECTED_SOURCE_QA_VARIANT", $PrevLabel, "Process")
    }
    $TestStart = Get-Date
    Write-Host ("ELEVATED SOURCE QA START: " + $TestStart.ToString("yyyy-MM-dd HH:mm:ss")) -ForegroundColor Cyan
    Write-Host ("Selected LTK pair: " + $Variant)
    Write-Host "Start League and enter Practice Tool while Python PSM is running." -ForegroundColor Cyan
    Write-Host "Close PSM normally after the test; this window must remain open." -ForegroundColor Yellow
    & python ".\main.py" --dev --debug --logs
    $ExitCode = $LASTEXITCODE
    Write-Host ("SOURCE QA ENDED; Python exit code: " + $ExitCode)
    Write-Host ("For sanitized logs use -SinceLocal ([datetime]'" + $TestStart.ToString("yyyy-MM-dd HH:mm:ss") + "')")
}
finally {
    [Environment]::SetEnvironmentVariable("PSM_LTK_QA_RUNTIME_DIR", $Previous, "Process")
    Pop-Location
}
Write-Host "Working source files were never replaced. Source QA is NOT public installer approval."
