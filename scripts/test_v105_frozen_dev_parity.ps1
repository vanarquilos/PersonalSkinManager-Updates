# PSM v1.0.5 frozen-vs-source startup parity test. PRIVATE QA ONLY.
# Launches an EXISTING frozen EXE in the same --dev --debug --logs mode as
# the working Python test. Does not build, install, modify binaries or bypass
# Windows/game security.
param(
    [ValidateSet("Portable", "Installed")]
    [string]$Variant = "Portable",
    [string]$InstalledDir = "C:\Program Files\Personal Skin Manager"
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$AppDir = if ($Variant -eq "Portable") { Join-Path $Root "dist\PersonalSkinManager" } else { $InstalledDir }
$Exe = Join-Path $AppDir "PersonalSkinManager.exe"
$Report = Join-Path ([Environment]::GetFolderPath("Desktop")) "PSM-v1.0.5-frozen-dev-parity.txt"
$LogDir = Join-Path $env:LOCALAPPDATA "Rose\logs"
$Start = Get-Date
$Lines = [System.Collections.Generic.List[string]]::new()
$Lines.Add("PSM v1.0.5 - frozen --dev --debug --logs QA")
$Lines.Add("Variant: " + $Variant)
$Lines.Add("Started: " + $Start.ToString("yyyy-MM-dd HH:mm:ss zzz"))
$Lines.Add("Purpose: compare with previously working Python --dev --debug --logs source launch.")
$Lines.Add("Shared application logs can be affected by other PSM instances.")
$Lines.Add("")

if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) { throw "Selected frozen PSM executable is missing." }
$ToolsDir = Join-Path $AppDir "_internal\injection\tools"
if (-not (Test-Path -LiteralPath $ToolsDir -PathType Container)) { $ToolsDir = Join-Path $AppDir "injection\tools" }
foreach ($Name in @("ltk_patcher_host.exe", "ltk_patcher_dll.dll", "mod-tools.exe")) {
    if (-not (Test-Path -LiteralPath (Join-Path $ToolsDir $Name) -PathType Leaf)) {
        throw "Selected frozen build is missing required LTK/overlay tool: $Name"
    }
}
$Lines.Add("Frozen EXE SHA256: " + (Get-FileHash -LiteralPath $Exe -Algorithm SHA256).Hash)
$Lines.Add("LTK host SHA256: " + (Get-FileHash -LiteralPath (Join-Path $ToolsDir "ltk_patcher_host.exe") -Algorithm SHA256).Hash)
$Lines.Add("LTK DLL SHA256: " + (Get-FileHash -LiteralPath (Join-Path $ToolsDir "ltk_patcher_dll.dll") -Algorithm SHA256).Hash)

$Busy = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -in @("PersonalSkinManager", "League of Legends",
        "League of Legends (TM) Client", "ltk_patcher_host")
})
if ($Busy.Count -gt 0) { throw "Close PSM, League gameplay, and LTK host before this private test." }
$Lines.Add("Launch arguments: --dev --debug --logs")
Write-Host "Private source-parity test of existing $Variant EXE; no files replaced." -ForegroundColor Cyan
Write-Warning "Use Practice Tool with a non-default skin, then exit PSM to finish capture."
Write-Warning "This --dev mode skips the production startup launcher and is NOT a release acceptance test."
$LauncherError = $null
try {
    # The old EXE may independently request elevation in Python startup code.
    # Report a possible early exit instead of asserting whether UAC occurred.
    $Proc = Start-Process -FilePath $Exe -WorkingDirectory $AppDir -ArgumentList @("--dev", "--debug", "--logs") -PassThru -Wait
    $Lines.Add("Launched process exit code: " + $Proc.ExitCode)
}
catch {
    $LauncherError = $_.Exception.GetType().Name
    $Lines.Add("Launch exception category: " + $LauncherError)
}
$End = Get-Date
$Lines.Add("Ended: " + $End.ToString("yyyy-MM-dd HH:mm:ss zzz"))
$StillRunning = @(Get-Process -Name "PersonalSkinManager" -ErrorAction SilentlyContinue).Count
$Lines.Add("PSM processes still running after launcher returned: " + $StillRunning)
if ($StillRunning -gt 0) {
    $Lines.Add("WARNING: Another PSM process may still be running. This test is not complete until it exits.")
}

# Select ONLY logs modified since this test began and keep the report sanitized.
$Recent = @(Get-ChildItem -LiteralPath $LogDir -File -Filter "rose_*.log*" -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -ge $Start.AddSeconds(-3) -and $_.LastWriteTime -le $End.AddSeconds(3) } |
    Sort-Object LastWriteTime -Descending | Select-Object -First 3)
$Lines.Add("Rose logs modified during test: " + $Recent.Count)
if ($Recent.Count -eq 0) {
    $Lines.Add("INCONCLUSIVE: no log modified during test. No failure/success conclusion.")
}
foreach ($File in $Recent) {
    $Tail = @(Get-Content -LiteralPath $File.FullName -Tail 12000 -ErrorAction SilentlyContinue)
    $Lines.Add("Fresh log modified at " + $File.LastWriteTime.ToString("HH:mm:ss"))
    $Patterns = [ordered]@{
        "Skin selection" = '(?i)Using skin file:|Skin selected:'
        "Scanner armed" = '(?i)Scanner armed before League launch'
        "Overlay prepared" = '(?i)mkoverlay completed|Overlay preparation succeeded'
        "Hook install error" = '(?i)SetWindowsHookEx failed|hook install failed'
        "Host verification refused" = '(?i)host verification failed.*refusing overlay'
        "DLL attached" = '(?i)status=inject(?:ed|ing)|dll attached'
        "DLL initialized" = '(?i)DLL overlay initialization confirmed|DLL overlay initialization observed: True'
        "WAD redirected" = '(?i)WAD redirection observed|redirected wad:'
    }
    foreach ($Entry in $Patterns.GetEnumerator()) {
        $Count = @($Tail | Where-Object { $_ -match $Entry.Value }).Count
        $Lines.Add("  " + $Entry.Key + ": " + $Count)
    }
}
$Lines.Add("Markers are observations, not proof that a non-default skin rendered.")
$Lines.Add("Capture your visual Practice Tool result separately.")
$Lines | Set-Content -LiteralPath $Report -Encoding UTF8
$Lines | ForEach-Object { Write-Host $_ }
Write-Host "Report saved: PSM-v1.0.5-frozen-dev-parity.txt (Desktop)" -ForegroundColor Cyan
