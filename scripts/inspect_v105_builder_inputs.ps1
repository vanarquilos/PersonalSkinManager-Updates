# PSM v1.0.5 - read-only four-component packaging comparison.
# Inspects local source, official LTK reference, unsigned stage, build output,
# and installed copy. Does not launch a host, run League, alter files or publish.
param(
    [string]$InstalledDir = "C:\Program Files\Personal Skin Manager"
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Source = Join-Path $Root "injection\tools"
$Official = Join-Path $Root "installer\candidates\v1.0.5\audit-only-ltk-v1.28.1"
$Unsigned = Join-Path $Root "installer\candidates\v1.0.5\release-unsigned-ltk"
$Dist = Join-Path $Root "dist\PersonalSkinManager"
$Names = @("mod-tools.exe", "cslol-dll.dll", "ltk_patcher_host.exe", "ltk_patcher_dll.dll")
$Ltk = @("ltk_patcher_host.exe", "ltk_patcher_dll.dll")
$Groups = [ordered]@{
    "source-active" = $Source
    "ltk-official-reference" = $Official
    "ltk-unsigned-stage" = $Unsigned
    "frozen-build" = $Dist
    "installed-package" = $InstalledDir
}
$KnownBad = @{
    "ltk_patcher_host.exe" = "5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9"
    "ltk_patcher_dll.dll" = "B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29"
}
$Rows = @()

function Resolve-RuntimeFile([string]$Group, [string]$Base, [string]$Name) {
    if ($Group -eq "frozen-build" -or $Group -eq "installed-package") {
        $Possibilities = @(
            (Join-Path (Join-Path $Base "_internal\injection\tools") $Name),
            (Join-Path (Join-Path $Base "injection\tools") $Name)
        )
        foreach ($Candidate in $Possibilities) {
            if (Test-Path -LiteralPath $Candidate -PathType Leaf) { return $Candidate }
        }
        return $Possibilities[0]
    }
    return (Join-Path $Base $Name)
}

foreach ($Group in $Groups.Keys) {
    foreach ($Name in $Names) {
        if ($Group -in @("ltk-official-reference", "ltk-unsigned-stage") -and $Name -notin $Ltk) {
            continue # CSLOL/mod-tools are not inputs from these LTK-only directories.
        }
        $Path = Resolve-RuntimeFile $Group $Groups[$Group] $Name
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
            $Rows += [pscustomobject]@{
                group = $Group; component = $Name; present = $false
                size_bytes = $null; sha256 = ""; signature = "MISSING"
            }
            continue
        }
        $Item = Get-Item -LiteralPath $Path
        $Signature = Get-AuthenticodeSignature -LiteralPath $Path
        $Rows += [pscustomobject]@{
            group = $Group
            component = $Name
            present = $true
            size_bytes = [int64]$Item.Length
            sha256 = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
            signature = [string]$Signature.Status
        }
    }
}

function Get-Row([string]$Group, [string]$Name) {
    return @($Rows | Where-Object { $_.group -eq $Group -and $_.component -eq $Name })[0]
}

Write-Host "PSM v1.0.5 - four-component runtime fingerprint audit" -ForegroundColor Cyan
Write-Host "READ ONLY: no runtime, installer, game, project file, or registry entry modified."
$Rows | Format-Table group, component, present, size_bytes, signature, sha256 -AutoSize -Wrap
$Problems = [System.Collections.Generic.List[string]]::new()
foreach ($Name in $Names) {
    $SourceRow = Get-Row "source-active" $Name
    $InstalledRow = Get-Row "installed-package" $Name
    if (-not $SourceRow.present) { $Problems.Add("Source component missing: $Name") }
    if (-not $InstalledRow.present) { $Problems.Add("Installed component missing: $Name") }
    if ($SourceRow.present -and $InstalledRow.present) {
        if ($SourceRow.sha256 -eq $InstalledRow.sha256) {
            Write-Host "MATCH: $Name source and installed bytes are identical." -ForegroundColor Green
        } else {
            Write-Host "DIFFERENT: $Name source and installed bytes differ." -ForegroundColor Yellow
        }
    }
}
foreach ($Name in $Ltk) {
    $OfficialRow = Get-Row "ltk-official-reference" $Name
    $UnsignedRow = Get-Row "ltk-unsigned-stage" $Name
    $InstalledRow = Get-Row "installed-package" $Name
    if (-not $OfficialRow.present) { $Problems.Add("Original LTK reference missing: $Name") }
    if (-not $UnsignedRow.present) { $Problems.Add("Unsigned stage missing: $Name") }
    if ($OfficialRow.present -and $UnsignedRow.present) {
        if ($OfficialRow.sha256 -eq $UnsignedRow.sha256) {
            $Problems.Add("LTK staged file identical to original (signature not removed?): $Name")
        }
        if ($UnsignedRow.signature -ne "NotSigned") {
            $Problems.Add("LTK staged file not confirmed unsigned: $Name ($($UnsignedRow.signature))")
        }
    }
    if ($InstalledRow.present -and $UnsignedRow.present -and $InstalledRow.sha256 -ne $UnsignedRow.sha256) {
        $Problems.Add("Installed LTK file differs from unsigned stage: $Name")
    }
}
$StageHost = Get-Row "ltk-unsigned-stage" "ltk_patcher_host.exe"
$StageDll = Get-Row "ltk-unsigned-stage" "ltk_patcher_dll.dll"
if ($StageHost.present -and $StageDll.present -and
    $StageHost.sha256 -eq $KnownBad["ltk_patcher_host.exe"] -and
    $StageDll.sha256 -eq $KnownBad["ltk_patcher_dll.dll"]) {
    $Problems.Add("KNOWN FAILURE: staged LTK unsigned pair matches prior SetWindowsHookEx failure. Do not rebuild identical RC.")
}
$Cslol = Get-Row "installed-package" "cslol-dll.dll"
if ($Cslol.present) {
    Write-Host "CSLOL SIGNING OBSERVATION: $($Cslol.signature) - this does NOT establish publisher certificate, timestamp, content-policy compliance or redistribution permission." -ForegroundColor Yellow
}
Write-Host ""
if ($Problems.Count -eq 0) {
    Write-Host "Fingerprint comparison completed without the checked inconsistencies." -ForegroundColor Green
} else {
    foreach ($Problem in $Problems) { Write-Warning $Problem }
}
Write-Host "No gameplay run occurred. File/signature checks cannot prove skin rendering or legal approval." -ForegroundColor Cyan
Write-Host "If original signed source works but staged unsigned source fails, investigate runtime compatibility; if both sources work but installed fails, investigate installed launch context."
Write-Host "No files were created, replaced, removed, signed, or uploaded."