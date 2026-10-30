# PSM v1.0.5 — Rose-style, user-provided LeagueToolkit integration

**Implementation status:** Staged in draft PR #18; no validated release/installer and no verified visible-skin outcome. Windows unit tests and MSVC compilation are pending on the maintainer's PC.

## Uploaded legacy CSLOL binary audit — October 31, 2026

The maintainer supplied one file, `cslol-dll(1).dll`. Read-only local PE inspection (not execution) established:

- SHA-256: `4A009619C6DEA691780B2F20CF17E08DE478A78B3F11CD72759DD71C00AD1C90`; this **exactly matches** the previously recorded third-party-signed CSLOL QA component. It is not a new LeagueToolkit patcher release.
- PE32+ Windows x64 DLL, 257,040 bytes, COFF linker timestamp 2025-08-21.
- Embedded Authenticode PKCS#7 includes code-signing certificate for **Daniel Langov**, SHA-256 certificate fingerprint `1F51EA1346FF54970541227A4A88E9B4B11FB9A0ADB6B17040DC5DB84E905CE9`. Certificate validity range 2025-02-08 to 2026-02-08; presence of this certificate does **not** establish a currently valid Windows Authenticode verdict without checking a trusted signing timestamp and certificate chain on Windows.
- Exact eight PE exports: `cslol_find`, `cslol_hook`, `cslol_init`, `cslol_log_pull`, `cslol_msg_hookproc`, `cslol_set_config`, `cslol_set_flags`, `cslol_set_log_level`.
- This revealed **one genuine bug** in the PSM-authored inert loader stub: missing `cslol_msg_hookproc` export and wrong `cslol_set_flags` parameter width. Corrected the stub to implement a do-nothing message callback and match the public upstream `cslol-api.h` signatures. Added source contract regression and `dumpbin /exports` validation to the isolated MSVC build. Sample export-table parser tested locally; MSVC compilation of the actual stub is still pending on Windows.

**Do not package the maintainer's uploaded DLL**: it belongs to a different publisher. The successful historical v1.0.0–v1.0.4 gameplay behavior, if any, cannot establish compatibility with current League's 2026 hook stack. The old frozen v1.0.5 QA failed at LTK `SetWindowsHookEx` before DLL overlay initialization. Fixing CSLOL stub loader exports prevents an independent loader error, but does not itself fix the LTK/game hook.

## Why this approach

Rose (Alban1911/Rose, MIT, 2026) does not bundle the LeagueToolkit host and patcher DLL with its public installation. It asks users for the matching patcher pair, starts the host early, preserves user-supplied binaries during application updates, and compiles its own inert loader stand-in `cslol-dll.dll` for `mod-tools.exe mkoverlay`. PSM has adopted the compatible packaging, setup, and local import principles, **not** Rose's flag 4 anti-skinhack opt-out. Official LTK Manager v1.31.1 defines the existing host wire protocol and defaults to flags 0.

### Source changes

- `PersonalSkinManager.spec` and `scripts/build_pyinstaller.py`: default build no longer packages `ltk_patcher_host.exe` or `ltk_patcher_dll.dll`. Only explicit `PSM_RELEASE_LTK_DIR` in *private* QA includes those inputs. `installer.iss` also excludes user-supplied binaries and `ltk-user-local.json` so in-place upgrades do not overwrite them. **A full uninstall removes the installation's _internal directory, including user-provisioned files; back up your personally supplied pair before uninstalling.**
- `native/cslol_stub/psm_cslol_stub.c`: original PSM-authored inert exports for the `mod-tools` DLL dependency; never performs hooking or bypassing.
- `scripts/build_psm_cslol_stub.py`: compiles this stub in a separate empty folder with MSVC x64, not using a LeagueToolkit-signed CSLOL DLL.
- `injection/tools/patcher.py`: accepts a separately placed `ltk-user-local.json`, checks schema/protocol and both file hashes, refuses tampered or incomplete supplied binaries.
- `injection/tools/tools_manager.py`: now propagates manifest failure even when both physical patcher files are present.
- `scripts/import_user_ltk_v105.ps1`: explicit administrator-run opt-in importer. Requires independent expected SHA-256 of the two official unmodified files, verifies Authenticode signatures, refuses overwrites or the historical known-failed unsigned pair, stages both files before committing and writes local hash manifest. Only modifies the selected, existing PSM tools directory, never the upstream LTK directory.
- `utils/integration/ltk_onboarding.py`: a native first-launch message (installed, not `--dev`) guides users to provide their own patcher; no download and no automatic install.
- `injection/overlay/ltk_host.py`: still uses PSM's early scanner and game lifecycle, retaining LTK vendor content enforcement (`flags 0`), host verification, and game security protections.
- `scripts/build_v105_rose_style_frozen_private_qa.ps1`: builds **only in a brand-new linked worktree** on a `qa/v105-rose-*` branch; verifies mod-tools hash, compiles inert stub, runs tests, builds frozen PSM without LTK, verifies no host/DLL was included, and records `public_distribution_approved=false`.

### First: Windows regression tests

```powershell
$Original = "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
$Staging = "C:\Users\Van Arquilos\Desktop\PSM-v105-Public-Local-Test-Worktree"
git -C $Staging pull --ff-only origin release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) { throw "Git fetch failed" }
Push-Location $Staging
try {
    python -m unittest tests.test_v105_user_ltk_provisioning tests.test_v105_rose_style_build_contract tests.test_v105_current_ltk_private_manifest tests.test_v105_current_ltk_build_contract tests.test_ltk_host_protocol tests.test_release_packaging tests.test_release_skin_routing
    if ($LASTEXITCODE -ne 0) { throw "Windows unit tests failed; collect the FIRST failing test name, do not build" }
} finally { Pop-Location }
```

### Next: local frozen QA package, no LTK included

Requires Visual Studio 2022 MSVC C++ x64 build tools, existing source `mod-tools.exe`, and a clean Windows linked worktree. Close PSM, League and LTK host first.

```powershell
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Branch = "qa/v105-rose-$Stamp"
$New = "C:\Users\Van Arquilos\Desktop\PSM-v105-Rose-QA-$Stamp"
git -C $Original fetch origin release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) { throw "Git fetch failed" }
git -C $Original worktree add -b $Branch $New origin/release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) { throw "Could not create linked QA worktree" }
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned `
    -File (Join-Path $New "scripts\build_v105_rose_style_frozen_private_qa.ps1") `
    -ModToolsFile (Join-Path $Original "injection\tools\mod-tools.exe")
if ($LASTEXITCODE -ne 0) { throw "Rose-style local QA build failed" }
```

The new EXE at `dist/PersonalSkinManager/PersonalSkinManager.exe` intentionally does **not** include LTK, and is not tested yet.

### Explicit user-provided LTK setup

Obtain an original, official and compatible bundled pair `ltk_patcher_host.exe` + `ltk_patcher_dll.dll` from a trusted LTK Manager installation. Verify upstream release, signing identity and independent SHA-256 fingerprints. Do not use a delivered patcher DLL from a user-writable AppData cache with elevated PSM. Do not use the historical known-failed unsigned v1.28.1 pair.

The import destination is the frozen PSM's `_internal/injection/tools` directory. Start an Administrator PowerShell (because the official design expects the target install folder to be protected and PSM's runtime currently elevates). It refuses any preexisting host or DLL to avoid altering working versions.

```powershell
$PsmExe = Join-Path $New "dist\PersonalSkinManager\PersonalSkinManager.exe"
$OfficialLtkDir = "C:\REPLACE-WITH-OFFICIAL-LTK-BUNDLED-HOST-AND-DLL"
$ExpectedHost = "REPLACE_WITH_VERIFIED_64_CHAR_SHA256"
$ExpectedDll = "REPLACE_WITH_VERIFIED_64_CHAR_SHA256"
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned `
  -File (Join-Path $New "scripts\import_user_ltk_v105.ps1") `
  -SourceLtkDir $OfficialLtkDir -PsmExe $PsmExe `
  -ExpectedHostSha256 $ExpectedHost -ExpectedDllSha256 $ExpectedDll
if ($LASTEXITCODE -ne 0) { throw "Local LTK import failed" }
```

The first-run guide can open the destination folder but never installs the files automatically. A valid file checksum proves byte identity only; a signed DLL and current protocol are **not** a guarantee that a custom cosmetic will render.

### Game QA / release gate

Record the frozen executable SHA-256. Run one instance of PSM in `--dev --debug --logs`, enter Practice Tool with an authorized custom cosmetic, and run `scripts/inspect_v105_hook_failure_details.ps1` against the actual test-start timestamp. Verify WebSocket connection, skin trigger, overlay preparation, scanner, host attachment, vendor WAD verification and visible cosmetic result; no bypass of signature, skinhack or anti-cheat checks is permitted.

**Public installer remains NO-GO.** This QA build has not passed Windows tests, MSVC compilation, Practice Tool, second-match or clean-install testing. The PSM-owned inert CSLOL stub's actual build behavior requires Windows verification; separate intellectual-property and permitted-content review remains necessary. Publishing only after clear upstream license compliance and successful installed gameplay is demonstrated.
