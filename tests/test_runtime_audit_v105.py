#!/usr/bin/env python3
"""Release guard against repackaging the runtime from the failed 26.21 test."""
import unittest

from scripts.audit_runtime_v105 import was_in_failed_v105_test


class RuntimeAuditV105Tests(unittest.TestCase):
    def test_known_failed_host_and_dll_pair_is_refused(self):
        files = {
            "ltk_patcher_host.exe": {"sha256": "A7C4047CE7548C7AE820BC440735F15B9D1A495ACF061DBB5A5A2893A0ED8D7C"},
            "ltk_patcher_dll.dll": {"sha256": "07A43BF36A389EB00F6276E333BD7F2B95218F25A58E1E128FF4D2E4AB2DC99B"},
        }
        self.assertTrue(was_in_failed_v105_test(files))

    def test_altered_pair_is_not_automatically_declared_failed(self):
        files = {
            "ltk_patcher_host.exe": {"sha256": "1" * 64},
            "ltk_patcher_dll.dll": {"sha256": "2" * 64},
        }
        self.assertFalse(was_in_failed_v105_test(files))

    def test_missing_pair_is_not_misidentified(self):
        self.assertFalse(was_in_failed_v105_test({}))


if __name__ == "__main__":
    unittest.main()
