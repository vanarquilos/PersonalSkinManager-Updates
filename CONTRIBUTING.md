# Contributing to Personal Skin Manager

Thanks for contributing to Personal Skin Manager (PSM).

PSM is a compatibility-first Windows project derived from Rose. Contributions should preserve working behavior unless a change is required for correctness, security, provenance, maintainability, or an explicitly accepted feature.

## Development baseline

Use the current `main` branch in this public repository as your starting point.

Recommended branch names:

```text
feature/<short-description>
fix/<short-description>
docs/<short-description>
chore/<short-description>
```

Keep changes focused. Avoid combining unrelated refactors, formatting churn, and behavior changes in one pull request.

## Before submitting

For code changes:

1. install dependencies from `requirements.txt`
2. run the most relevant targeted checks/tests for the area changed
3. build with `python .\scripts\build_pyinstaller.py` when the change affects packaged application behavior
4. verify that no generated build output, local configuration, logs, signing material, or local-only binaries were added
5. describe what changed, why it changed, and how it was verified

Do not claim a check passed unless you actually ran it.

Every pull request also runs lightweight public-source checks for Python compilation, tracked-secret/local-file hygiene, generated-output boundaries, and stable-manifest structure. These automated checks do not replace Windows/runtime QA when the behavior being changed requires it.

## Project boundaries

Pull requests must not add or improve:

- anti-cheat bypass/evasion
- stealth, process concealment, or detection-avoidance behavior
- driver tricks or security-control disabling
- tampering with third-party security/enforcement controls
- distribution of private signing material
- distribution of `cslol-dll.dll`

Do not add Riot Games assets, paid cosmetic content, credentials, tokens, private keys, personal logs, or user-specific cache data to the repository.

## Third-party dependencies and binaries

Any new third-party source or binary must have:

- a clear upstream origin
- a compatible redistribution/license basis
- version/provenance information where practical
- an update to `THIRD_PARTY_NOTICES.md` when appropriate

The root PSM MIT license does not automatically relicense third-party components.

In particular, `cslol-dll.dll` is governed by the League Toolkit CSLOL DLL License Addendum and is not distributed by PSM.

## Compatibility-first rule

Prefer the smallest safe patch.

Avoid broad rewrites of the League/LCU integration, game monitor, content synchronization, mod tooling, updater, or installer when a narrowly scoped correction is sufficient.

Compatibility fixes should not weaken integrity checks or package/signature verification.

## Stable update channel

`stable/manifest.json` is compatibility-critical for supported installed clients.

Do not modify the stable manifest as part of unrelated work. Any intentional release/update-channel change must preserve signing-key secrecy, package verification, published release provenance, and backward-compatible URLs where required.

Do not rewrite an already-published release tag merely to reorganize source history.

## Documentation

Documentation changes should reflect the actual code and release state. Do not document a feature, compatibility claim, build result, or release status that has not been verified.

## Pull request checklist

- [ ] change is narrowly scoped
- [ ] no secrets or private signing material
- [ ] no local-only `cslol-dll.dll`
- [ ] no generated build/cache/log output
- [ ] stable manifest unchanged unless intentionally part of reviewed release work
- [ ] existing release/tag provenance preserved
- [ ] third-party licensing/provenance reviewed if applicable
- [ ] relevant checks/tests run
- [ ] Windows/runtime QA performed when required
- [ ] user-visible behavior documented when needed
- [ ] `THIRD_PARTY_NOTICES.md` updated when needed

## License

By contributing code to this repository, you agree that your contribution may be distributed under the applicable project license(s), subject to any preserved third-party license terms.
