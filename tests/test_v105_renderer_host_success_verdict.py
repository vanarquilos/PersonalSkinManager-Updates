"""The LTK host adapter must never report an unrendered skin as applied.

No patcher executable, game instance or third-party DLL is run by these tests.
"""
import time
from types import SimpleNamespace
from unittest import TestCase, mock

from injection.overlay.ltk_host import (
    LtkHostResult,
    _skin_application_evidence_observed,
    run_ltk_patcher_host_session,
)


class RendererEvidenceTests(TestCase):
    def make_session(self, *, attached=False, initialized=False,
                     redirects=0, stopped=False):
        result = LtkHostResult()
        result.attached = attached
        result.overlay_initialized = initialized
        result.redirected_wads = redirects
        result.failure = None
        proc = mock.Mock()
        proc.poll.return_value = 0
        proc.returncode = 0
        manager = SimpleNamespace(stopped_by_user=stopped,
                                  current_overlay_process=None)
        session = SimpleNamespace(
            proc=proc, result=result, events=mock.Mock(),
            process_manager=manager, started_at=time.time(),
        )
        return session

    def test_success_requires_all_three_observations(self):
        session = self.make_session(attached=True, initialized=True, redirects=1)
        self.assertTrue(_skin_application_evidence_observed(session.result))
        for attached, initialized, redirects in (
            (False, True, 1), (True, False, 1), (True, True, 0),
            (False, False, 0),
        ):
            candidate = self.make_session(
                attached=attached, initialized=initialized,
                redirects=redirects
            )
            self.assertFalse(_skin_application_evidence_observed(candidate.result))

    def test_failure_always_overrides_potential_evidence(self):
        session = self.make_session(attached=True, initialized=True, redirects=1)
        session.result.failure = "upstream refused overlay"
        self.assertFalse(_skin_application_evidence_observed(session.result))

    @mock.patch("injection.overlay.ltk_host.report_issue")
    @mock.patch("injection.overlay.ltk_host._shutdown_host")
    @mock.patch("injection.overlay.ltk_host._drain_events")
    def test_clean_exit_without_attachment_is_not_skin_success(
        self, drain, shutdown, issue
    ):
        session = self.make_session()
        self.assertEqual(run_ltk_patcher_host_session(session), 3)
        self.assertEqual(issue.call_args.args[0], "LTK_NO_WAD_REDIRECTION")

    @mock.patch("injection.overlay.ltk_host._shutdown_host")
    @mock.patch("injection.overlay.ltk_host._drain_events")
    def test_complete_evidence_allows_success(self, drain, shutdown):
        session = self.make_session(attached=True, initialized=True, redirects=1)
        self.assertEqual(run_ltk_patcher_host_session(session), 0)

    @mock.patch("injection.overlay.ltk_host._shutdown_host")
    @mock.patch("injection.overlay.ltk_host._drain_events")
    def test_manual_stop_without_redirection_is_not_success(self, drain, shutdown):
        session = self.make_session(stopped=True)
        self.assertEqual(run_ltk_patcher_host_session(session), 3)
