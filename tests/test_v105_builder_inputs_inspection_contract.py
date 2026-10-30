"""Static safety checks for the read-only v1.0.5 four-component audit."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "inspect_v105_builder_inputs.ps1"


class BuilderInspectionContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_powershell_51_ascii(self):
        self.assertTrue(SCRIPT.read_bytes().isascii())

    def test_all_four_components_covered(self):
        for filename in (
            "mod-tools.exe", "cslol-dll.dll", "ltk_patcher_host.exe", "ltk_patcher_dll.dll"
        ):
            self.assertIn(filename, self.text)

    def test_all_runtime_locations_covered(self):
        for label in (
            "source-active", "ltk-official-reference", "ltk-unsigned-stage",
            "frozen-build", "installed-package"
        ):
            self.assertIn(label, self.text)

    def test_no_mutating_or_publishing_commands(self):
        forbidden = (
            "Remove-Item", "Copy-Item", "Move-Item", "Set-Content", "Add-Content",
            "Out-File", "Start-Process", "Invoke-WebRequest", "gh release create",
            "Set-AuthenticodeSignature", "signtool remove", "git reset", "git switch",
        )
        for command in forbidden:
            with self.subTest(command=command):
                self.assertNotIn(command, self.text)

    def test_known_failing_ltk_pair_flagged(self):
        self.assertIn("5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9", self.text)
        self.assertIn("B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29", self.text)
        self.assertIn("KNOWN FAILURE", self.text)

    def test_no_false_compliance_or_skin_render_claim(self):
        self.assertIn("cannot prove skin rendering", self.text)
        self.assertIn("content-policy compliance", self.text)


if __name__ == "__main__":
    unittest.main()
