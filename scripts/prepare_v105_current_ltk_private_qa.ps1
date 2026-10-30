# PSM v1.0.5: prepare CURRENT LTK pair for PRIVATE local QA only.
# Requires independently obtained, verified local files and expected hashes.
# This creates only an isolated JSON *test manifest*, never copies binaries,
# patches vendor security, accesses a patcher delivery service or publishes.
param(
    [Parameter(Mandatory = $true)][string]$LtkDir,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Fa-f0-9]{64}$')][string]$ExpectedHostSha256,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Fa-f0-9]{64}$')][string]$ExpectedDllSha256,
    [Parameter(Mandatory = $true)][string]$OutputManifest,
    [ValidatePattern('^v[0-9]+\.[0-9]+\.[0-9]+$')]
    [string]$SourceManagerRelease = "v1.31.1"
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if ($env:OS -ne "Windows_NT") { throw "Windows-only local QA." }
$Directory = (Resolve-Path -LiteralPath $LtkDir).Path
$Out = [IO.Path]::GetFullPath($OutputManifest)
if (Test-Path -LiteralPath $Out) {
    throw "QA manifest already exists; will not overwrite it."
}
if ($Out.StartsWith($Directory + "\", [StringComparison]::OrdinalIgnoreCase)) {
    throw "Keep the QA manifest outside the vendor runtime directory."
}
$OriginalKnownBad = @{
    "ltk_patcher_host.exe" = "5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9"
    "ltk_patcher_dll.dll" = "B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29"
}
$Expected = [ordered]@{
    "ltk_patcher_host.exe" = $ExpectedHostSha256.ToUpperInvariant()
    "ltk_patcher_dll.dll" = $ExpectedDllSha256.ToUpperInvariant()
}
if ($Expected["ltk_patcher_host.exe"] -eq $OriginalKnownBad["ltk_patcher_host.exe"] -and
    $Expected["ltk_patcher_dll.dll"] -eq $OriginalKnownBad["ltk_patcher_dll.dll"]) {
    throw "Refusing the previously failed v1.28.1 unsigned pair as a current candidate."
}
$Observed = [ordered]@{}
foreach ($Name in $Expected.Keys) {
    $File = Join-Path $Directory $Name
    if (-not (Test-Path -LiteralPath $File -PathType Leaf)) {
        throw "Required LTK input missing: $Name"
    }
    $Attributes = Get-Item -LiteralPath $File
    if (($Attributes.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Symlink/reparse-point LTK input not accepted."
    }
    $Hash = (Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($Hash -ne $Expected[$Name]) { throw "Input digest differs from independently specified $Name SHA-256" }
    $Signature = Get-AuthenticodeSignature -LiteralPath $File
    if ($Signature.Status -ne "Valid" -or $null -eq $Signature.SignerCertificate) {
        throw "Private upstream provenance cannot be verified by Authenticode for $Name."
    }
    $Observed[$Name] = [ordered]@{
        sha256 = $Hash
        authenticode_status = [string]$Signature.Status
        signer_subject = [string]$Signature.SignerCertificate.Subject
    }
}
$Parent = Split-Path -Path $Out -Parent
if (-not (Test-Path -LiteralPath $Parent -PathType Container)) {
    throw "Output parent directory does not exist; create a separate local QA directory first."
}
$Manifest = [ordered]@{
    schema = 1
    purpose = "PSM_V105_PRIVATE_QA_ONLY"
    source_manager_release = $SourceManagerRelease
    host_protocol = 3
    public_distribution_approved = $false
    files_sha256 = [ordered]@{
        "ltk_patcher_host.exe" = $Expected["ltk_patcher_host.exe"]
        "ltk_patcher_dll.dll" = $Expected["ltk_patcher_dll.dll"]
    }
}
$Manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Out -Encoding UTF8
Write-Host "PRIVATE LTK QA MANIFEST CREATED" -ForegroundColor Green
Write-Host ("Host protocol: " + $Manifest.host_protocol)
Write-Host ("Source manager release metadata: " + $SourceManagerRelease)
Write-Host "Both SHA-256 hashes and Authenticode signature statuses checked."
Write-Warning "A valid signature and hash only prove local file identity, NOT vendor delivery authorization, host protocol gameplay compatibility, or redistribution rights."
Write-Warning "Do not publish the DLLs, this manifest as permission, or any installer built with upstream-signed binaries."
