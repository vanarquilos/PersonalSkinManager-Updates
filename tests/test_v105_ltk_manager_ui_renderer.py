"""Offline contract tests for LTK Manager's user-visible UI renderer adapter.

Unit tests do not launch a game, run a patcher, or alter LTK Manager.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
import json

from injection.overlay.ltk_manager_ui_renderer import (
    LibraryProfile,
    LtkManagerUIRenderer,
    ManagerUIError,
    installed_manager,
    read_library,
    resolve_skin_profile,
)


class ManagerUIRendererUnitTests(TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.index = self.root / "library.json"
        self.mapping = self.root / "mapping.json"
        self.manager = self.root / "LTK Manager" / "ltk-manager.exe"
        self.manager.parent.mkdir(parents=True)
        self.manager.write_bytes(b"fixture")
        self.index.write_text(json.dumps({
            "version": 2,
            "mods": [],
            "profiles": [
                {"id": "default", "name": "Default", "enabledMods": []},
                {"id": "skin1", "name": "PSM skin_266001",
                 "enabledMods": ["mod-123"]},
            ],
            "activeProfileId": "default",
        }), encoding="utf-8")
        self.mapping.write_text(json.dumps({
            "skin_266001": "PSM skin_266001"
        }), encoding="utf-8")

    def test_installed_exe_detection(self):
        self.assertEqual(
            installed_manager({"ProgramFiles": str(self.root)}),
            self.manager.resolve(),
        )

    def test_profile_library_parsed_read_only(self):
        before = self.index.read_bytes()
        profiles, active = read_library(self.index)
        self.assertEqual(active, "default")
        self.assertEqual(profiles[1].enabled_mods, ("mod-123",))
        self.assertEqual(self.index.read_bytes(), before)

    def test_skin_maps_to_explicit_profile(self):
        self.assertEqual(resolve_skin_profile("skin_266001", self.mapping),
                         "PSM skin_266001")

    def test_unmapped_skin_refuses_without_fallback(self):
        with self.assertRaisesRegex(ManagerUIError, "No LTK profile mapped"):
            resolve_skin_profile("skin_266002", self.mapping)

    def test_invalid_schema_refuses(self):
        self.index.write_text('{"version": 3}', encoding="utf-8")
        with self.assertRaisesRegex(ManagerUIError, "schema"):
            read_library(self.index)

    def test_empty_profile_cannot_render(self):
        renderer = LtkManagerUIRenderer(self.manager, self.index)
        with self.assertRaisesRegex(ManagerUIError, "no enabled mods"):
            renderer.check_profile("Default")

    def test_requires_explicit_consent_before_window_access(self):
        renderer = LtkManagerUIRenderer(self.manager, self.index)
        with mock.patch.object(renderer, "_window") as window:
            with self.assertRaisesRegex(ManagerUIError, "consent"):
                renderer.activate("PSM skin_266001")
            window.assert_not_called()

    def test_wrong_manager_executable_refuses(self):
        impostor = self.root / "wrong.exe"
        impostor.write_bytes(b"fixture")
        with self.assertRaisesRegex(ManagerUIError, "unexpected"):
            LtkManagerUIRenderer(impostor, self.index)

    def test_no_bypass_or_private_ipc(self):
        path = Path(__file__).resolve().parents[1] / (
            "injection/overlay/ltk_manager_ui_renderer.py")
        code = path.read_text(encoding="utf-8")
        for dangerous in (
            "SetWindowsHookEx", "CreateRemoteThread",
            "PROC_THREAD_ATTRIBUTE_PARENT_PROCESS",
            "plugin:patcher|start_patcher",
            "LeagueToolFlop.dll", "ltk_patcher_dll.dll",
        ):
            self.assertNotIn(dangerous, code)
