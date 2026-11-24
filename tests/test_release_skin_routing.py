#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Release invariants for supported skin/mod routing."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TRIGGER = ROOT / "threads/handlers/injection_trigger.py"


class ReleaseSkinRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = TRIGGER.read_text(encoding="utf-8")

    def test_owned_riot_skins_use_native_lcu_without_overlay(self):
        start = self.source.index("# Native client selection needs no overlay")
        end = self.source.index("# Owning a base cosmetic", start)
        route = self.source[start:end]
        self.assertIn("native_target_id in (owned_skin_ids or set())", route)
        self.assertIn("not is_default_skin(native_target_id)", route)
        self.assertIn("self._force_owned_skin(native_target_id)", route)
        self.assertIn("discard_early_patcher()", route)
        self.assertNotIn("inject_skin_immediately", route)
        self.assertIn("Visual rendering not verified", route)

    def test_native_selection_requires_matching_local_player_confirmation(self):
        import ast
        from types import SimpleNamespace
        from unittest.mock import Mock

        tree = ast.parse(self.source)
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                  and n.name == "_force_owned_skin")
        scope = {"log": Mock(), "time": SimpleNamespace(sleep=lambda _: None),
                 "BASE_SKIN_VERIFICATION_WAIT_S": 0}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(TRIGGER), "exec"), scope)
        apply = scope["_force_owned_skin"]
        from unittest.mock import PropertyMock
        for final_skin, owned, expected, writes in (
            (266001, {266001}, True, 1),
            (266000, {266001}, False, 1),
            (266001, set(), False, 0),
        ):
            with self.subTest(final_skin=final_skin, owned=owned):
                lcu = Mock()
                def snapshot(skin):
                    return {"localPlayerCellId": 0, "myTeam": [
                        {"cellId": 0, "championId": 266, "selectedSkinId": skin}
                    ]}
                type(lcu).session = PropertyMock(side_effect=[
                    snapshot(266000), snapshot(final_skin)])
                lcu.set_my_selection_skin.return_value = True
                injector = SimpleNamespace(
                    state=SimpleNamespace(owned_skin_ids=owned,
                        locked_champ_id=266, hovered_champ_id=266, local_cell_id=0),
                    lcu=lcu, injection_manager=None,
                    _skin_matches_champion=lambda s, c: s // 1000 == c,
                )
                self.assertEqual(apply(injector, 266001), expected)
                self.assertEqual(lcu.set_my_selection_skin.call_count, writes)

    def test_owned_base_does_not_imply_chroma_ownership(self):
        start = self.source.index("# Owning a base cosmetic")
        end = self.source.index("# Inject if user doesn't own", start)
        route = self.source[start:end]
        self.assertIn("Chroma ownership not confirmed", route)
        self.assertNotIn("_force_owned_skin(", route)
        self.assertNotIn("inject_skin_immediately", route)

    def test_unowned_official_skin_routes_through_overlay_runtime(self):
        self.assertIn(
            "Inject if user doesn't own the hovered skin",
            self.source,
        )
        self.assertIn("inject_skin_immediately(", self.source)
        self.assertNotIn(
            "Selected unowned League skin cannot be applied with the current supported runtime.",
            self.source,
        )

    def test_unowned_riot_skin_can_be_used_as_custom_mod_carrier(self):
        self.assertIn("injecting carrier %s + custom mod", self.source)
        self.assertIn("base_skin_name=carrier_name", self.source)
        self.assertNotIn("carrier overlay was not started", self.source)

    def test_category_mods_keep_unowned_skin_carrier(self):
        self.assertIn("base_skin_name_for_injection = name", self.source)
        self.assertIn(
            "injecting skin carrier +",
            self.source,
        )

    def test_runtime_uses_upstream_content_enforcement_flags(self):
        ltk_source = (
            ROOT / "injection/overlay/ltk_host.py"
        ).read_text(encoding="utf-8")
        self.assertIn("LTK_PATCHER_FLAGS = 0", ltk_source)
        self.assertIn("LTK_PATCHER_LOG_LEVEL = 0x10", ltk_source)


if __name__ == "__main__":
    unittest.main()
