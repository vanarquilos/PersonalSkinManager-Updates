#!/usr/bin/env python3
"""Tests for frozen PSM manifest inspection without modifying binaries."""
import unittest

from scripts.audit_v105_exe_manifest import execution_levels


MANIFEST = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security><requestedPrivileges>
      <requestedExecutionLevel level="asInvoker" uiAccess="false"/>
    </requestedPrivileges></security>
  </trustInfo>
</assembly>
"""


class V105ManifestTests(unittest.TestCase):
    def test_as_invoker_level_extracted(self):
        self.assertEqual(execution_levels(MANIFEST), ["asInvoker"])

    def test_administrator_level_is_distinguishable(self):
        manifest = MANIFEST.replace(b'level="asInvoker"', b'level="requireAdministrator"')
        self.assertEqual(execution_levels(manifest), ["requireAdministrator"])

    def test_missing_requested_level_not_mistaken_for_normal_user(self):
        manifest = MANIFEST.replace(b'<requestedExecutionLevel level="asInvoker" uiAccess="false"/>', b'')
        self.assertEqual(execution_levels(manifest), [])

    def test_invalid_manifest_rejected(self):
        with self.assertRaises(ValueError):
            execution_levels(b"not a valid XML manifest")


if __name__ == "__main__":
    unittest.main()
