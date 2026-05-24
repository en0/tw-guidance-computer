"""Tests for the SQLite game state store."""

import pytest

from tw_guidance_computer.adapters.outbound.sqlite_store import SqliteGameStateStore
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
        assert status.cargo == []

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


    def test_upsert_and_has_planet(self, store, make_planet):
        planet = make_planet(sector_id=616, name="Terra", planet_class="M")
        store.upsert_planet(planet)
        assert store.has_planet(616) is True

    def test_has_planet_false(self, store):
        assert store.has_planet(999) is False

    def test_multiple_planets_per_sector(self, store, make_planet):
        store.upsert_planet(make_planet(sector_id=1, name="Terra", planet_class="M"))
        store.upsert_planet(make_planet(sector_id=1, name="Luna", planet_class="K"))
        assert store.has_planet(1) is True

    def test_upsert_planet_updates_class(self, store, make_planet):
        store.upsert_planet(make_planet(sector_id=5, name="X", planet_class="M"))
        store.upsert_planet(make_planet(sector_id=5, name="X", planet_class="K"))
        assert store.has_planet(5) is True


class TestGetSafeSectorIds:
    def test_returns_federation_sectors(self, store):
        store.upsert_sector(Sector(id=1, region="The Federation", explored=True))
        store.upsert_sector(Sector(id=500, region="uncharted space", explored=True))
        result = store.get_safe_sector_ids()
        assert 1 in result
        assert 500 not in result

    def test_returns_stardock_sectors(self, store):
        store.upsert_port(Port(sector_id=42, name="StarDock", port_class=0, port_type=""))
        result = store.get_safe_sector_ids()
        assert 42 in result

    def test_returns_union_without_duplicates(self, store):
        store.upsert_sector(Sector(id=1, region="The Federation", explored=True))
        store.upsert_port(Port(sector_id=1, name="Sol", port_class=0, port_type=""))
        result = store.get_safe_sector_ids()
        assert result.count(1) == 1

    def test_returns_empty_when_no_safe_sectors(self, store):
        store.upsert_sector(Sector(id=500, region="uncharted space", explored=True))
        store.upsert_port(Port(sector_id=600, name="Trader Vic's", port_class=6, port_type="SBS"))
        result = store.get_safe_sector_ids()
        assert result == []


class TestCargoStubbed:
    def test_get_player_status_returns_empty_cargo(self, store):
        cargo = [CargoHold(CommodityType.ORGANICS, 20, 31.5)]
        store.set_player_status(PlayerStatus(
            sector_id=100, turns_remaining=500, credits=1000,
            cargo=cargo, holds_total=20, holds_empty=0,
        ))
        status = store.get_player_status()
        assert status is not None
        assert status.cargo == []

    def test_set_player_status_still_stores_cargo(self, store):
        cargo = [CargoHold(CommodityType.FUEL_ORE, 10, 50.0)]
        store.set_player_status(PlayerStatus(
            sector_id=100, turns_remaining=500, credits=1000,
            cargo=cargo, holds_total=20, holds_empty=10,
        ))
        row = store._exec(
            "SELECT cargo_json FROM player_status WHERE id = 1"
        ).fetchone()
        assert row is not None
        assert "Fuel Ore" in row[0]


class TestReplaceWarpsFromSector:
    def test_replaces_existing_warps(self, store):
        store.upsert_warp(WarpConnection(from_sector=100, to_sector=200))
        store.upsert_warp(WarpConnection(from_sector=100, to_sector=300))
        store.replace_warps_from_sector(100, [
            WarpConnection(from_sector=100, to_sector=400),
            WarpConnection(from_sector=100, to_sector=500),
        ])
        warps = store.get_warps(100)
        destinations = sorted(w.to_sector for w in warps)
        assert destinations == [400, 500]

    def test_inserts_when_no_prior_warps(self, store):
        store.replace_warps_from_sector(100, [
            WarpConnection(from_sector=100, to_sector=200),
        ])
        warps = store.get_warps(100)
        assert len(warps) == 1
        assert warps[0].to_sector == 200

    def test_does_not_affect_other_sectors(self, store):
        store.upsert_warp(WarpConnection(from_sector=100, to_sector=200))
        store.upsert_warp(WarpConnection(from_sector=200, to_sector=300))
        store.replace_warps_from_sector(100, [
            WarpConnection(from_sector=100, to_sector=999),
        ])
        warps_200 = store.get_warps(200)
        assert len(warps_200) == 1
        assert warps_200[0].to_sector == 300

    def test_removes_intel_imported_warps(self, store):
        store.import_warps(
            [(WarpConnection(from_sector=100, to_sector=200), 1000.0)],
            source="remote1",
        )
        store.replace_warps_from_sector(100, [
            WarpConnection(from_sector=100, to_sector=300),
        ])
        warps = store.get_warps(100)
        assert len(warps) == 1
        assert warps[0].to_sector == 300
