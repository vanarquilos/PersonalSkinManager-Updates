## Summary

Describe the change and why it is needed.

## Scope

- What area of PSM does this affect?
- Is this a code, documentation, compatibility, build, installer, updater, or diagnostics change?

## Verification

List the checks you actually ran. Do not claim checks that were not executed.

```text
<commands / QA performed>
```

## Compatibility / integrity checklist

- [ ] Change is narrowly scoped and avoids unrelated refactors.
- [ ] No `cslol-dll.dll` or other local-only QA binary was added.
- [ ] No private signing key, password, token, local config, cache, or log was added.
- [ ] No generated `build/`, `dist/`, installer working output, or temporary file was added.
- [ ] `stable/manifest.json` was not changed unless this PR intentionally performs reviewed release/update-channel work.
- [ ] Existing release/tag provenance was not rewritten.
- [ ] Third-party licensing/provenance was reviewed if dependencies or binaries changed.
- [ ] Relevant source checks/tests were run.
- [ ] Windows/runtime QA was performed when behavior requires it.

## Security boundary

This project does not accept changes intended to add or improve anti-cheat bypass/evasion, stealth, process concealment, driver-based circumvention, security-control disabling, or tampering with third-party enforcement controls.
