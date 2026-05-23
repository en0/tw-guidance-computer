"""Tests for the SyncIntelWorker background service."""

from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.application.pull_intel import PullIntel
from tw_guidance_computer.application.push_intel import PushIntel
from tw_guidance_computer.application.sync_intel_worker import SyncIntelWorker
from tw_guidance_computer.domain.exceptions import (
    IntelConnectError,
    IntelDataError,
    IntelKeyError,
    IntelTransferError,
)
from tw_guidance_computer.domain.models import IntelConfig, IntelMergeResult


@pytest.fixture(autouse=True)
def _fast_sleep(monkeypatch):
    """Make interruptible_sleep return immediately."""
    counter = [0.0]

    def fake_monotonic():
        counter[0] += 100.0
        return counter[0]

    monkeypatch.setattr("tw_guidance_computer.application.sync_intel_worker.time.monotonic", fake_monotonic)
    monkeypatch.setattr("tw_guidance_computer.application.sync_intel_worker.time.sleep", lambda _: None)


@pytest.fixture()
def config():
    return IntelConfig(host="intel.example.com", key_path="/tmp/key", sync_interval=2, sync_budget=1)


@pytest.fixture()
def mock_push():
    push = MagicMock(spec=PushIntel)
    push.execute.return_value = 10
    return push


@pytest.fixture()
def mock_pull():
    pull = MagicMock(spec=PullIntel)
    pull.execute.return_value = IntelMergeResult()
    return pull


@pytest.fixture()
def worker(mock_push, mock_pull, config):
    return SyncIntelWorker(mock_push, mock_pull, config)


class TestStartupPull:
    def test_pulls_on_startup(self, worker, mock_pull):
        mock_pull.execute.side_effect = lambda **kwargs: _stop(worker)
        worker.run()
        mock_pull.execute.assert_called()

    def test_startup_pull_uses_budget_and_offset_zero(self, worker, mock_pull):
        mock_pull.execute.side_effect = lambda **kwargs: _stop(worker)
        worker.run()
        mock_pull.execute.assert_called_with(budget_seconds=1.0, offset=0)


class TestSyncLoop:
    def test_push_then_pull_on_cycle(self, worker, mock_push, mock_pull):
        call_count = [0]

        def pull_side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] >= 2:
                worker.request_stop()
            return IntelMergeResult()

        mock_pull.execute.side_effect = pull_side_effect
        worker.run()
        # After startup pull, one cycle: push + pull
        assert mock_push.execute.call_count == 1
        assert mock_pull.execute.call_count == 2

    def test_sync_counter_increments(self, worker, mock_push, mock_pull):
        call_count = [0]
        offsets = []

        def track_pull(**kwargs):
            offsets.append(kwargs.get("offset"))
            call_count[0] += 1
            if call_count[0] >= 3:
                worker.request_stop()
            return IntelMergeResult()

        mock_pull.execute.side_effect = track_pull
        worker.run()
        # Startup pull offset=0, first cycle offset=0 (counter increments after), second cycle offset=1
        assert offsets == [0, 0, 1]

    def test_clears_error_on_success(self, worker, mock_push, mock_pull):
        call_count = [0]

        def fail_then_succeed(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise IntelConnectError("connection refused")
            worker.request_stop()
            return IntelMergeResult()

        mock_pull.execute.side_effect = fail_then_succeed
        worker.run()
        assert worker.get_status().last_error is None


class TestShutdown:
    def test_shutdown_does_final_push(self, worker, mock_push, mock_pull):
        mock_pull.execute.side_effect = lambda **kwargs: _shutdown(worker)
        worker.run()
        mock_push.execute.assert_called_once()

    def test_shutdown_status_done(self, worker, mock_push, mock_pull):
        mock_pull.execute.side_effect = lambda **kwargs: _shutdown(worker)
        worker.run()
        assert worker.get_status().shutdown_status == "Done."

    def test_shutdown_push_failure_reports_status(self, worker, mock_push, mock_pull):
        mock_pull.execute.side_effect = lambda **kwargs: _shutdown(worker)
        mock_push.execute.side_effect = IntelTransferError("upload timeout")
        worker.run()
        status = worker.get_status()
        assert status.shutdown_status is not None
        assert "Push failed:" in status.shutdown_status

    def test_shutdown_sets_exporting_status(self, worker, mock_push, mock_pull):
        statuses = []

        def capture_status_on_push():
            statuses.append(worker.get_status().shutdown_status)
            return 10

        mock_pull.execute.side_effect = lambda **kwargs: _shutdown(worker)
        mock_push.execute.side_effect = capture_status_on_push
        worker.run()
        assert "Exporting sectors..." in statuses


class TestStop:
    def test_stop_exits_immediately(self, worker, mock_push, mock_pull):
        mock_pull.execute.side_effect = lambda **kwargs: _stop(worker)
        worker.run()
        mock_push.execute.assert_not_called()

    def test_stop_during_shutdown_skips_push(self, worker, mock_push, mock_pull):
        def shutdown_then_stop(**kwargs):
            worker.request_shutdown()
            worker.request_stop()
            return IntelMergeResult()

        mock_pull.execute.side_effect = shutdown_then_stop
        worker.run()
        mock_push.execute.assert_not_called()


class TestErrorCodeMapping:
    def test_connect_error_sets_e24(self, worker, mock_pull):
        def fail_and_stop(**kwargs):
            worker.request_stop()
            raise IntelConnectError("connection refused")

        mock_pull.execute.side_effect = fail_and_stop
        worker.run()
        assert worker.get_status().last_error == "E24"

    def test_auth_error_sets_e31(self, worker, mock_pull):
        def fail_and_stop(**kwargs):
            worker.request_stop()
            raise IntelConnectError("permission denied")

        mock_pull.execute.side_effect = fail_and_stop
        worker.run()
        assert worker.get_status().last_error == "E31"

    def test_auth_error_detected_by_auth_keyword(self, worker, mock_pull):
        def fail_and_stop(**kwargs):
            worker.request_stop()
            raise IntelConnectError("authentication failed")

        mock_pull.execute.side_effect = fail_and_stop
        worker.run()
        assert worker.get_status().last_error == "E31"

    def test_transfer_error_during_push_sets_e38(self, worker, mock_push, mock_pull):
        call_count = [0]

        def pull_side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return IntelMergeResult()
            # After push fails, stop on next pull
            worker.request_stop()
            return IntelMergeResult()

        mock_pull.execute.side_effect = pull_side_effect

        def push_fail_and_stop():
            worker.request_stop()
            raise IntelTransferError("upload failed")

        mock_push.execute.side_effect = push_fail_and_stop
        worker.run()
        assert worker.get_status().last_error == "E38"

    def test_transfer_error_during_pull_sets_e45(self, worker, mock_pull):
        def fail_and_stop(**kwargs):
            worker.request_stop()
            raise IntelTransferError("download failed")

        mock_pull.execute.side_effect = fail_and_stop
        worker.run()
        assert worker.get_status().last_error == "E45"

    def test_data_error_during_push_sets_e17(self, worker, mock_push, mock_pull):
        call_count = [0]

        def pull_side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return IntelMergeResult()
            worker.request_stop()
            return IntelMergeResult()

        mock_pull.execute.side_effect = pull_side_effect

        def push_fail_and_stop():
            worker.request_stop()
            raise IntelDataError("serialize failed")

        mock_push.execute.side_effect = push_fail_and_stop
        worker.run()
        assert worker.get_status().last_error == "E17"

    def test_data_error_during_pull_sets_e52(self, worker, mock_pull):
        def fail_and_stop(**kwargs):
            worker.request_stop()
            raise IntelDataError("corrupt data")

        mock_pull.execute.side_effect = fail_and_stop
        worker.run()
        assert worker.get_status().last_error == "E52"

    def test_key_error_sets_e66(self, worker, mock_pull):
        def fail_and_stop(**kwargs):
            worker.request_stop()
            raise IntelKeyError("key not found")

        mock_pull.execute.side_effect = fail_and_stop
        worker.run()
        assert worker.get_status().last_error == "E66"


class TestGetStatus:
    def test_initial_status_has_no_error(self, worker):
        status = worker.get_status()
        assert status.last_error is None
        assert status.shutdown_status is None


def _stop(worker: SyncIntelWorker) -> IntelMergeResult:
    worker.request_stop()
    return IntelMergeResult()


def _shutdown(worker: SyncIntelWorker) -> IntelMergeResult:
    worker.request_shutdown()
    return IntelMergeResult()
