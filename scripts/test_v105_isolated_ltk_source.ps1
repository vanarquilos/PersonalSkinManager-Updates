# Source-only LTK A/B compatibility check. No installer, signing, copying or file mutation.
# Start with "Unsigned" after confirming the original signed source tester works.
param(
    [ValidateSet("Unsigned", "Original")]
    [string]$Variant = "Unsigned",
    [string]$LeagueGameDir = "C:\Riot Games\League of Legends\Game"
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Source = Join-Path $Root "injection\tools"
$Original = Join-Path $Root "installer\candidates\v1.0.5\audit-only-ltk-v1.28.1"
$Unsigned = Join-Path $Root "installer\candidates\v1.0.5\release-unsigned-ltk"
$HashesSigned = @{
    "ltk_patcher_host.exe" = "23FA1AAEDA1A0C743DA44227F179084E1FB81C7CD262144A3C8604FFC49D3BC1"
    "ltk_patcher_dll.dll" = "6D419057E6667994BA752AD0FB089B363DB98267618644D7F7B6632441A21D74"
}
$HashesUnsigned = @{
    "ltk_patcher_host.exe" = "5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9"
    "ltk_patcher_dll.dll" = "B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29"
}
$Selected = if ($Variant -eq "Unsigned") { $Unsigned } else { $Original }
$Expected = if ($Variant -eq "Unsigned") { $HashesUnsigned } else { $HashesSigned }
if (-not (Test-Path -LiteralPath $LeagueGameDir -PathType Container)) {
    throw "League Game directory missing. Supply -LeagueGameDir."
}
if (-not (Test-Path -LiteralPath (Join-Path $Source "mod-tools.exe") -PathType Leaf)) {
    throw "The existing source overlay-builder binary is missing."
}
foreach ($Name in $HashesSigned.Keys) {
    $Local = Join-Path $Source $Name
    $Pinned = Join-Path $Original $Name
    $TestFile = Join-Path $Selected $Name
    foreach ($Entry in @(
        @{ path = $Local; sha = $HashesSigned[$Name] },
        @{ path = $Pinned; sha = $HashesSigned[$Name] },
        @{ path = $TestFile; sha = $Expected[$Name] }
    )) {
        if (-not (Test-Path -LiteralPath $Entry.path -PathType Leaf) -or
            (Get-FileHash -LiteralPath $Entry.path -Algorithm SHA256).Hash -ne $Entry.sha) {
            throw "Input fingerprint mismatch for $Name. No game or runtime files were changed."
        }
    }
    if ((Get-AuthenticodeSignature -LiteralPath $Local).Status -ne "Valid") {
        throw "Working source runtime is not signed as expected."
    }
}
$Busy = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -in @("PersonalSkinManager", "League of Legends",
        "League of Legends (TM) Client", "ltk_patcher_host")
})
if ($Busy.Count -gt 0) {
    throw "Close PSM, League gameplay and any LTK host before starting an isolated comparison."
}
Write-Host "Source tester and selected candidate fingerprints verified." -ForegroundColor Green
Write-Host ("Isolated test pair: " + $Variant + ". No files will be replaced.") -ForegroundColor Cyan
Write-Warning "This is a PRIVATE SOURCE compatibility test. Do not publish official signed LTK binaries."
if ($Variant -eq "Unsigned") {
    Write-Warning "This same unsigned pair failed the installed PSM. Compare its behavior in the source app."
}
$Prior = [Environment]::GetEnvironmentVariable("PSM_LTK_QA_RUNTIME_DIR")
Set-Location -LiteralPath $Root
try {
    $env:PSM_LTK_QA_RUNTIME_DIR = $Selected
    & python -m unittest tests.test_ltk_qa_runtime_selector tests.test_ltk_host_protocol
    if ($LASTEXITCODE -ne 0) { throw "Focused source tests failed." }
    & powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\run_live_qa.ps1" -SkipTests
    if ($LASTEXITCODE -ne 0) { throw "Source app exited with a test failure." }
}
finally {
    [Environment]::SetEnvironmentVariable("PSM_LTK_QA_RUNTIME_DIR", $Prior)
    foreach ($Name in $HashesSigned.Keys) {
        $Active = Join-Path $Source $Name
        if ((Get-FileHash -LiteralPath $Active -Algorithm SHA256).Hash -ne $HashesSigned[$Name]) {
            Write-Error "Working source $Name changed unexpectedly. Stop; inspect before more testing."
        }
    }
    Write-Host "Working signed source binaries unchanged." -ForegroundColor Green
}
Write-Host "Record whether a non-default skin rendered in Practice Tool; source success alone does NOT approve an installer." -ForegroundColor Cyan
