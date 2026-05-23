"""Tests for the PullIntel use case."""

from unittest.mock import MagicMock, patch

import pytest

from tw_guidance_computer.application.import_intel import ImportIntel
from tw_guidance_computer.application.ports.intel_transport import IntelTransport
from tw_guidance_computer.application.pull_intel import PullIntel
from tw_guidance_computer.domain.exceptions import IntelDataError
from tw_guidance_computer.domain.models import IntelMergeResult, RemoteFile


@pytest.fixture()
def mock_import():
    imp = MagicMock(spec=ImportIntel)
    imp.execute.return_value = IntelMergeResult(sectors_added=1, warps_added=2)
    return imp


@pytest.fixture()
def mock_transport():
    transport = MagicMock(spec=IntelTransport)
    transport.list_files.return_value = [
        RemoteFile(name="aaa111", size=500),
        RemoteFile(name="bbb222", size=600),
    ]
    transport.download.return_value = "csv content"
    return transport


@pytest.fixture()
def pull_intel(mock_import, mock_transport):
    return PullIntel(mock_import, mock_transport, "myident", max_file_size=10000)


class TestPullIntel:
    def test_excludes_own_identity(self, mock_import, mock_transport):
        mock_transport.list_files.return_value = [
            RemoteFile(name="myident", size=100),
            RemoteFile(name="other", size=200),
        ]
        pull = PullIntel(mock_import, mock_transport, "myident", max_file_size=10000)
        pull.execute()
        mock_transport.download.assert_called_once_with("other")

    def test_downloads_and_imports_all_files(self, pull_intel, mock_transport, mock_import):
        pull_intel.execute()
        assert mock_transport.download.call_count == 2
        assert mock_import.execute.call_count == 2

    def test_aggregates_results(self, pull_intel, mock_import):
        mock_import.execute.side_effect = [
            IntelMergeResult(sectors_added=2, ports_added=1),
            IntelMergeResult(sectors_added=3, warps_added=4),
        ]
        result = pull_intel.execute()
        assert result.sectors_added == 5
        assert result.ports_added == 1
        assert result.warps_added == 4

    def test_skips_corrupt_file_continues(self, pull_intel, mock_import, mock_transport):
        mock_import.execute.side_effect = [
            IntelDataError("corrupt"),
            IntelMergeResult(sectors_added=5),
        ]
        result = pull_intel.execute()
        assert result.sectors_added == 5
        assert mock_transport.download.call_count == 2

    def test_skips_oversized_files(self, mock_import, mock_transport):
        mock_transport.list_files.return_value = [
            RemoteFile(name="big", size=99999),
            RemoteFile(name="small", size=100),
        ]
        pull = PullIntel(mock_import, mock_transport, "myident", max_file_size=1000)
        pull.execute()
        mock_transport.download.assert_called_once_with("small")

    def test_budget_stops_processing(self, pull_intel, mock_transport, mock_import):
        mock_transport.list_files.return_value = [
            RemoteFile(name="a", size=10),
            RemoteFile(name="b", size=10),
            RemoteFile(name="c", size=10),
        ]
        times = [100.0, 100.0, 105.0]
        with patch("tw_guidance_computer.application.pull_intel.time.monotonic", side_effect=times):
            _ = pull_intel.execute(budget_seconds=3.0)
        assert mock_transport.download.call_count == 1

    def test_no_budget_processes_all(self, pull_intel):
        result = pull_intel.execute(budget_seconds=None)
        assert result.sectors_added == 2
        assert result.warps_added == 4

    def test_offset_rotates_file_order(self, mock_import, mock_transport):
        mock_transport.list_files.return_value = [
            RemoteFile(name="a", size=10),
            RemoteFile(name="b", size=10),
            RemoteFile(name="c", size=10),
        ]
        mock_import.execute.return_value = IntelMergeResult()
        pull = PullIntel(mock_import, mock_transport, "myident", max_file_size=10000)
        pull.execute(offset=1)
        calls = [c[0][0] for c in mock_transport.download.call_args_list]
        assert calls == ["b", "c", "a"]

    def test_offset_wraps_around(self, mock_import, mock_transport):
        mock_transport.list_files.return_value = [
            RemoteFile(name="a", size=10),
            RemoteFile(name="b", size=10),
        ]
        mock_import.execute.return_value = IntelMergeResult()
        pull = PullIntel(mock_import, mock_transport, "myident", max_file_size=10000)
        pull.execute(offset=5)
        calls = [c[0][0] for c in mock_transport.download.call_args_list]
        assert calls == ["b", "a"]

    def test_empty_file_list_returns_zero(self, mock_import, mock_transport):
        mock_transport.list_files.return_value = []
        pull = PullIntel(mock_import, mock_transport, "myident", max_file_size=10000)
        result = pull.execute()
        assert result.total == 0
        mock_transport.download.assert_not_called()

    def test_all_files_are_own_identity(self, mock_import, mock_transport):
        mock_transport.list_files.return_value = [
            RemoteFile(name="myident", size=100),
        ]
        pull = PullIntel(mock_import, mock_transport, "myident", max_file_size=10000)
        result = pull.execute()
        assert result.total == 0

    def test_ports_updated_aggregated(self, pull_intel, mock_import):
        mock_import.execute.side_effect = [
            IntelMergeResult(ports_updated=3),
            IntelMergeResult(ports_updated=2),
        ]
        result = pull_intel.execute()
        assert result.ports_updated == 5
