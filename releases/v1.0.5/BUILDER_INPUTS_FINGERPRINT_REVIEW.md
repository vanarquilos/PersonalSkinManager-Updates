# PSM v1.0.5 — four-component builder input review

This supplement is additive and read-only. It does not change the private tested installer, runtime binaries, distribution builder, existing GitHub releases, or stable update manifest.

## Known baseline

- Working private source branch: `fix/v1.0.5-rose-local-rollback`; source commit reported as `b06fa4bde67bf226b371ff75f993c3434dfc8f9f`.
- Maintainer-reported installed private QA installer: 28,210,688 bytes, SHA-256 `49661E6419F1A0B0691DADBC6FC4D9F5193B997B2B55C1649200180DEF5AEF69`.
- The installed unsigned LTK candidate previously failed at `SetWindowsHookEx`; merely rebuilding identical unsigned bytes cannot resolve a reproducible runtime incompatibility.
- The LTK Patcher License and the separate CSLOL DLL License Addendum apply even to open-source redistribution. CSLOL requires a publicly trusted distributor code-signing certificate, timestamp and restrictions on prohibited content.

## Step 1 — Windows read-only inspection

From your Windows working tree that contains the additive audit branch:

```powershell
Set-Location -LiteralPath 'C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates'
python -m unittest tests.test_v105_builder_inputs_inspection_contract
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File '.\scripts\inspect_v105_builder_inputs.ps1'
```

Supply `-InstalledDir 'C:\your\actual\installation\directory'` if the installed PSM folder differs from the default.

The audit checks four runtime components — `mod-tools.exe`, `cslol-dll.dll`, `ltk_patcher_host.exe`, and `ltk_patcher_dll.dll` — using local SHA-256, size, Authenticode status and comparison across source/staging/build/installed locations. LTK-only reference/staging directories are not expected to contain the CSLOL tools. It writes no report or file and does not launch a game or patcher.

## Step 2 — Existing isolated A/B source tests

Only after source/installed file identities are documented, execute the already-existing A/B helper in separate sessions with League gameplay and PSM closed beforehand:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File '.\scripts\test_v105_isolated_ltk_source.ps1' -Variant Original
# After ending the original session and closing League gameplay:
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File '.\scripts\test_v105_isolated_ltk_source.ps1' -Variant Unsigned
```

Use only appropriately authorized custom cosmetic content to test visible rendering. An overlay build or DLL initialization is not evidence of a rendered skin.

## Result interpretation

| Original signed source | Unsigned source | Previous unsigned installed | Next diagnostic focus |
| --- | --- | --- | --- |
| Works | Fails | Fails | Unsigned runtime compatibility; packaging alone cannot fix it |
| Works | Works | Fails | Installed launch context, binary adjacency, Windows access / integrity level, and sanitized new-session log evidence |
| Works | Works | Works in a new check | Still requires legal review and clean install, Practice Tool, Swiftplay, consecutive match QA |
| Fails | Any | Any | Preserve baseline; investigate source regression first |

Do not publish original upstream-signed LTK binaries without permission, distribute CSLOL without satisfying its separate license, or disable antivirus or security controls to force a successful run. This audit is not proof of compliance or a distribution approval.
