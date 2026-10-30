# PSM v1.0.5 — Official publication approval gate

**Status (2026-10-30): preparation only; GitHub v1.0.5 has not been published.**

## Immutable working reference

- Product: Personal Skin Manager v1.0.5
- Working source lineage: `fix/v1.0.5-rose-local-rollback`
- The combined private QA builder keeps upstream-signed original LTK v1.28.1 host/DLL, a matching `mod-tools.exe` and its `cslol-dll.dll` companions; it stages a private, separate-identity Inno installer.
- Maintainer reported the *installed combined private installer* working, with custom skins rendering, October 30, 2026.
- **Working private installer identity (maintainer-supplied read-only Windows SHA-256 output, October 30, 2026):**
  - Filename: `PersonalSkinManager_v1.0.5_Combined_PrivateQA_PSMv105Combined-20261030-192151-d6ef3007.exe`
  - Size: **28,210,688 bytes**
  - SHA-256: `49661E6419F1A0B0691DADBC6FC4D9F5193B997B2B55C1649200180DEF5AEF69`
  - SHA-256 was reported directly from the user's machine; **the installer bytes have not been provided to this repository or independently inspected here**.
  - `source_commit` reported by **two** `private-qa-manifest.json` files on the maintainer's Windows computer: `b06fa4bde67bf226b371ff75f993c3434dfc8f9f`.
  - GitHub independently confirms that commit exists on the working Rose rollback source lineage; its latest commit message is `docs(rollback): resolve only stale 11:46 Pengu warning after skins work`.
  - Both manifest records report the **same revision**; that does not establish they are distinct tested builds or prove which manifest accompanies the exact installer without checking each manifest's associated output path and installer hash. The `d6ef3007` filename suffix is **not** a Git commit SHA and must not be substituted for provenance.
- The checksum above identifies the **private test installer only**. It is not a digest for a distributable/public installer and must not be used as a release-asset verification value unless that very same file independently meets redistribution requirements.
- A working private installation is **not automatically a public-distribution license**.

## Mandatory before a public GitHub release

1. **Identify and preserve the exact tested installer.** Retain the byte-for-byte artifact and its `private-qa-manifest.json` outside the repository. Record SHA-256, size, and `source_commit`. Never rename an untested installer to claim it was tested.
2. **Third-party legal review.** `licenses/LTK-PATCHER-LICENSE.md` requires removing LeagueToolkit's official Authenticode signatures from both bundled patcher binaries for redistribution, unless explicit written permission authorizes distribution bearing those original signatures. Confirm applicable CSLOL/Pengu permissions and required notices as well. Do not publish upstream-signed LTK binaries absent permission.
3. **Produce a legally distributable candidate.** If the host/DLL must be altered to remove official signatures, construct a separate distribution artifact from reviewed, provenance-pinned copies. Keep the working private installer untouched. Do not bypass game security, tamper with a signature to defeat integrity validation, or silently reuse the prior unsigned installer that displayed default skins.
4. **Test that exact changed candidate on Windows** after clean installation:
   - League Client detected and active LCU session verified
   - Pengu client integration working (not just HTTP 200)
   - `mod-tools.exe` can start with its matching `cslol-dll.dll` and complete overlay creation
   - A selected non-default skin visibly renders inside Practice Tool
   - Swiftplay rendering, reconnect, subsequent match and normal exit/uninstall confirmed
   - No unexplained UAC, security, runtime verification or persistent troubleshooting failures
5. **Verify the artifact.** Check the installer SHA-256, byte count, source commit and bundled LTK/CSLOL DLL hashes. Inspect bundled Authenticode signature status and check for accidental private files, credentials, tokens or signing material. Ensure notices/licenses are included.
6. **Approval:** The maintainer must explicitly confirm the *distributable* installer was tested, licensed and approved for upload. No automatic "yes" flags based only on the original private test.
7. **Publish as GitHub pre-release first**, keeping v1.0.4 available as fallback. Do not update `stable/manifest.json` or replace existing signed update manifests without the authorized Ed25519 signing process.
8. **Verify the published asset digest matches** the independently audited candidate. Confirm the published release page contains correct support, compatibility, license disclosures and no secrets.

## Release fields to collect from the final Windows test

| Field | Required |
|---|---|
| Private tested filename | `PersonalSkinManager_v1.0.5_Combined_PrivateQA_PSMv105Combined-20261030-192151-d6ef3007.exe` (maintainer reported) |
| Private tested SHA-256 | `49661E6419F1A0B0691DADBC6FC4D9F5193B997B2B55C1649200180DEF5AEF69` (not independently verified here) |
| Private tested size | 28,210,688 bytes (maintainer reported) |
| Private tested source commit SHA | `b06fa4bde67bf226b371ff75f993c3434dfc8f9f` (two local manifest reports; exact manifest-to-installer association not independently inspected) |
| Final public filename | Pending, must be a separately approved asset |
| Final public SHA-256 checksum | Pending |
| Final public size in bytes | Pending |
| Final public source commit SHA | Pending |
| Host/DLL signatures or written distribution permission | Pending |
| CSLOL/Pengu license review | Pending |
| Windows version and League patch actually tested | Pending |
| League detection + WebSocket + Pengu | Pending for *distributable* candidate |
| Practice Tool / Swiftplay / second match | Pending for *distributable* candidate |
| Clean install/uninstall and security review | Pending |
| GitHub v1.0.5 published asset and matching digest | Pending |

## Read-only Windows provenance commands

Run locally with the **exact tested or prospective final installer** (adjust the path):

```powershell
$Installer = "C:\path\to\PersonalSkinManager_Setup.exe"
if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) { throw "Installer not found" }
$File = Get-Item -LiteralPath $Installer
$Hash = Get-FileHash -LiteralPath $Installer -Algorithm SHA256
"File: $($File.Name)"
"Bytes: $($File.Length)"
"SHA256: $($Hash.Hash)"
```

Inspect the installed runtime files from the corresponding **staged distribution folder**, not an unrelated working source directory:

```powershell
$Tools = "C:\path\to\staged\dist\PersonalSkinManager\_internal\injection\tools"
foreach ($Name in @("mod-tools.exe","cslol-dll.dll","ltk_patcher_host.exe","ltk_patcher_dll.dll")) {
    $Path = Join-Path $Tools $Name
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing $Name" }
    $Hash = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
    $Signature = (Get-AuthenticodeSignature -LiteralPath $Path).Status
    "$Name | $Hash | $Signature"
}
```

**Do not upload the private signed LTK installer, private QA manifest containing private paths, or game auth files.** Share only sanitized SHA-256 values and license/QA status when seeking review.

## Available GitHub release tooling

The currently connected GitHub actions can edit source and create branches/PRs, but do not expose a GitHub Release asset-upload or release-publication action. Creating this preparation branch or PR does **not** create a public GitHub v1.0.5 release. Use the GitHub Releases UI (or a separately authorized `gh release create` session) only after the above gate passes.
