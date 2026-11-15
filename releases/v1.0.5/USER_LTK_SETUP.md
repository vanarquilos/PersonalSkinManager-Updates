# Personal Skin Manager v1.0.5 — legacy LTK import for PRIVATE QA

**This is not the current Rose runtime architecture and is not an end-user
modskin fix.** As of Rose 1.5.0 (November 5, 2026), Alban1911/Rose requires
an installed official LTK Manager and controls it through its own LTF bridge.
Recent official patcher DLLs implement host verification intended to reject
third-party direct host sessions. Importing two files into PSM, even files
with valid Authenticode signatures and SHA-256 hashes, **does not make PSM's
standalone direct-host backend authorized or functional**.

The PSM installer intentionally contains **no** `ltk_patcher_host.exe` or
`ltk_patcher_dll.dll`. PSM's library and non-injection features can run
without those files. This opt-in import procedure is retained only for
private, controlled diagnostics while an authorized runtime architecture
is evaluated. Do not distribute or call a resulting build skin-ready.

## Reviewed private QA input only

Obtain **both matching files** from LeagueToolkit's authorized release/update
channel or an existing official LTK Manager installation. Do not take files
from random mirrors, mix versions, strip signatures, modify build cutoffs, or
disable Riot/Vanguard protections.

A binary that worked on an earlier League update may now be expired.
On October 31, 2026, every LTK pair in the maintainer's seven scanned PSM
folders was expired for the October 30 League executable build. Reusing
those files will not resolve the failure.

## Optional private diagnostic setup after PSM installation (Windows PowerShell as Administrator)

Replace the example official source folder with a real location containing
the two original, signed files:

```powershell
$Source = "D:\YourOfficialLTKPair"
$PsmExe = "$env:ProgramFiles\Personal Skin Manager\PersonalSkinManager.exe"
$SetupScript = "$env:ProgramFiles\Personal Skin Manager\tools\import_user_ltk_v105.ps1"

$Host = Join-Path $Source "ltk_patcher_host.exe"
$Dll = Join-Path $Source "ltk_patcher_dll.dll"
if (-not (Test-Path $Host) -or -not (Test-Path $Dll)) {
    throw "Complete official host/DLL pair required."
}
$HostSignature = Get-AuthenticodeSignature -LiteralPath $Host
$DllSignature = Get-AuthenticodeSignature -LiteralPath $Dll
if ($HostSignature.Status -ne "Valid" -or $DllSignature.Status -ne "Valid") {
    throw "Official Authenticode signature verification failed."
}
$HostHash = (Get-FileHash -LiteralPath $Host -Algorithm SHA256).Hash
$DllHash = (Get-FileHash -LiteralPath $Dll -Algorithm SHA256).Hash

& $SetupScript -SourceLtkDir $Source -PsmExe $PsmExe -ExpectedHostSha256 $HostHash -ExpectedDllSha256 $DllHash
if ($LASTEXITCODE -ne 0) { throw "LTK provisioning failed." }
```

The installer places the script in `{app}\tools\import_user_ltk_v105.ps1`.
Provisioning writes only to the PSM runtime directory and creates a local
SHA-256 manifest. PSM uses that manifest to detect later changes. The script
does not download a binary, extend the DLL's compatibility, execute a game
process, or grant any redistribution rights. A valid digital signature and
matching hash are necessary checks, but **cannot bypass host verification or
prove that the copied DLL will run under PSM**. Current Rose does not use this
copy-based procedure.

If your PSM was installed in another folder, change `$PsmExe` and
`$SetupScript` accordingly. The script refuses to overwrite an existing
pair; it does not silently update vendor files. Back up before replacing
old, already-provisioned files through a separate reviewed update path.

## Troubleshooting

- **Missing runtime:** the legacy PSM direct-host implementation cannot apply a skin. Supplying a pair is for diagnostics only, not a confirmed fix.
- **LTK patcher outdated:** the installed game's PE build is newer than the
  selected DLL's embedded cutoff. Acquire a newer compatible official pair.
  Rebuilding the Python EXE cannot fix this.
- **Verification/host rejected:** stop instead of bypassing enforcement.
  Check upstream release compatibility and PSM logs.
- **No visible skin despite no errors:** do not claim success from
  file hashes, host startup, or overlay preparation alone. A controlled,
  permitted Practice Tool test must confirm visible rendering.

PSM and Rose are independent products. Uninstalling PSM must not uninstall
Rose or recursively erase personally provisioned LTK files.
