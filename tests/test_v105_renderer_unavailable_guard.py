"""Refusal of an unavailable renderer must not mutate skins or hold League.

Runs offline. Does not load LTK/League code or attempt skin rendering.
"""
from unittest import TestCase, mock

from injection.core.injector import SkinInjector


class UnavailableRendererGuardTests(TestCase):
    def make_injector(self):
        injector = SkinInjector.__new__(SkinInjector)
        injector.runtime_ready = False
        injector._resolve_zip = mock.Mock(
            side_effect=AssertionError("ZIP selection must not start")
        )
        injector._clean_mods_dir = mock.Mock(
            side_effect=AssertionError("Mods must not be deleted")
        )
        injector._clean_overlay_dir = mock.Mock(
            side_effect=AssertionError("Overlay must not be deleted")
        )
        injector._extract_zip_to_mod = mock.Mock(
            side_effect=AssertionError("ZIP must not be extracted")
        )
        injector._mk_run_overlay = mock.Mock(
            side_effect=AssertionError("Renderer must not run")
        )
        return injector

    @mock.patch("injection.core.injector.report_issue")
    def test_renderer_refusal_is_non_destructive_and_resumes_game(self, report):
        injector = self.make_injector()
        manager = mock.Mock()
        result = injector.inject_skin(
            "Example Skin", injection_manager=manager,
        )
        self.assertFalse(result)
        manager.resume_if_suspended.assert_called_once_with()
        injector._resolve_zip.assert_not_called()
        injector._clean_mods_dir.assert_not_called()
        injector._clean_overlay_dir.assert_not_called()
        injector._extract_zip_to_mod.assert_not_called()
        injector._mk_run_overlay.assert_not_called()
        self.assertEqual(report.call_args.args[0], "INJECTION_RUNTIME_UNAVAILABLE")
        self.assertIn("renderer is unavailable", report.call_args.args[2])

    @mock.patch("injection.core.injector.report_issue")
    def test_missing_readiness_flag_refuses_closed(self, report):
        injector = self.make_injector()
        del injector.runtime_ready
        self.assertFalse(injector.inject_skin("Example Skin"))
        injector._resolve_zip.assert_not_called()
        self.assertEqual(report.call_args.args[0], "INJECTION_RUNTIME_UNAVAILABLE")

    @mock.patch("injection.core.injector.report_issue")
    @mock.patch("injection.core.injector.log")
    def test_failed_game_resume_is_reported_without_starting_renderer(self, log, report):
        injector = self.make_injector()
        manager = mock.Mock()
        manager.resume_if_suspended.side_effect = RuntimeError("test error")
        self.assertFalse(
            injector.inject_skin("Example Skin", injection_manager=manager)
        )
        manager.resume_if_suspended.assert_called_once_with()
        log.exception.assert_called_once()
        injector._mk_run_overlay.assert_not_called()
        self.assertEqual(report.call_args.args[0], "INJECTION_RUNTIME_UNAVAILABLE")
