# PSM v1.0.5 - READ-ONLY installed versus source-runtime parity audit.
# Does not launch the patcher, game, installer, build process, or change files.
# Intended for separately staged LTK unsigned source QA versus an installed PSM.
param(
    [Parameter(Mandatory = $true)][string]$SourceToolsDir,
    [Parameter(Mandatory = $true)][string]$UnsignedLtkDir,
    [string]$InstalledDir = "C:\Program Files\Personal Skin Manager",
    [ValidateSet("Unknown", "HistoricalUnsignedFailed", "WorkingPrivate")]
    [string]$InstalledIdentity = "Unknown"
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Names = @("mod-tools.exe", "cslol-dll.dll", "ltk_patcher_host.exe", "ltk_patcher_dll.dll")
$LtkNames = @("ltk_patcher_host.exe", "ltk_patcher_dll.dll")
$KnownUnsigned = @{
    "ltk_patcher_host.exe" = "5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9"
    "ltk_patcher_dll.dll" = "B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29"
}
$Groups = [ordered]@{
    "source-tools" = $SourceToolsDir
    "unsigned-qa-ltk" = $UnsignedLtkDir
    "installed-psm" = $InstalledDir
}

function Get-FileRecord([string]$Path, [string]$Group, [string]$Name, [string]$Layout) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return [pscustomobject]@{
            group = $Group; component = $Name; exists = $false
            location = $Layout; size_bytes = 0; sha256 = ""; signature = "MISSING"
        }
    }
    $File = Get-Item -LiteralPath $Path
    return [pscustomobject]@{
        group = $Group
        component = $Name
        exists = $true
        location = $Layout
        size_bytes = [long]$File.Length
        sha256 = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
        signature = [string](Get-AuthenticodeSignature -LiteralPath $Path).Status
    }
}
function Find-InstalledFile([string]$Name) {
    $Candidates = @(
        @{ path = (Join-Path $InstalledDir ("_internal\injection\tools\" + $Name)); label = "_internal/injection/tools" },
        @{ path = (Join-Path $InstalledDir ("injection\tools\" + $Name)); label = "injection/tools" }
    )
    $Found = @($Candidates | Where-Object { Test-Path -LiteralPath $_.path -PathType Leaf })
    if ($Found.Count -eq 0) {
        return @{ path = $Candidates[0].path; label = "MISSING"; duplicates = 0 }
    }
    return @{ path = $Found[0].path; label = $Found[0].label; duplicates = $Found.Count }
}
function Row-For([string]$Group, [string]$Name) {
    return @($Rows | Where-Object { $_.group -eq $Group -and $_.component -eq $Name })[0]
}

Write-Host "PSM v1.0.5 installed-versus-unsigned-source parity audit" -ForegroundColor Cyan
Write-Host "Installed identity supplied by operator: $InstalledIdentity"
Write-Host "This audit is READ ONLY. No original runtime, installer or League files changed."
Write-Warning "The existing installed PSM may be the WORKING private version, not the previously failed unsigned build."
$Rows = @()
$Warnings = [System.Collections.Generic.List[string]]::new()
$InstalledLayout = [ordered]@{}
foreach ($Name in $Names) {
    $Source = Join-Path $SourceToolsDir $Name
    $Rows += Get-FileRecord $Source "source-tools" $Name "injection/tools"
    if ($Name -in $LtkNames) {
        $Unsigned = Join-Path $UnsignedLtkDir $Name
        $Rows += Get-FileRecord $Unsigned "unsigned-qa-ltk" $Name "staged-LTK-only"
    }
    $Location = Find-InstalledFile $Name
    $Rows += Get-FileRecord $Location.path "installed-psm" $Name $Location.label
    $InstalledLayout[$Name] = $Location.label
    if ($Location.duplicates -gt 1) {
        $Warnings.Add("Duplicate installed copies of $Name in distinct supported layouts.")
    }
}
$Rows | Format-Table group, component, exists, location, size_bytes, signature, sha256 -AutoSize
Write-Host "Comparisons:" -ForegroundColor Cyan
$UnsignedVerified = $true
foreach ($Name in $Names) {
    $Source = Row-For "source-tools" $Name
    $Installed = Row-For "installed-psm" $Name
    if (-not $Source.exists) { $Warnings.Add("Source file missing: $Name") }
    if (-not $Installed.exists) {
        $Warnings.Add("Installed file missing: $Name")
        continue
    }
    if ($Name -in $LtkNames) {
        $Unsigned = Row-For "unsigned-qa-ltk" $Name
        if (-not $Unsigned.exists) {
            $UnsignedVerified = $false
            $Warnings.Add("Unsigned QA input missing: $Name")
            continue
        }
        if ($Unsigned.sha256 -ne $KnownUnsigned[$Name]) {
            $UnsignedVerified = $false
            $Warnings.Add("Unsigned QA input differs from the previously inspected pair: $Name")
        }
        if ($Installed.sha256 -eq $Unsigned.sha256) {
            Write-Host "LTK $Name : installed matches unsigned source QA bytes" -ForegroundColor Green
        } else {
            Write-Host "LTK $Name : installed differs from unsigned source QA bytes" -ForegroundColor Yellow
        }
    } elseif ($Source.exists) {
        if ($Installed.sha256 -eq $Source.sha256) {
            Write-Host "$Name : installed matches original source-tools bytes" -ForegroundColor Green
        } else {
            Write-Host "$Name : installed differs from original source-tools bytes" -ForegroundColor Yellow
        }
    }
}
$LayoutNames = @($InstalledLayout.Values | Where-Object { $_ -ne "MISSING" } | Sort-Object -Unique)
if ($LayoutNames.Count -gt 1) {
    $Warnings.Add("Installed runtime components occupy inconsistent directory layouts.")
} elseif ($LayoutNames.Count -eq 1) {
    Write-Host ("Installed tools appear co-located: " + $LayoutNames[0])
}
$InstalledExe = Join-Path $InstalledDir "PersonalSkinManager.exe"
if (Test-Path -LiteralPath $InstalledExe -PathType Leaf) {
    $AppFile = Get-Item -LiteralPath $InstalledExe
    Write-Host ("Installed PSM EXE SHA-256: " +
        (Get-FileHash -LiteralPath $InstalledExe -Algorithm SHA256).Hash.ToUpperInvariant())
    Write-Host ("Installed PSM EXE file version: " + [string]$AppFile.VersionInfo.FileVersion)
} else {
    $Warnings.Add("Installed PSM executable missing from selected installed directory.")
}
$LogDir = Join-Path $env:LOCALAPPDATA "Rose\logs"
$Recent = @(Get-ChildItem -LiteralPath $LogDir -File -Filter "rose_*.log*" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1)
if ($Recent.Count -eq 1) {
    $AgeMinutes = [int][math]::Round(((Get-Date) - $Recent[0].LastWriteTime).TotalMinutes)
    Write-Host ("Newest shared Rose log age (minutes): " + $AgeMinutes)
    Write-Warning "Shared Rose logs cannot be attributed to the installed application from this audit."
}
if ($UnsignedVerified) {
    Write-Host "Staged LTK file hashes match the source-tested unsigned pair." -ForegroundColor Green
    Write-Host "User reported visible custom-skin rendering from source QA; this is not a packaged QA pass."
}
if ($InstalledIdentity -ne "HistoricalUnsignedFailed") {
    Write-Warning "Do not interpret current installed fingerprints as evidence for the old failed unsigned installation."
}
foreach ($Notice in $Warnings) { Write-Warning $Notice }
Write-Host "No runtime binaries were modified. No installer built. No public release approved."
