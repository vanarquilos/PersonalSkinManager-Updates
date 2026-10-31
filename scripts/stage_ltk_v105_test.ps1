# PSM v1.0.5: official pinned LTK binaries for LOCAL PRIVATE TEST ONLY.
# Source: LeagueToolkit/ltk-manager v1.30.1 commit 044e6b5...
# Redistribution requires removing the official code signatures under the
# LTK Patcher License. NEVER publish binaries staged by this test-only script.
# powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\stage_ltk_v105_test.ps1
param([string]$LeagueGameDir = "C:\Riot Games\League of Legends\Game")
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $Root
$Tools = Join-Path $Root "injection\tools"
$LegacyTest = Join-Path $Tools "_v105_rose_legacy_local_state.json"
if (Test-Path -LiteralPath $LegacyTest -PathType Leaf) {
    throw "Original LTK v1.28.1 source-test runtime is active. Do not overwrite it with v1.30.1 staging; use build_v105_distribution_candidate.ps1 for release packaging."
}
$Commit = "044e6b5fc2dfe78d92dc5a5ada3e0f57f32860f6"
$Files = @(
    @{ Name = "ltk_patcher_host.exe"; Size = 1239304; Blob = "1636152586db31d40f4331dba07e752c7a929b90" },
    @{ Name = "ltk_patcher_dll.dll"; Size = 834816; Blob = "ca984e99e5cfe1217cc706c1584b543ab7321d59" }
)
$Stage = Join-Path $Tools ("_v105_stage_" + [guid]::NewGuid().ToString("N"))
$Backup = Join-Path $Tools ("_v105_previous_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
$Audit = Join-Path $Root "installer\candidates\v1.0.5\reports\staged-runtime-audit.json"

if ($env:OS -ne "Windows_NT") { throw "This helper requires Windows." }
foreach ($Cmd in @("git", "python")) {
    if (-not (Get-Command $Cmd -ErrorAction SilentlyContinue)) { throw "$Cmd missing." }
}
if (-not (Test-Path -LiteralPath $LeagueGameDir -PathType Container)) {
    throw "League Game directory not found: $LeagueGameDir"
}
if (-not (Test-Path -LiteralPath (Join-Path $Tools "mod-tools.exe") -PathType Leaf)) {
    throw "Trusted local mod-tools.exe is missing; this script updates only the LTK pair."
}
$Active = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -in @("PersonalSkinManager", "League of Legends", "League of Legends (TM) Client", "ltk_patcher_host")
})
if ($Active.Count -gt 0) {
    throw "Close PSM, League gameplay, and any active LTK patcher before staging."
}

Write-Host "LTK v1.30.1 - pinned official runtime for PRIVATE TESTING" -ForegroundColor Cyan
Write-Host "Upstream source commit: $Commit"
New-Item -ItemType Directory -Path $Stage -Force | Out-Null
try {
    foreach ($Item in $Files) {
        $Name = $Item.Name
        $File = Join-Path $Stage $Name
        $Url = "https://raw.githubusercontent.com/LeagueToolkit/ltk-manager/$Commit/src-tauri/resources/$Name"
        Invoke-WebRequest -Uri $Url -OutFile $File -UseBasicParsing
        if ((Get-Item -LiteralPath $File).Length -ne [int64]$Item.Size) {
            throw "Unexpected size for $Name; aborting."
        }
        $Blob = (& git hash-object -- $File)
        if ($LASTEXITCODE -ne 0 -or $Blob.Trim().ToLowerInvariant() -ne $Item.Blob) {
            throw "Source Git object verification failed for $Name; aborting."
        }
        $Signature = Get-AuthenticodeSignature -LiteralPath $File
        Write-Host ("VERIFIED " + $Name + " | git blob " + $Blob.Trim() + " | signature " + $Signature.Status)
    }
    Copy-Item -LiteralPath (Join-Path $Tools "mod-tools.exe") -Destination $Stage -Force
    New-Item -ItemType Directory -Path (Split-Path -Parent $Audit) -Force | Out-Null
    $AuditLines = @(& python (Join-Path $Root "scripts\audit_runtime_v105.py") --tools-dir $Stage --game-dir $LeagueGameDir)
    $AuditExit = $LASTEXITCODE
    $AuditLines | Out-File -LiteralPath $Audit -Encoding utf8
    $AuditData = ($AuditLines -join [Environment]::NewLine) | ConvertFrom-Json
    if ($AuditExit -ne 0) {
        foreach ($Problem in @($AuditData.errors)) { Write-Host ("Audit error: " + $Problem) }
        throw "Official runtime pair failed the local cutoff audit."
    }
    if ($null -eq $AuditData.game_build_pe_timestamp -or $null -eq $AuditData.dll_cutoff_pe_timestamp) {
        throw "Game or DLL build timestamp is unknown; refusing to stage."
    }
    Write-Host ("League build: " + $AuditData.game_build_utc)
    Write-Host ("LTK DLL cutoff: " + $AuditData.dll_cutoff_utc)

    New-Item -ItemType Directory -Path $Backup -Force | Out-Null
    foreach ($Item in $Files) {
        $Old = Join-Path $Tools $Item.Name
        if (Test-Path -LiteralPath $Old -PathType Leaf) {
            Copy-Item -LiteralPath $Old -Destination (Join-Path $Backup $Item.Name) -Force
        }
    }
    try {
        foreach ($Item in $Files) {
            Copy-Item -LiteralPath (Join-Path $Stage $Item.Name) -Destination (Join-Path $Tools $Item.Name) -Force
            $Blob = (& git hash-object -- (Join-Path $Tools $Item.Name))
            if ($LASTEXITCODE -ne 0 -or $Blob.Trim().ToLowerInvariant() -ne $Item.Blob) {
                throw "Post-copy integrity verification failed for $($Item.Name)"
            }
        }
    }
    catch {
        foreach ($Item in $Files) {
            $Old = Join-Path $Backup $Item.Name
            if (Test-Path -LiteralPath $Old -PathType Leaf) {
                Copy-Item -LiteralPath $Old -Destination (Join-Path $Tools $Item.Name) -Force
            }
        }
        throw
    }
    $Record = [ordered]@{
        purpose = "LOCAL TEST ONLY - DO NOT REDISTRIBUTE WITH OFFICIAL SIGNATURES"
        source = "LeagueToolkit/ltk-manager"
        source_commit = $Commit
        source_tag = "v1.30.1"
        created_utc = (Get-Date).ToUniversalTime().ToString("o")
        host_blob = $Files[0].Blob
        dll_blob = $Files[1].Blob
        league_build_utc = $AuditData.game_build_utc
        dll_cutoff_utc = $AuditData.dll_cutoff_utc
        backup_folder = $Backup
    }
    $Record | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Tools "_v105_runtime_origin.json") -Encoding UTF8
    Write-Host "LOCAL RUNTIME STAGED. Backup: $Backup" -ForegroundColor Green
    Write-Host "Next: build a local TEST installer. This does NOT prove in-game compatibility."
    Write-Warning "Do not publish a PSM installer containing League Toolkit's official signatures."
}
finally {
    if (Test-Path -LiteralPath $Stage -PathType Container) {
        Remove-Item -LiteralPath $Stage -Recurse -Force -ErrorAction SilentlyContinue
    }
}
