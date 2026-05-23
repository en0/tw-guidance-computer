import subprocess
from unittest.mock import MagicMock

import pytest

from tw_guidance_computer.adapters.outbound.sftp_transport import (
    SftpTransport,
    _parse_ls_output,
)
from tw_guidance_computer.domain.exceptions import IntelConnectError, IntelTransferError
from tw_guidance_computer.domain.models import IntelConfig, RemoteFile


@pytest.fixture()
def config():
    return IntelConfig(host="intel.example.com", key_path="/tmp/test_key", port=2222)


@pytest.fixture()
def mock_run(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("tw_guidance_computer.adapters.outbound.sftp_transport.subprocess.run", mock)
    return mock


@pytest.fixture()
def transport(config, mock_run):
    return SftpTransport(config)


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class TestUpload:
    def test_constructs_correct_command(self, transport, mock_run):
        mock_run.return_value = _completed()
        transport.upload("data content", "remote.csv")
        args = mock_run.call_args[0][0]
        assert args[0] == "sftp"
        assert "-i" in args
        assert "/tmp/test_key" in args
        assert "-P" in args
        assert "2222" in args
        assert "intel@intel.example.com" in args

    def test_batch_contains_put_command(self, transport, mock_run):
        mock_run.return_value = _completed()
        transport.upload("data content", "remote.csv")
        args = mock_run.call_args[0][0]
        assert "-b" in args

    def test_raises_transfer_error_on_failure(self, transport, mock_run):
        mock_run.return_value = _completed(returncode=1, stderr="upload failed")
        with pytest.raises(IntelTransferError, match="upload failed"):
            transport.upload("data", "remote.csv")

    def test_raises_connect_error_on_connection_refused(self, transport, mock_run):
        mock_run.return_value = _completed(returncode=1, stderr="Connection refused")
        with pytest.raises(IntelConnectError, match="Connection refused"):
            transport.upload("data", "remote.csv")

    def test_raises_connect_error_on_permission_denied(self, transport, mock_run):
        mock_run.return_value = _completed(returncode=1, stderr="Permission denied (publickey)")
        with pytest.raises(IntelConnectError, match="Permission denied"):
            transport.upload("data", "remote.csv")

    def test_raises_connect_error_on_timeout(self, transport, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="sftp", timeout=30)
        with pytest.raises(IntelConnectError, match="timed out"):
            transport.upload("data", "remote.csv")


class TestDownload:
    def test_returns_file_content(self, transport, mock_run):
        def write_and_succeed(*args, **kwargs):
            batch_idx = args[0].index("-b")
            batch_path = args[0][batch_idx + 1]
            with open(batch_path) as f:
                batch_content = f.read()
            local_path = batch_content.strip().split()[-1]
            with open(local_path, "w") as f:
                f.write("downloaded content")
            return _completed()

        mock_run.side_effect = write_and_succeed
        result = transport.download("remote.csv")
        assert result == "downloaded content"

    def test_raises_transfer_error_on_failure(self, transport, mock_run):
        mock_run.return_value = _completed(returncode=1, stderr="No such file")
        with pytest.raises(IntelTransferError, match="No such file"):
            transport.download("missing.csv")

    def test_raises_connect_error_on_auth_failure(self, transport, mock_run):
        mock_run.return_value = _completed(returncode=1, stderr="Authentication failed")
        with pytest.raises(IntelConnectError, match="Authentication failed"):
            transport.download("remote.csv")


class TestListFiles:
    def test_parses_ls_output(self, transport, mock_run):
        ls_output = (
            "sftp> ls -l\n"
            "-rw-r--r--    1 intel    intel        1234 May 22 10:00 abc123.csv\n"
            "-rw-r--r--    1 intel    intel        5678 May 22 11:00 def456.csv\n"
        )
        mock_run.return_value = _completed(stdout=ls_output)
        result = transport.list_files()
        assert result == [
            RemoteFile(name="abc123.csv", size=1234),
            RemoteFile(name="def456.csv", size=5678),
        ]

    def test_skips_directories(self, transport, mock_run):
        ls_output = (
            "drwxr-xr-x    2 intel    intel        4096 May 22 10:00 subdir\n"
            "-rw-r--r--    1 intel    intel        1234 May 22 10:00 file.csv\n"
        )
        mock_run.return_value = _completed(stdout=ls_output)
        result = transport.list_files()
        assert len(result) == 1
        assert result[0].name == "file.csv"

    def test_returns_empty_on_no_files(self, transport, mock_run):
        mock_run.return_value = _completed(stdout="sftp> ls -l\n")
        result = transport.list_files()
        assert result == []

    def test_raises_transfer_error_on_failure(self, transport, mock_run):
        mock_run.return_value = _completed(returncode=1, stderr="network error")
        with pytest.raises(IntelTransferError, match="network error"):
            transport.list_files()


class TestParseLsOutput:
    def test_parses_standard_format(self):
        output = "-rw-r--r--    1 intel    intel        999 May 22 10:00 data.csv\n"
        result = _parse_ls_output(output)
        assert result == [RemoteFile(name="data.csv", size=999)]

    def test_skips_empty_lines(self):
        output = "\n\n-rw-r--r--    1 intel    intel        100 May 22 10:00 f.csv\n\n"
        result = _parse_ls_output(output)
        assert len(result) == 1

    def test_skips_sftp_prompt_lines(self):
        output = "sftp> ls -l\n-rw-r--r--    1 intel    intel        100 May 22 10:00 f.csv\n"
        result = _parse_ls_output(output)
        assert len(result) == 1

    def test_skips_malformed_lines(self):
        output = "not a valid line\n-rw-r--r--    1 intel    intel        100 May 22 10:00 f.csv\n"
        result = _parse_ls_output(output)
        assert len(result) == 1

    def test_skips_lines_with_non_numeric_size(self):
        output = "-rw-r--r--    1 intel    intel        abc May 22 10:00 f.csv\n"
        result = _parse_ls_output(output)
        assert result == []


class TestErrorClassification:
    def test_timed_out_stderr(self, transport, mock_run):
        mock_run.return_value = _completed(returncode=1, stderr="Connection timed out")
        with pytest.raises(IntelConnectError):
            transport.upload("data", "f.csv")

    def test_no_route_to_host(self, transport, mock_run):
        mock_run.return_value = _completed(returncode=1, stderr="No route to host")
        with pytest.raises(IntelConnectError):
            transport.upload("data", "f.csv")

    def test_generic_error_is_transfer_error(self, transport, mock_run):
        mock_run.return_value = _completed(returncode=1, stderr="something unexpected")
        with pytest.raises(IntelTransferError):
            transport.upload("data", "f.csv")

    def test_os_error_raises_transfer_error(self, transport, mock_run):
        mock_run.side_effect = OSError("sftp not found")
        with pytest.raises(IntelTransferError, match="Failed to execute sftp"):
            transport.upload("data", "f.csv")
