"""Tests for the SQLite game state store."""

import pytest

from tw_guidance_computer.adapters.sqlite_store import SqliteGameStateStore
from tw_guidance_computer.domain.models import (
    CargoHold,
    ChatMessage,
    CommodityType,
    PlayerStatus,
    Port,
    PortCommodity,
    Sector,
    TradeDirection,
    WarpConnection,
)


@pytest.fixture()
def store(tmp_path):
    return SqliteGameStateStore(tmp_path / "test.db")


class TestSqliteGameStateStore:
    def test_upsert_and_get_sector(self, store):
        store.upsert_sector(Sector(id=100, region="Test", explored=True))
        sector = store.get_sector(100)
        assert sector is not None
        assert sector.region == "Test"
        assert sector.explored is True

    def test_upsert_preserves_region(self, store):
        store.upsert_sector(Sector(id=100, region="Known Region", explored=True))
        store.upsert_sector(Sector(id=100, region="", explored=True))
        sector = store.get_sector(100)
        assert sector is not None
        assert sector.region == "Known Region"

    def test_upsert_upgrades_explored(self, store):
        store.upsert_sector(Sector(id=100, region="", explored=False))
        store.upsert_sector(Sector(id=100, region="Found", explored=True))
        sector = store.get_sector(100)
        assert sector is not None
        assert sector.explored is True

    def test_upsert_and_get_port(self, store):
        commodities = [
            PortCommodity(CommodityType.FUEL_ORE, TradeDirection.SELLING, 2000, 100),
        ]
        store.upsert_port(Port(sector_id=100, name="Test Port", port_class=4, port_type="SSB", commodities=commodities))
        port = store.get_port(100)
        assert port is not None
        assert port.name == "Test Port"
        assert port.port_type == "SSB"
        assert len(port.commodities) == 1

    def test_upsert_and_get_warps(self, store):
        store.upsert_warp(WarpConnection(from_sector=100, to_sector=200))
        store.upsert_warp(WarpConnection(from_sector=100, to_sector=300))
        warps = store.get_warps(100)
        assert len(warps) == 2

    def test_player_status_roundtrip(self, store):
        cargo = [CargoHold(CommodityType.ORGANICS, 20, 31.5)]
        store.set_player_status(PlayerStatus(
            sector_id=865, turns_remaining=800, credits=5000,
            cargo=cargo, holds_total=20, holds_empty=0,
        ))
        status = store.get_player_status()
        assert status is not None
        assert status.sector_id == 865
        assert status.turns_remaining == 800
        assert status.credits == 5000
        assert len(status.cargo) == 1
        assert status.cargo[0].cost_per_unit == 31.5

    def test_chat_messages(self, store):
        store.add_chat_message(ChatMessage(sender="bob", message="hello", channel="radio"))
        store.add_chat_message(ChatMessage(sender="alice", message="hi", channel="fed"))
        messages = store.get_recent_chat(limit=10)
        assert len(messages) == 2
        assert messages[0].sender == "alice"  # newest first

    def test_get_all_ports(self, store):
        store.upsert_port(Port(sector_id=100, name="A", port_class=4, port_type="SSB"))
        store.upsert_port(Port(sector_id=200, name="B", port_class=1, port_type="BBS"))
        ports = store.get_all_ports()
        assert len(ports) == 2

    def test_persistence(self, tmp_path):
        db_path = tmp_path / "persist.db"
        store1 = SqliteGameStateStore(db_path)
        store1.upsert_sector(Sector(id=42, region="Persistent", explored=True))
        store1.close()

        store2 = SqliteGameStateStore(db_path)
        sector = store2.get_sector(42)
        assert sector is not None
        assert sector.region == "Persistent"
        store2.close()
