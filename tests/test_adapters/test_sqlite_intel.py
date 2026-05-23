"""Tests for SQLite IntelStore implementation."""

import time

import pytest

from tw_guidance_computer.adapters.outbound.sqlite_store import SqliteGameStateStore
from tw_guidance_computer.domain.models import (
    CommodityType,
    Planet,
    Port,
    PortCommodity,
    Sector,
    TradeDirection,
    WarpConnection,
)


@pytest.fixture()
def store(tmp_path):
    return SqliteGameStateStore(tmp_path / "test.db")


class TestMigrationIdempotent:
    def test_double_init_same_db(self, tmp_path):
        db_path = tmp_path / "test.db"
        store1 = SqliteGameStateStore(db_path)
        store1.close()
        # Second init should not raise on duplicate column
        store2 = SqliteGameStateStore(db_path)
        store2.close()


class TestLocalExport:
    def test_get_local_sectors_excludes_imported(self, store):
        store.upsert_sector(Sector(id=100, region="Local", explored=True))
        store.import_sectors(
            [(Sector(id=200, region="Remote", explored=True), 1000.0)],
            source="abc123",
        )
        results = store.get_local_sectors()
        assert len(results) == 1
        assert results[0][0].id == 100

    def test_get_local_ports_excludes_imported(self, store):
        store.upsert_port(Port(sector_id=100, name="Local Port", port_class=4, port_type="SSB"))
        store.import_ports(
            [(Port(sector_id=200, name="Remote Port", port_class=3, port_type="BBS"), 1000.0)],
            source="abc123",
        )
        results = store.get_local_ports()
        assert len(results) == 1
        assert results[0][0].sector_id == 100

    def test_get_local_warps_excludes_imported(self, store):
        store.upsert_warp(WarpConnection(from_sector=100, to_sector=200))
        store.import_warps(
            [(WarpConnection(from_sector=300, to_sector=400), 1000.0)],
            source="abc123",
        )
        results = store.get_local_warps()
        assert len(results) == 1
        assert results[0][0].from_sector == 100

    def test_get_local_planets_excludes_imported(self, store):
        store.upsert_planet(Planet(sector_id=100, name="Terra", planet_class="M"))
        store.import_planets(
            [(Planet(sector_id=200, name="Mars", planet_class="K"), 1000.0)],
            source="abc123",
        )
        results = store.get_local_planets()
        assert len(results) == 1
        assert results[0][0].sector_id == 100

    def test_local_sectors_include_updated_at(self, store):
        before = time.time()
        store.upsert_sector(Sector(id=100, region="Test", explored=True))
        after = time.time()
        results = store.get_local_sectors()
        assert len(results) == 1
        assert before <= results[0][1] <= after


class TestImportSectors:
    def test_inserts_new_sector(self, store):
        count = store.import_sectors(
            [(Sector(id=500, region="Far Away", explored=True), 1000.0)],
            source="remote1",
        )
        assert count == 1
        sector = store.get_sector(500)
        assert sector is not None
        assert sector.region == "Far Away"
        assert sector.explored is True

    def test_explored_beats_unexplored(self, store):
        # Local has unexplored
        store.upsert_sector(Sector(id=100, region="", explored=False))
        # Import explored version
        count = store.import_sectors(
            [(Sector(id=100, region="Found It", explored=True), 2000.0)],
            source="remote1",
        )
        assert count == 1
        sector = store.get_sector(100)
        assert sector is not None
        assert sector.explored is True
        assert sector.region == "Found It"

    def test_unexplored_does_not_beat_explored(self, store):
        store.upsert_sector(Sector(id=100, region="Known", explored=True))
        count = store.import_sectors(
            [(Sector(id=100, region="", explored=False), 9999.0)],
            source="remote1",
        )
        assert count == 0
        sector = store.get_sector(100)
        assert sector is not None
        assert sector.explored is True
        assert sector.region == "Known"

    def test_tie_keeps_local(self, store):
        # Insert local with known timestamp
        store._exec(
            "INSERT INTO sectors (id, region, explored, updated_at) VALUES (?, ?, ?, ?)",
            (100, "Local", 1, 1000.0),
        )
        store._commit()
        # Import with same timestamp — should NOT update
        count = store.import_sectors(
            [(Sector(id=100, region="Remote", explored=True), 1000.0)],
            source="remote1",
        )
        assert count == 0
        sector = store.get_sector(100)
        assert sector is not None
        assert sector.region == "Local"

    def test_fresher_updates(self, store):
        store._exec(
            "INSERT INTO sectors (id, region, explored, updated_at) VALUES (?, ?, ?, ?)",
            (100, "Old", 1, 1000.0),
        )
        store._commit()
        count = store.import_sectors(
            [(Sector(id=100, region="New", explored=True), 2000.0)],
            source="remote1",
        )
        assert count == 1
        sector = store.get_sector(100)
        assert sector is not None
        assert sector.region == "New"


class TestImportPorts:
    def test_inserts_new_port(self, store):
        port = Port(sector_id=500, name="New Port", port_class=3, port_type="BBS")
        count = store.import_ports([(port, 1000.0)], source="remote1")
        assert count == 1
        result = store.get_port(500)
        assert result is not None
        assert result.name == "New Port"

    def test_fresher_updates_port(self, store):
        store._exec(
            "INSERT INTO ports (sector_id, name, port_class, port_type, commodities_json, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (100, "Old Port", 4, "SSB", "[]", 1000.0),
        )
        store._commit()
        port = Port(sector_id=100, name="New Port", port_class=6, port_type="SBS")
        count = store.import_ports([(port, 2000.0)], source="remote1")
        assert count == 1
        result = store.get_port(100)
        assert result is not None
        assert result.name == "New Port"
        assert result.port_type == "SBS"

    def test_tie_keeps_local_port(self, store):
        store._exec(
            "INSERT INTO ports (sector_id, name, port_class, port_type, commodities_json, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (100, "Local Port", 4, "SSB", "[]", 1000.0),
        )
        store._commit()
        port = Port(sector_id=100, name="Remote Port", port_class=6, port_type="SBS")
        count = store.import_ports([(port, 1000.0)], source="remote1")
        assert count == 0
        result = store.get_port(100)
        assert result is not None
        assert result.name == "Local Port"

    def test_stale_does_not_update(self, store):
        store._exec(
            "INSERT INTO ports (sector_id, name, port_class, port_type, commodities_json, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (100, "Fresh Port", 4, "SSB", "[]", 2000.0),
        )
        store._commit()
        port = Port(sector_id=100, name="Stale Port", port_class=3, port_type="BBS")
        count = store.import_ports([(port, 1000.0)], source="remote1")
        assert count == 0
        result = store.get_port(100)
        assert result is not None
        assert result.name == "Fresh Port"

    def test_import_port_with_commodities(self, store):
        commodities = [
            PortCommodity(CommodityType.FUEL_ORE, TradeDirection.SELLING, 2000, 100),
            PortCommodity(CommodityType.ORGANICS, TradeDirection.BUYING, 500, 50),
        ]
        port = Port(sector_id=500, name="Rich Port", port_class=6, port_type="SBS", commodities=commodities)
        count = store.import_ports([(port, 1000.0)], source="remote1")
        assert count == 1
        result = store.get_port(500)
        assert result is not None
        assert len(result.commodities) == 2


class TestImportWarps:
    def test_inserts_new_warp(self, store):
        count = store.import_warps(
            [(WarpConnection(from_sector=500, to_sector=600), 1000.0)],
            source="remote1",
        )
        assert count == 1
        warps = store.get_warps(500)
        assert len(warps) == 1
        assert warps[0].to_sector == 600

    def test_ignores_existing_warp(self, store):
        store.upsert_warp(WarpConnection(from_sector=100, to_sector=200))
        count = store.import_warps(
            [(WarpConnection(from_sector=100, to_sector=200), 1000.0)],
            source="remote1",
        )
        assert count == 0

    def test_additive_new_warps(self, store):
        store.upsert_warp(WarpConnection(from_sector=100, to_sector=200))
        count = store.import_warps(
            [(WarpConnection(from_sector=100, to_sector=300), 1000.0)],
            source="remote1",
        )
        assert count == 1
        warps = store.get_warps(100)
        assert len(warps) == 2


class TestImportPlanets:
    def test_inserts_new_planet(self, store):
        count = store.import_planets(
            [(Planet(sector_id=500, name="Mars", planet_class="K"), 1000.0)],
            source="remote1",
        )
        assert count == 1
        assert store.has_planet(500) is True

    def test_ignores_existing_planet(self, store):
        store.upsert_planet(Planet(sector_id=100, name="Terra", planet_class="M"))
        count = store.import_planets(
            [(Planet(sector_id=100, name="Terra", planet_class="K"), 1000.0)],
            source="remote1",
        )
        assert count == 0

    def test_additive_different_planet(self, store):
        store.upsert_planet(Planet(sector_id=100, name="Terra", planet_class="M"))
        count = store.import_planets(
            [(Planet(sector_id=100, name="Luna", planet_class="K"), 1000.0)],
            source="remote1",
        )
        assert count == 1


class TestSourceColumn:
    def test_local_upsert_has_null_source(self, store):
        store.upsert_sector(Sector(id=100, region="Test", explored=True))
        row = store._exec("SELECT source FROM sectors WHERE id = ?", (100,)).fetchone()
        assert row[0] is None

    def test_import_sets_source(self, store):
        store.import_sectors(
            [(Sector(id=100, region="Test", explored=True), 1000.0)],
            source="abc123",
        )
        row = store._exec("SELECT source FROM sectors WHERE id = ?", (100,)).fetchone()
        assert row[0] == "abc123"

    def test_import_port_sets_source(self, store):
        store.import_ports(
            [(Port(sector_id=100, name="P", port_class=4, port_type="SSB"), 1000.0)],
            source="xyz789",
        )
        row = store._exec("SELECT source FROM ports WHERE sector_id = ?", (100,)).fetchone()
        assert row[0] == "xyz789"

    def test_import_warp_sets_source(self, store):
        store.import_warps(
            [(WarpConnection(from_sector=100, to_sector=200), 1000.0)],
            source="warp_src",
        )
        row = store._exec(
            "SELECT source FROM warps WHERE from_sector = ? AND to_sector = ?", (100, 200)
        ).fetchone()
        assert row[0] == "warp_src"

    def test_import_planet_sets_source(self, store):
        store.import_planets(
            [(Planet(sector_id=100, name="X", planet_class="M"), 1000.0)],
            source="planet_src",
        )
        row = store._exec(
            "SELECT source FROM planets WHERE sector_id = ? AND name = ?", (100, "X")
        ).fetchone()
        assert row[0] == "planet_src"


class TestExistingUpsertsRegression:
    def test_upsert_sector_still_works(self, store):
        store.upsert_sector(Sector(id=100, region="Test", explored=True))
        sector = store.get_sector(100)
        assert sector is not None
        assert sector.region == "Test"

    def test_upsert_port_still_works(self, store):
        store.upsert_port(Port(sector_id=100, name="Port", port_class=4, port_type="SSB"))
        port = store.get_port(100)
        assert port is not None
        assert port.name == "Port"

    def test_upsert_warp_still_works(self, store):
        store.upsert_warp(WarpConnection(from_sector=100, to_sector=200))
        warps = store.get_warps(100)
        assert len(warps) == 1

    def test_upsert_planet_still_works(self, store):
        store.upsert_planet(Planet(sector_id=100, name="Terra", planet_class="M"))
        assert store.has_planet(100) is True

    def test_upsert_sector_upgrades_explored(self, store):
        store.upsert_sector(Sector(id=100, region="", explored=False))
        store.upsert_sector(Sector(id=100, region="Found", explored=True))
        sector = store.get_sector(100)
        assert sector is not None
        assert sector.explored is True
        assert sector.region == "Found"
