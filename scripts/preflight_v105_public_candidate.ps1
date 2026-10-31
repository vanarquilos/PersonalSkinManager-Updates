# PSM v1.0.5 public-candidate readiness audit. Read-only; does not build or publish.
# Run locally on Windows. Do not upload signer private keys or runtime binaries.
param(
    [string]$LtkDir = "",
    [string]$CslolDir = "",
    [string]$ModToolsFile = "",
    [string]$ExpectedDistributorCertSha256 = ""
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if (-not $LtkDir) { $LtkDir = Join-Path $Root "installer\candidates\v1.0.5\release-unsigned-ltk" }
if (-not $CslolDir) { $CslolDir = Join-Path $Root "injection\tools" }
$OriginalTools = Join-Path $Root "injection\tools"
# Observed third-party DLL and signing certificate from 2026-10-30.
# Their Authenticode status can be Valid without meeting CSLOL section 5.
$KnownThirdPartyCSLOLDllSha256 = "4A009619C6DEA691780B2F20CF17E08DE478A78B3F11CD72759DD71C00AD1C90"
$KnownThirdPartyCertSha256 = "1F51EA1346FF54970541227A4A88E9B4B11FB9A0ADB6B17040DC5DB84E905CE9"
if (-not $ModToolsFile) { $ModToolsFile = Join-Path $OriginalTools "mod-tools.exe" }
$KnownBad = @{
    "ltk_patcher_host.exe" = "5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9"
    "ltk_patcher_dll.dll" = "B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29"
}
$KnownOfficialSigned = @{
    "ltk_patcher_host.exe" = "23FA1AAEDA1A0C743DA44227F179084E1FB81C7CD262144A3C8604FFC49D3BC1"
    "ltk_patcher_dll.dll" = "6D419057E6667994BA752AD0FB089B363DB98267618644D7F7B6632441A21D74"
}
$Files = [ordered]@{
    "mod-tools.exe" = $ModToolsFile
    "cslol-dll.dll" = Join-Path $CslolDir "cslol-dll.dll"
    "ltk_patcher_host.exe" = Join-Path $LtkDir "ltk_patcher_host.exe"
    "ltk_patcher_dll.dll" = Join-Path $LtkDir "ltk_patcher_dll.dll"
}
$Results = [ordered]@{}
$Blockers = New-Object System.Collections.Generic.List[string]
$Rows = @()
foreach ($Name in $Files.Keys) {
    $Path = $Files[$Name]
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        $Blockers.Add("Missing staged component: $Name")
        $Rows += [pscustomobject]@{ file = $Name; bytes = $null; signature = "MISSING"; sha256 = "" }
        continue
    }
    $Item = Get-Item -LiteralPath $Path
    $Hash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToUpperInvariant()
    $Sig = Get-AuthenticodeSignature -LiteralPath $Path
    $Rows += [pscustomobject]@{ file = $Name; bytes = $Item.Length; signature = [string]$Sig.Status; sha256 = $Hash }
    $Results[$Name] = [pscustomobject]@{
        hash = $Hash
        status = [string]$Sig.Status
        subject = if ($null -ne $Sig.SignerCertificate) { [string]$Sig.SignerCertificate.Subject } else { "" }
        timestamp_present = ($null -ne $Sig.TimeStamperCertificate)
    }
}
if ($Results.Contains("ltk_patcher_host.exe") -and $Results.Contains("ltk_patcher_dll.dll")) {
    if ($Results["ltk_patcher_host.exe"].hash -eq $KnownBad["ltk_patcher_host.exe"] -and
        $Results["ltk_patcher_dll.dll"].hash -eq $KnownBad["ltk_patcher_dll.dll"]) {
        $Blockers.Add("Unsigned LTK pair rendered a skin in SOURCE QA but failed in the earlier INSTALLED candidate (SetWindowsHookEx). Installed packaging parity remains unverified; do not publish.")
    }
}
foreach ($Name in @("ltk_patcher_host.exe", "ltk_patcher_dll.dll")) {
    if (-not $Results.Contains($Name)) { continue }
    $Sig = $Results[$Name]
    if ($Results[$Name].hash -eq $KnownOfficialSigned[$Name]) {
        $Blockers.Add("Known original upstream-signed LTK file: $Name; public bundling needs written permission.")
    }
    if ($Sig.subject -match "(?i)league\s*toolkit") {
        $Blockers.Add("Original League Toolkit publisher signature still present on $Name; cannot redistribute it in a PSM installer without written permission.")
    }
    if ($Sig.status -eq "Valid" -and $Sig.subject -notmatch "(?i)league\s*toolkit") {
        $Blockers.Add("Signed LTK publisher identity needs PSM distributor certificate review before a public build: $Name.")
    }
    if ($Sig.status -notin @("NotSigned", "Valid")) {
        $Blockers.Add("LTK signature validation failed for $Name (status: $($Sig.status)).")
    }
}
if ($Results.Contains("cslol-dll.dll")) {
    $Cslol = $Results["cslol-dll.dll"]
    if ($Cslol.status -ne "Valid") {
        $Blockers.Add("CSLOL DLL requires a valid distributor-owned, publicly trusted code-signing certificate.")
    }
    if (-not $Cslol.timestamp_present) {
        $Blockers.Add("CSLOL DLL trusted timestamp is missing or cannot be established by this audit.")
    }
    if ($Cslol.hash -eq $KnownThirdPartyCSLOLDllSha256) {
        $Blockers.Add("Observed CSLOL DLL is the existing third-party-signed copy; signature Valid does not grant PSM distribution rights.")
    }
    if ([string]::IsNullOrWhiteSpace($ExpectedDistributorCertSha256)) {
        $Blockers.Add("No PSM distributor certificate SHA-256 supplied for identity verification; public distribution cannot be approved.")
    }
    if ($Cslol.subject -match "(?i)league\s*toolkit|daniel\s*langov") {
        $Blockers.Add("CSLOL DLL bears a known non-PSM publisher signature; third-party credits do not replace distributor code signing.")
    }
}
$Trigger = Join-Path $Root "threads\handlers\injection_trigger.py"
$ContentReview = "PENDING"
if (Test-Path -LiteralPath $Trigger -PathType Leaf) {
    $SourceText = Get-Content -LiteralPath $Trigger -Raw -Encoding UTF8
    if ($SourceText.Contains("Custom mod targets unowned skin") -or
        $SourceText.Contains("unowned selected skin is added as the Rose-style carrier")) {
        $Blockers.Add("Launcher paid-skin/competitive-content enforcement requires independent review; unowned-skin carrier routing exists.")
    } else {
        $Blockers.Add("Launcher content enforcement still requires independent verification; absence of marker is not proof.")
    }
} else {
    $Blockers.Add("Launcher content enforcement cannot be audited: injection_trigger.py missing.")
}
Write-Host "PSM v1.0.5 - staged public candidate readiness" -ForegroundColor Cyan
Write-Host "READ ONLY. Four required components; no files changed."
$Rows | Format-Table file, bytes, signature, sha256 -AutoSize
if ($Results.Contains("cslol-dll.dll")) {
    $CslolSignature = Get-AuthenticodeSignature -LiteralPath $Files["cslol-dll.dll"]
    if ($null -ne $CslolSignature.SignerCertificate) {
        $PublicCertificate = $CslolSignature.SignerCertificate
        $Hasher = [System.Security.Cryptography.SHA256]::Create()
        try {
            $CertificateSha256 = [BitConverter]::ToString(
                $Hasher.ComputeHash($PublicCertificate.RawData)).Replace("-", "")
        } finally {
            $Hasher.Dispose()
        }
        Write-Host ("CSLOL certificate subject: " + $PublicCertificate.Subject)
        Write-Host ("CSLOL public certificate SHA-256: " + $CertificateSha256)
        if ($CertificateSha256 -eq $KnownThirdPartyCertSha256) {
            $Blockers.Add("CSLOL certificate fingerprint matches the known non-PSM signing certificate.")
        }
        if (-not [string]::IsNullOrWhiteSpace($ExpectedDistributorCertSha256)) {
            if ($ExpectedDistributorCertSha256.Trim().ToUpperInvariant() -notmatch "^[0-9A-F]{64}$") {
                $Blockers.Add("Provided distributor certificate SHA-256 must be 64 hexadecimal characters.")
            } elseif ($CertificateSha256 -ne $ExpectedDistributorCertSha256.Trim().ToUpperInvariant()) {
                $Blockers.Add("CSLOL signer fingerprint does not match the expected PSM distributor certificate.")
            }
        }
        Write-Host ("CSLOL timestamp certificate observed: " +
            [string]($null -ne $CslolSignature.TimeStamperCertificate))
    } else {
        Write-Warning "CSLOL signer certificate could not be inspected."
    }
}
Write-Host "Certificate identity, public CA chain, publisher ownership and content rules still require independent verification." -ForegroundColor Yellow
Write-Host "CSLOL license addendum also requires a certificate fingerprint, DLL hash disclosure, and effective content blocking."
Write-Host "LTK file identity, compatibility and visible in-game skin rendering require separate real-game QA."
Write-Host "Release requirements remain blocked until publisher authorization and complete gameplay evidence are recorded."
foreach ($Problem in $Blockers) { Write-Warning $Problem }
if ($Blockers.Count -eq 0) {
    Write-Warning "Static evidence alone cannot authorize public distribution. Manual license and gameplay approvals remain pending."
}
Write-Host "PUBLICATION: NOT APPROVED; no installer was built or released." -ForegroundColor Yellow
Write-Host "If reporting results, share only file hashes, signature statuses, and sanitized errors; never share keys or tokens."
