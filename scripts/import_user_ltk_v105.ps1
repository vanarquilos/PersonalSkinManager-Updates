# PSM v1.0.5: explicitly import official user-owned LTK patcher binaries.
# Never downloads or edits vendor DLLs. Works only on user's local machine.
# No overwrite of existing runtime. Requires elevated permission for install dir.
param(
    [Parameter(Mandatory=$true)][string]$SourceLtkDir,
    [Parameter(Mandatory=$true)][string]$PsmExe,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Fa-f0-9]{64}$')]
    [string]$ExpectedHostSha256,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Fa-f0-9]{64}$')]
    [string]$ExpectedDllSha256
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if ($env:OS -ne "Windows_NT") { throw "This tool works only on Windows." }
$User = [Security.Principal.WindowsIdentity]::GetCurrent()
$Admin = [Security.Principal.WindowsPrincipal]::new($User)
if (-not $Admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Open PowerShell as Administrator to provision the PSM installation."
}
$Source = (Resolve-Path -LiteralPath $SourceLtkDir).Path
$Exe = (Resolve-Path -LiteralPath $PsmExe).Path
if ((Split-Path -Path $Exe -Leaf) -ne "PersonalSkinManager.exe") {
    throw "Expected the PersonalSkinManager.exe inside its installation directory."
}
$App = Split-Path -Path $Exe -Parent
$ToolCandidates = @(
    (Join-Path $App "injection\tools"),
    (Join-Path $App "_internal\injection\tools")
)
$Tools = @($ToolCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Container })
if ($Tools.Count -ne 1) {
    throw "Expected exactly one existing PSM runtime tools directory. Refusing ambiguous installation."
}
$Target = $Tools[0]
if ($Target -eq $Source -or
    $Target.StartsWith($Source + "\", [StringComparison]::OrdinalIgnoreCase)) {
    throw "Input and destination cannot be the same directory."
}
$Expected = [ordered]@{
    "ltk_patcher_host.exe" = $ExpectedHostSha256.ToUpperInvariant()
    "ltk_patcher_dll.dll" = $ExpectedDllSha256.ToUpperInvariant()
}
$KnownFailed = @{
    "ltk_patcher_host.exe" = "5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9"
    "ltk_patcher_dll.dll" = "B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29"
}
if ($Expected["ltk_patcher_host.exe"] -eq $KnownFailed["ltk_patcher_host.exe"] -and
    $Expected["ltk_patcher_dll.dll"] -eq $KnownFailed["ltk_patcher_dll.dll"]) {
    throw "The previously failed unsigned v1.28.1 pair is not an acceptable source."
}
$Manifest = Join-Path $Target "ltk-user-local.json"
foreach ($Name in @($Expected.Keys) + @("ltk-user-local.json")) {
    if (Test-Path -LiteralPath (Join-Path $Target $Name)) {
        throw "User runtime already provisioned or partially present. No overwrite permitted: $Name"
    }
}
$Busy = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -in @("PersonalSkinManager","ltk_patcher_host","League of Legends","League of Legends (TM) Client")
})
if ($Busy.Count -gt 0) { throw "Close PSM, the LTK host, and League gameplay first." }
foreach ($Name in $Expected.Keys) {
    $File = Join-Path $Source $Name
    if (-not (Test-Path -LiteralPath $File -PathType Leaf)) { throw "Missing vendor file: $Name" }
    if (((Get-Item -LiteralPath $File).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Symlink/reparse-point vendor input refused: $Name"
    }
    $Hash = (Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($Hash -ne $Expected[$Name]) { throw "The independently specified SHA-256 differs: $Name" }
    $Signature = Get-AuthenticodeSignature -LiteralPath $File
    if ($Signature.Status -ne "Valid" -or $null -eq $Signature.SignerCertificate) {
        throw "Expected a valid original vendor Authenticode signature: $Name"
    }
}
# Stage both files in the protected install location before making either active.
# On failure, clean up only files created during this explicit import operation.
$Stage = Join-Path $Target ("ltkp-qa-stage-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $Stage -ErrorAction Stop | Out-Null
$Created = New-Object System.Collections.ArrayList
try {
    foreach ($Name in $Expected.Keys) {
        $Dest = Join-Path $Stage $Name
        Copy-Item -LiteralPath (Join-Path $Source $Name) -Destination $Dest -ErrorAction Stop
        if ((Get-FileHash -LiteralPath $Dest -Algorithm SHA256).Hash.ToUpperInvariant() -ne $Expected[$Name]) {
            throw "Staged LTK input differs: $Name"
        }
    }
    foreach ($Name in $Expected.Keys) {
        $Dest = Join-Path $Target $Name
        if (Test-Path -LiteralPath $Dest) { throw "Concurrent runtime file appeared: $Name" }
        Move-Item -LiteralPath (Join-Path $Stage $Name) -Destination $Dest -ErrorAction Stop
        [void]$Created.Add($Dest)
    }
    $Record = [ordered]@{
        schema = 1
        purpose = "PSM_V105_USER_PROVIDED_LTK"
        host_protocol = 3
        public_distribution_approved = $false
        files_sha256 = $Expected
    }
    $Record | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $Manifest -Encoding UTF8 -ErrorAction Stop
    [void]$Created.Add($Manifest)
}
catch {
    foreach ($File in $Created) {
        if (Test-Path -LiteralPath $File -PathType Leaf) {
            Remove-Item -LiteralPath $File -Force -ErrorAction SilentlyContinue
        }
    }
    throw
}
finally {
    if (Test-Path -LiteralPath $Stage -PathType Container) {
        Remove-Item -LiteralPath $Stage -Recurse -Force -ErrorAction SilentlyContinue
    }
}
Write-Host "User-supplied, SHA-pinned LTK host/DLL installed into PSM." -ForegroundColor Green
Write-Host "The original vendor directory was not modified."
Write-Warning "No game/rendering, signature redistribution, or release compatibility is attested by this import."
Write-Warning "Keep patcher updates manual and reviewed; do not disable Vanguard or content integrity checks."
