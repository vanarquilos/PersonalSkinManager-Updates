# Read-only installed PSM process and PE runtime inspection.
# Does not start injection, alter signature, modify game, or change files.
param([string]$InstalledDir = "C:\Program Files\Personal Skin Manager")
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Out = Join-Path ([Environment]::GetFolderPath("Desktop")) "PSM-v1.0.5-installed-context.txt"
$Rows = [System.Collections.Generic.List[string]]::new()
$Rows.Add("PSM v1.0.5 - installed process and runtime context (read-only)")
$Rows.Add("Generated: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"))
$Rows.Add("Paths, user identities and process command lines are excluded.")
$Rows.Add("")

$Files = [ordered]@{
    "source host" = Join-Path $Root "injection\tools\ltk_patcher_host.exe"
    "source dll" = Join-Path $Root "injection\tools\ltk_patcher_dll.dll"
    "installed host" = Join-Path $InstalledDir "_internal\injection\tools\ltk_patcher_host.exe"
    "installed dll" = Join-Path $InstalledDir "_internal\injection\tools\ltk_patcher_dll.dll"
}
foreach ($Key in @("installed host", "installed dll")) {
    if (-not (Test-Path -LiteralPath $Files[$Key] -PathType Leaf)) {
        $Name = Split-Path -Leaf $Files[$Key]
        $Files[$Key] = Join-Path (Join-Path $InstalledDir "injection\tools") $Name
    }
}
function PE-Machine([string]$Path) {
    $Stream = [System.IO.File]::OpenRead($Path)
    try {
        $Reader = [System.IO.BinaryReader]::new($Stream)
        $Stream.Position = 0x3c
        $PeOffset = $Reader.ReadInt32()
        if ($PeOffset -lt 64 -or $PeOffset -ge ($Stream.Length - 6)) { return "INVALID_PE" }
        $Stream.Position = $PeOffset
        if ($Reader.ReadUInt32() -ne 0x00004550) { return "INVALID_PE" }
        $Machine = $Reader.ReadUInt16()
        switch ($Machine) {
            0x8664 { return "x64" }
            0x014c { return "x86" }
            0xAA64 { return "ARM64" }
            default { return ("0x{0:X4}" -f $Machine) }
        }
    }
    finally { $Stream.Dispose() }
}
foreach ($Entry in $Files.GetEnumerator()) {
    if (-not (Test-Path -LiteralPath $Entry.Value -PathType Leaf)) {
        $Rows.Add($Entry.Key + " | MISSING")
        continue
    }
    $Hash = (Get-FileHash -LiteralPath $Entry.Value -Algorithm SHA256).Hash
    $Signed = [string](Get-AuthenticodeSignature -LiteralPath $Entry.Value).Status
    $Rows.Add($Entry.Key + " | PE=" + (PE-Machine $Entry.Value) + " | Signature=" + $Signed + " | SHA256=" + $Hash)
}
$Rows.Add("")
# No command line, executable path or account names are collected.
$ProcessNames = @("PersonalSkinManager", "ltk_patcher_host", "League of Legends", "League of Legends (TM) Client")
foreach ($Name in $ProcessNames) {
    $Processes = @(Get-Process -Name $Name -ErrorAction SilentlyContinue)
    $Rows.Add("Process " + $Name + " running instances: " + $Processes.Count)
}
$Rows.Add("")
$LogDir = Join-Path $env:LOCALAPPDATA "Rose\logs"
$Latest = @(Get-ChildItem -LiteralPath $LogDir -File -Filter "rose_*.log*" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1)
if ($Latest.Count -gt 0) {
    $Age = [int][math]::Floor(((Get-Date) - $Latest[0].LastWriteTime).TotalMinutes)
    $Rows.Add("Newest shared Rose log age (minutes): " + $Age)
    $Tail = @(Get-Content -LiteralPath $Latest[0].FullName -Tail 10000 -ErrorAction SilentlyContinue)
    $Hooks = @($Tail | Where-Object { $_ -match '(?i)SetWindowsHookEx failed|hook install failed' }).Count
    $Armed = @($Tail | Where-Object { $_ -match 'Scanner armed before League launch' }).Count
    $Rows.Add("Scanner armed messages: " + $Armed)
    $Rows.Add("Hook install failure messages: " + $Hooks)
    $Rows.Add("Shared log cannot be conclusively attributed to an installed process.")
} else {
    $Rows.Add("No shared Rose application log found.")
}
$Rows.Add("Read-only inspection complete. Files unchanged.")
$Rows | Set-Content -LiteralPath $Out -Encoding UTF8
$Rows | ForEach-Object { Write-Host $_ }
Write-Host ("Report saved on Desktop as " + (Split-Path -Leaf $Out)) -ForegroundColor Cyan
