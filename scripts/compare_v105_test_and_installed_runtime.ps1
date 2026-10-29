# Read-only PSM source tester vs installed runtime fingerprint comparison.
param([string]$InstalledDir = "C:\Program Files\Personal Skin Manager")
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Groups = [ordered]@{
    "working tester" = Join-Path $Root "injection\tools"
    "official reference" = Join-Path $Root "installer\candidates\v1.0.5\audit-only-ltk-v1.28.1"
    "unsigned release input" = Join-Path $Root "installer\candidates\v1.0.5\release-unsigned-ltk"
    "build output" = Join-Path $Root "dist\PersonalSkinManager"
    "installed PSM" = $InstalledDir
}
$Names = @("ltk_patcher_host.exe", "ltk_patcher_dll.dll")
$Rows = @()
foreach ($Group in $Groups.Keys) {
    foreach ($Name in $Names) {
        # Source and reference directories contain other nested copies; inspect
        # only the actual runtime file in each expected location.
        if ($Group -eq "build output" -or $Group -eq "installed PSM") {
            $Base = Join-Path $Groups[$Group] "_internal\injection\tools"
            $Candidate = Join-Path $Base $Name
            if (-not (Test-Path -LiteralPath $Candidate -PathType Leaf)) {
                $Candidate = Join-Path (Join-Path $Groups[$Group] "injection\tools") $Name
            }
        } else {
            $Candidate = Join-Path $Groups[$Group] $Name
        }
        $Items = @()
        if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
            $Items = @(Get-Item -LiteralPath $Candidate)
        }
        if ($Items.Count -eq 1) {
            $Rows += [pscustomobject]@{
                group = $Group
                file = $Name
                status = "found"
                sha256 = (Get-FileHash -LiteralPath $Items[0].FullName -Algorithm SHA256).Hash
                signature = [string](Get-AuthenticodeSignature -LiteralPath $Items[0].FullName).Status
            }
        } else {
            $Rows += [pscustomobject]@{
                group = $Group
                file = $Name
                status = "found $($Items.Count)"
                sha256 = ""
                signature = ""
            }
        }
    }
}
$Rows | Format-Table -AutoSize group,file,status,signature,sha256
Write-Host "Full fingerprints:"
$Rows | ForEach-Object { Write-Host ("{0} | {1} | {2} | {3}" -f $_.group, $_.file, $_.signature, $_.sha256) }
foreach ($Name in $Names) {
    $Source = @($Rows | Where-Object { $_.group -eq "working tester" -and $_.file -eq $Name })[0]
    $Installed = @($Rows | Where-Object { $_.group -eq "installed PSM" -and $_.file -eq $Name })[0]
    if ($Source.status -ne "found" -or $Installed.status -ne "found") {
        Write-Warning "${Name}: cannot compare; verify installed directory."
    } elseif ($Source.sha256 -ne $Installed.sha256) {
        Write-Warning "${Name}: installed copy differs from working tester."
    } else {
        Write-Host "$Name matches the tester byte-for-byte." -ForegroundColor Green
    }
}
Write-Host ""
Write-Host "Interpretation: Different hashes are EXPECTED after Authenticode signature removal." -ForegroundColor Cyan
Write-Host "This report alone cannot establish why the packaged version shows a default skin."
Write-Host "Retain the working source runtime. Capture a sanitized log from the installed candidate before altering binaries."
Write-Host "Read-only comparison finished. No files modified." -ForegroundColor Cyan
