import pytest

from tw_guidance_computer.domain.exceptions import ValidationError
from tw_guidance_computer.domain.models import IntelConfig, IntelMergeResult, RemoteFile, SyncStatus


class TestIntelConfig:
    def test_construction_defaults(self):
        cfg = IntelConfig(host="intel.example.com", key_path="/home/user/.ssh/id_ed25519")
        assert cfg.host == "intel.example.com"
        assert cfg.key_path == "/home/user/.ssh/id_ed25519"
        assert cfg.port == 22
        assert cfg.sync_interval == 300
        assert cfg.sync_budget == 30
        assert cfg.max_file_size == 10485760

    def test_construction_custom(self):
        cfg = IntelConfig(
            host="10.0.0.1",
            key_path="/keys/tw",
            port=2222,
            sync_interval=600,
            sync_budget=60,
            max_file_size=5000000,
        )
        assert cfg.port == 2222
        assert cfg.sync_interval == 600
        assert cfg.sync_budget == 60
        assert cfg.max_file_size == 5000000

    def test_frozen(self):
        cfg = IntelConfig(host="x", key_path="/k")
        with pytest.raises(AttributeError):
            cfg.host = "y"  # type: ignore[misc]

    def test_empty_host(self):
        with pytest.raises(ValidationError, match="host must not be empty"):
            IntelConfig(host="   ", key_path="/k")

    def test_port_zero(self):
        with pytest.raises(ValidationError, match="port must be 1-65535"):
            IntelConfig(host="x", key_path="/k", port=0)

    def test_port_too_high(self):
        with pytest.raises(ValidationError, match="port must be 1-65535"):
            IntelConfig(host="x", key_path="/k", port=65536)

    def test_sync_budget_equals_interval(self):
        with pytest.raises(ValidationError, match="sync_budget must be less than sync_interval"):
            IntelConfig(host="x", key_path="/k", sync_interval=30, sync_budget=30)

    def test_sync_budget_exceeds_interval(self):
        with pytest.raises(ValidationError, match="sync_budget must be less than sync_interval"):
            IntelConfig(host="x", key_path="/k", sync_interval=30, sync_budget=60)

    def test_max_file_size_zero(self):
        with pytest.raises(ValidationError, match="max_file_size must be positive"):
            IntelConfig(host="x", key_path="/k", max_file_size=0)

    def test_max_file_size_negative(self):
        with pytest.raises(ValidationError, match="max_file_size must be positive"):
            IntelConfig(host="x", key_path="/k", max_file_size=-1)


class TestRemoteFile:
    def test_construction(self):
        f = RemoteFile(name="abc123.csv", size=1024)
        assert f.name == "abc123.csv"
        assert f.size == 1024

    def test_zero_size(self):
        f = RemoteFile(name="empty.csv", size=0)
        assert f.size == 0

    def test_frozen(self):
        f = RemoteFile(name="x", size=0)
        with pytest.raises(AttributeError):
            f.name = "y"  # type: ignore[misc]

    def test_empty_name(self):
        with pytest.raises(ValidationError, match="name must not be empty"):
            RemoteFile(name="   ", size=0)

    def test_negative_size(self):
        with pytest.raises(ValidationError, match="size must be non-negative"):
            RemoteFile(name="x", size=-1)


class TestIntelMergeResult:
    def test_defaults(self):
        r = IntelMergeResult()
        assert r.sectors_added == 0
        assert r.ports_added == 0
        assert r.ports_updated == 0
        assert r.warps_added == 0
        assert r.planets_added == 0

    def test_total(self):
        r = IntelMergeResult(sectors_added=5, ports_added=3, ports_updated=2, warps_added=10, planets_added=1)
        assert r.total == 21

    def test_total_defaults_zero(self):
        r = IntelMergeResult()
        assert r.total == 0

    def test_frozen(self):
        r = IntelMergeResult(sectors_added=1)
        with pytest.raises(AttributeError):
            r.sectors_added = 2  # type: ignore[misc]

    def test_negative_sectors_added(self):
        with pytest.raises(ValidationError, match="sectors_added must be non-negative"):
            IntelMergeResult(sectors_added=-1)

    def test_negative_ports_added(self):
        with pytest.raises(ValidationError, match="ports_added must be non-negative"):
            IntelMergeResult(ports_added=-1)


class TestSyncStatus:
    def test_defaults(self):
        s = SyncStatus()
        assert s.last_error is None
        assert s.shutdown_status is None

    def test_with_error(self):
        s = SyncStatus(last_error="E24")
        assert s.last_error == "E24"

    def test_with_shutdown_status(self):
        s = SyncStatus(shutdown_status="Done.")
        assert s.shutdown_status == "Done."

    def test_frozen(self):
        s = SyncStatus()
        with pytest.raises(AttributeError):
            s.last_error = "E24"  # type: ignore[misc]

    def test_empty_last_error(self):
        with pytest.raises(ValidationError, match="last_error must not be empty if set"):
            SyncStatus(last_error="   ")
