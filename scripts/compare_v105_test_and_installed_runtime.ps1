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
        $Items = @(Get-ChildItem -LiteralPath $Groups[$Group] -Recurse -File -Filter $Name -ErrorAction SilentlyContinue)
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
foreach ($Name in $Names) {
    $Source = @($Rows | Where-Object { $_.group -eq "working tester" -and $_.file -eq $Name })[0]
    $Installed = @($Rows | Where-Object { $_.group -eq "installed PSM" -and $_.file -eq $Name })[0]
    if ($Source.status -ne "found" -or $Installed.status -ne "found") {
        Write-Warning "$Name: cannot compare; verify installed directory."
    } elseif ($Source.sha256 -ne $Installed.sha256) {
        Write-Warning "$Name: installed copy differs from working tester."
    } else {
        Write-Host "$Name matches the tester byte-for-byte." -ForegroundColor Green
    }
}
Write-Host "Read-only comparison finished. No files modified." -ForegroundColor Cyan
