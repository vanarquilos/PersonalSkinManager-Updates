# Read-only v1.0.5 local packaging comparison. Does not start/modify the game.
# Compares source, release inputs, frozen portable output, and installed files.
param([string]$InstalledDir = "C:\Program Files\Personal Skin Manager")
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Report = Join-Path ([Environment]::GetFolderPath("Desktop")) "PSM-v1.0.5-package-parity.txt"
$Lines = [System.Collections.Generic.List[string]]::new()
$Lines.Add("PSM v1.0.5 - read-only portable vs installed LTK comparison")
$Lines.Add("Generated: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"))
$Lines.Add("No directories, usernames or raw League Client logs included.")
$Lines.Add("")

$Expected = @{
    "ltk_patcher_host.exe" = "5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9"
    "ltk_patcher_dll.dll" = "B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29"
    "mod-tools.exe" = "25FA57EB81ED308DCF8E3E2ABA1E3981E1697C99752F879E84746D1D90B4CB44"
}
$Groups = [ordered]@{
    "source tester" = Join-Path $Root "injection\tools"
    "unsigned release input" = Join-Path $Root "installer\candidates\v1.0.5\release-unsigned-ltk"
    "portable frozen" = Join-Path $Root "dist\PersonalSkinManager"
    "installed PSM" = $InstalledDir
}
foreach ($Group in $Groups.GetEnumerator()) {
    $Base = $Group.Value
    if ($Group.Key -eq "portable frozen" -or $Group.Key -eq "installed PSM") {
        $ToolsDir = Join-Path $Base "_internal\injection\tools"
        if (-not (Test-Path -LiteralPath $ToolsDir -PathType Container)) {
            $ToolsDir = Join-Path $Base "injection\tools"
        }
    } else {
        $ToolsDir = $Base
    }

    $Lines.Add("GROUP: " + $Group.Key)
    foreach ($Name in @("ltk_patcher_host.exe", "ltk_patcher_dll.dll", "mod-tools.exe")) {
        if ($Group.Key -eq "unsigned release input" -and $Name -eq "mod-tools.exe") { continue }
        $Path = Join-Path $ToolsDir $Name
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
            $Lines.Add("  " + $Name + " | MISSING")
            continue
        }
        $Hash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
        $Sig = [string](Get-AuthenticodeSignature -LiteralPath $Path).Status
        $Identity = if ($Group.Key -eq "source tester") {
            "working source reference"
        } elseif ($Hash -eq $Expected[$Name]) {
            "MATCH reviewed unsigned/builder hash"
        } else {
            "DIFFERENT from reviewed unsigned/builder hash"
        }
        $Lines.Add("  " + $Name + " | " + $Identity + " | signature=" + $Sig + " | sha256=" + $Hash)
    }
    if ($Group.Key -in @("portable frozen", "installed PSM")) {
        $Exe = Join-Path $Base "PersonalSkinManager.exe"
        if (Test-Path -LiteralPath $Exe -PathType Leaf) {
            $Lines.Add("  PSM EXE | SHA256=" + (Get-FileHash -LiteralPath $Exe -Algorithm SHA256).Hash)
            $Lines.Add("  PSM EXE | bytes=" + (Get-Item -LiteralPath $Exe).Length)
        } else {
            $Lines.Add("  PSM EXE | MISSING")
        }
        foreach ($Name in @("ltk_patcher_host.exe", "ltk_patcher_dll.dll")) {
            $Copies = @(Get-ChildItem -LiteralPath $Base -Recurse -File -Filter $Name -ErrorAction SilentlyContinue)
            $Lines.Add("  copies of " + $Name + " in app directory: " + $Copies.Count)
        }
    }
    $Lines.Add("")
}
$Audit = Join-Path $Root "installer\candidates\v1.0.5\release-candidate-audit.json"
if (Test-Path -LiteralPath $Audit -PathType Leaf) {
    try {
        $Record = Get-Content -LiteralPath $Audit -Raw -Encoding UTF8 | ConvertFrom-Json
        $Lines.Add("RC audit: " + [string]$Record.launch_profile + " | installed_test=" + [string]$Record.installed_test)
        $Lines.Add("RC audit source commit: " + [string]$Record.source_commit)
    } catch {
        $Lines.Add("RC audit: present but unreadable")
    }
} else {
    $Lines.Add("RC audit: missing (release candidate not finalized)")
}
$Lines.Add("This report proves file identity, NOT that a game hook worked.")
$Lines | Set-Content -LiteralPath $Report -Encoding UTF8
$Lines | ForEach-Object { Write-Host $_ }
Write-Host "Saved Desktop report: PSM-v1.0.5-package-parity.txt" -ForegroundColor Cyan
