"""Tests for the PushIntel use case."""

from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.application.export_intel import ExportIntel
from tw_guidance_computer.application.ports.intel_transport import IntelTransport
from tw_guidance_computer.application.push_intel import PushIntel
from tw_guidance_computer.domain.exceptions import IntelDataError, IntelTransferError


@pytest.fixture()
def mock_export():
    export = MagicMock(spec=ExportIntel)
    export.execute.return_value = "#TYPE:sectors\nid,region,explored,updated_at\n616,space,1,1000.0\n#SHA256:abc\n"
    return export


@pytest.fixture()
def mock_transport():
    return MagicMock(spec=IntelTransport)


@pytest.fixture()
def push_intel(mock_export, mock_transport):
    return PushIntel(mock_export, mock_transport, "deadbeef")


class TestPushIntel:
    def test_uploads_exported_content(self, push_intel, mock_export, mock_transport):
        push_intel.execute()
        content = mock_export.execute.return_value
        mock_transport.upload.assert_called_once_with(content, "deadbeef")

    def test_returns_line_count(self, push_intel):
        result = push_intel.execute()
        assert result == 4

    def test_export_failure_propagates(self, push_intel, mock_export):
        mock_export.execute.side_effect = IntelDataError("serialize failed")
        with pytest.raises(IntelDataError, match="serialize failed"):
            push_intel.execute()

    def test_upload_failure_propagates(self, push_intel, mock_transport):
        mock_transport.upload.side_effect = IntelTransferError("upload failed")
        with pytest.raises(IntelTransferError, match="upload failed"):
            push_intel.execute()

    def test_empty_export_returns_zero(self, push_intel, mock_export):
        mock_export.execute.return_value = ""
        result = push_intel.execute()
        assert result == 0
