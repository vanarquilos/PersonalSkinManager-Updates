# PSM v1.0.5: compare working Python-source tools with frozen QA tools.
# READ ONLY. No EXE launch, binary copy, installation, game modification or bypass.
param(
    [Parameter(Mandatory=$true)][string]$SourceRepo,
    [Parameter(Mandatory=$true)][string]$FrozenExe
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Src = (Resolve-Path -LiteralPath $SourceRepo).Path
$Exe = (Resolve-Path -LiteralPath $FrozenExe).Path
if ((Split-Path -Leaf $Exe) -ne "PersonalSkinManager.exe") {
    throw "FrozenExe must identify PersonalSkinManager.exe."
}
$SourceTools = Join-Path $Src "injection\tools"
$App = Split-Path -Parent $Exe
$Folders = @(
    (Join-Path $App "_internal\injection\tools"),
    (Join-Path $App "injection\tools")
)
$Existing = @($Folders | Where-Object { Test-Path -LiteralPath $_ -PathType Container })
if ($Existing.Count -ne 1) {
    throw "Expected one frozen runtime tools directory; found $($Existing.Count)."
}
$FrozenTools = $Existing[0]
$Names = @(
    "mod-tools.exe", "cslol-dll.dll",
    "ltk_patcher_host.exe", "ltk_patcher_dll.dll"
)
$Report = @()
foreach ($Name in $Names) {
    $A = Join-Path $SourceTools $Name
    $B = Join-Path $FrozenTools $Name
    $SourceFound = Test-Path -LiteralPath $A -PathType Leaf
    $FrozenFound = Test-Path -LiteralPath $B -PathType Leaf
    $Match = if ($SourceFound -and $FrozenFound) {
        if ((Get-FileHash -LiteralPath $A -Algorithm SHA256).Hash -eq
            (Get-FileHash -LiteralPath $B -Algorithm SHA256).Hash) {
            "IDENTICAL"
        } else { "DIFFERENT" }
    } elseif ($SourceFound) { "SOURCE_ONLY" }
      elseif ($FrozenFound) { "FROZEN_ONLY" }
      else { "ABSENT_BOTH" }
    $Report += [PSCustomObject]@{ Component = $Name; FileIdentity = $Match }
}
$Report | Format-Table -AutoSize
$Ltk = @($Report | Where-Object { $_.Component -like "ltk_patcher_*" })
if (@($Ltk | Where-Object { $_.FileIdentity -eq "SOURCE_ONLY" }).Count -eq 2) {
    Write-Warning "The source has an LTK host/DLL but the frozen app DOES NOT. Default Rose-style builds require separate user provisioning before skin QA."
} elseif (@($Ltk | Where-Object { $_.FileIdentity -eq "DIFFERENT" }).Count -gt 0) {
    Write-Warning "The frozen host/DLL differs from the source pair. Past source rendering cannot validate this frozen runtime."
} elseif (@($Ltk | Where-Object { $_.FileIdentity -eq "IDENTICAL" }).Count -eq 2) {
    Write-Host "Matching LTK host/DLL file identities in source and frozen QA." -ForegroundColor Green
    Write-Warning "Matching binaries alone do NOT prove game hooking, skin rendering, license compliance or release readiness."
} else {
    Write-Warning "Missing or incomplete LTK pair. No positive runtime parity demonstrated."
}
Write-Host "Read-only inventory finished. No DLL, executable or application was modified."
