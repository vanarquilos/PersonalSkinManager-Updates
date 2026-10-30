# PersonalSkinManager v1.0.5 — CSLOL public-distribution gate

**Status: NO-GO for public binary publication (2026-10-30).** Private working QA must stay intact. This is a release-licensing assessment, **not** a request to change working app features or binaries.

## Verified upstream rules

Official sources:
- [LeagueToolkit/cslol-manager — CSLOL DLL License Addendum v1.1](https://github.com/LeagueToolkit/cslol-manager/blob/master/LICENSE-CSLOL.md) (effective 2026-01-01)
- [LeagueToolkit/ltk-manager — LTK Patcher License v1.0](https://github.com/LeagueToolkit/ltk-manager/blob/main/LTK-PATCHER-LICENSE.md) (effective 2026-07-14)

The CSLOL addendum applies *specifically* to `cslol-dll.dll` even though the general CSLOL source repository uses GPL-3.0. An installer that provides this DLL to third parties counts as **distribution** (§3.4–3.5).

1. **§5.1–5.5 — required signing:** Do not redistribute the upstream-signed `cslol-dll.dll`. The distributor must re-sign the DLL with a **publicly trusted CA-issued certificate**, use a trusted timestamp, and publish the distributor certificate subject, certificate SHA-256 fingerprint (or public chain), and shipped DLL SHA-256.
2. **§6–7 — prohibited mod content:** The launcher must technically block paid-skin replication ("skinhacking") and competitive-advantage mods. Cosmetic content that substantially transforms assets may qualify under §6.3; no blanket approval for copying paid skins.
3. **§8 — do not patch, reverse engineer, or bypass controls** on the CSLOL DLL.
4. **LTK patcher §2:** If repackaging `ltk_patcher_host.exe` and `ltk_patcher_dll.dll` in PSM without specific written permission, separately staged copies must **not** retain the official LeagueToolkit Authenticode signatures; optional signatures must belong to the distributor. This condition is different from (and less restrictive than) CSLOL's compulsory publicly trusted re-signing.
5. Other dependencies including Pengu Loader, mod-tools, third-party content and license notices must independently satisfy their applicable terms.

## Specific PSM source evidence

The verified working baseline is source commit `b06fa4bde67bf226b371ff75f993c3434dfc8f9f` (Rose rollback).
`threads/handlers/injection_trigger.py` contains branches explicitly treating **unowned skins** as a downloaded Rose carrier and injecting associated mod content, including:
- `Custom mod targets unowned skin`
- `an unowned selected skin is added as the Rose-style carrier`

This does not by itself prove that every such mod violates the license; it **does** require a code/content-policy audit to establish the mandatory §6–7 block is actually effective. An unreviewed skin-unlock flow **cannot be asserted compliant**. Because the maintainer requested that the working private build not be modified, this review **does not change any skin behavior** and does not publish the present binary.

## Working private installer (do not redistribute)

- Filename: `PersonalSkinManager_v1.0.5_Combined_PrivateQA_PSMv105Combined-20261030-192151-d6ef3007.exe`
- Maintainer-reported SHA-256: `49661E6419F1A0B0691DADBC6FC4D9F5193B997B2B55C1649200180DEF5AEF69`
- Maintainer-reported file size: **28,210,688 bytes**
- Two local private QA manifests reported source commit `b06fa4bde67bf226b371ff75f993c3434dfc8f9f`
- Maintainer confirms the **installed private QA binary** renders selected custom skins; this is technical QA success, not a license grant.
- Neither the original installer bytes nor an independent cryptographic link between a specific private manifest and installer was supplied for our inspection.

## Release paths

### A. No public binary release (preserve all features)
Keep the signed private QA build, its complete toolset and current v1.0.4 GitHub releases unchanged. Do not upload the combined private installer, packaged runtime folder, or a binary-download URL.

### B. Prepare a compliant public binary (requires further work)
Prior to distributing any bundled CSLOL DLL, obtain a valid **publicly trusted distributor code-signing certificate** and signing/timestamp pipeline; audit and enforce prohibited-content blocks under §§6–7; prepare an independently staged distro with appropriate LTK signature handling, signed CSLOL DLL, full attribution and exact file hashes; test that **new installed artifact** in Practice Tool, Swiftplay and subsequent matches. A previously tried unsigned LTK pair failed in-game, so no assumption of functionality is warranted.

### C. Explore an authorized exception or alternative dependency
Request specific permissions or a different redistribution arrangement from the upstream rightsholder(s), or design a legitimate toolchain that **does not redistribute or invoke a restricted CSLOL dependency** while respecting all other relevant rights. Do **not** assume a downloader/self-install trick automatically avoids the addendum's launcher-level obligations.

**Not sufficient:** labeling the product open source, adding a disclaimer, copying a DLL alone, removing LTK signatures alone, signing only the outer installer, or borrowing LeagueToolkit's certificate. The CSLOL DLL addendum imposes separate substantive requirements.

## Decision record

- User selected **no email/contact** route on 2026-10-30.
- Accordingly, no rights-holder exception has been granted.
- Official release preparation can continue with license/compliance documentation and read-only inspection, but **do not build/publish a supposedly compliant public v1.0.5 installer until the CSLOL gates are met**.
- Keep draft PR #16 and the stable update manifest unchanged pending approval.
