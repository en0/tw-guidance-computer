"""SQLite implementation of the GameStateReader and GameStateWriter ports."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import final, override

from tw_guidance_computer.application.ports.game_state_reader import GameStateReader
from tw_guidance_computer.application.ports.game_state_writer import GameStateWriter
from tw_guidance_computer.application.ports.intel_store import IntelStore
from tw_guidance_computer.domain.exceptions import StorageError
from tw_guidance_computer.domain.models import (
    CargoHold,
    ChatMessage,
    CommodityType,
    Planet,
    PlayerStatus,
    Port,
    PortCommodity,
    Sector,
    TradeDirection,
    WarpConnection,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sectors (
    id INTEGER PRIMARY KEY,
    region TEXT NOT NULL DEFAULT '',
    explored INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ports (
    sector_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    port_class INTEGER NOT NULL DEFAULT 0,
    port_type TEXT NOT NULL DEFAULT '',
    commodities_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS warps (
    from_sector INTEGER NOT NULL,
    to_sector INTEGER NOT NULL,
    explored INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (from_sector, to_sector)
);

CREATE TABLE IF NOT EXISTS player_status (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    sector_id INTEGER NOT NULL,
    turns_remaining INTEGER NOT NULL DEFAULT 0,
    credits INTEGER NOT NULL DEFAULT 0,
    cargo_json TEXT NOT NULL DEFAULT '[]',
    holds_total INTEGER NOT NULL DEFAULT 0,
    holds_empty INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT NOT NULL,
    message TEXT NOT NULL,
    channel TEXT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS planets (
    sector_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    planet_class TEXT NOT NULL,
    PRIMARY KEY (sector_id, name)
);
"""


@final
class SqliteGameStateStore(GameStateReader, GameStateWriter, IntelStore):
    """SQLite-backed persistent game state store."""

    def __init__(self, db_path: Path) -> None:
        """Initialize the SQLite store.

        Args:
            db_path: Path to the SQLite database file.

        Raises:
            StorageError: If the database cannot be opened or initialized.
        """
        self._db_path = db_path
        try:
            self._conn = sqlite3.connect(str(db_path), isolation_level="DEFERRED")
            self._exec("PRAGMA journal_mode=WAL")
            self._exec("PRAGMA busy_timeout=5000")
            self._conn.executescript(_SCHEMA)
            self._run_migrations()
            self._commit()
        except sqlite3.Error as e:
            raise StorageError(f"Failed to initialize database: {e}") from e

    def _run_migrations(self) -> None:
        """Add source and updated_at columns to existing tables (idempotent)."""
        migrations = [
            "ALTER TABLE sectors ADD COLUMN source TEXT DEFAULT NULL",
            "ALTER TABLE sectors ADD COLUMN updated_at REAL DEFAULT 0.0",
            "ALTER TABLE ports ADD COLUMN source TEXT DEFAULT NULL",
            "ALTER TABLE ports ADD COLUMN updated_at REAL DEFAULT 0.0",
            "ALTER TABLE warps ADD COLUMN source TEXT DEFAULT NULL",
            "ALTER TABLE warps ADD COLUMN updated_at REAL DEFAULT 0.0",
            "ALTER TABLE planets ADD COLUMN source TEXT DEFAULT NULL",
            "ALTER TABLE planets ADD COLUMN updated_at REAL DEFAULT 0.0",
        ]
        for sql in migrations:
            try:
                self._conn.execute(sql)
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e):
                    raise StorageError(f"Migration failed: {e}") from e

    def _exec(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:  # type: ignore[type-arg]
        try:
            return self._conn.execute(sql, params)
        except sqlite3.Error as e:
            raise StorageError(f"Database operation failed: {e}") from e

    def _commit(self) -> None:
        try:
            self._conn.commit()
        except sqlite3.Error as e:
            raise StorageError(f"Database commit failed: {e}") from e

    @override
    def upsert_sector(self, sector: Sector) -> None:
        self._exec(
            """INSERT INTO sectors (id, region, explored, updated_at) VALUES (?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 region = CASE WHEN excluded.region != '' THEN excluded.region ELSE sectors.region END,
                 explored = MAX(sectors.explored, excluded.explored),
                 updated_at = excluded.updated_at""",
            (sector.id, sector.region, int(sector.explored), time.time()),
        )
        self._commit()

    @override
    def upsert_port(self, port: Port) -> None:
        commodities_json = json.dumps(
            [
                {
                    "commodity": pc.commodity.value,
                    "direction": pc.direction.value,
                    "quantity": pc.quantity,
                    "pct": pc.pct,
                }
                for pc in port.commodities
            ]
        )
        self._exec(
            """INSERT INTO ports (sector_id, name, port_class, port_type, commodities_json, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(sector_id) DO UPDATE SET
                 name = excluded.name,
                 port_class = CASE WHEN excluded.port_class != 0 THEN excluded.port_class ELSE ports.port_class END,
                 port_type = excluded.port_type,
                 commodities_json = CASE WHEN excluded.commodities_json != '[]'
                   THEN excluded.commodities_json ELSE ports.commodities_json END,
                 updated_at = excluded.updated_at""",
            (port.sector_id, port.name, port.port_class, port.port_type, commodities_json, time.time()),
        )
        self._commit()

    @override
    def upsert_warp(self, warp: WarpConnection) -> None:
        self._exec(
            """INSERT INTO warps (from_sector, to_sector, explored, updated_at) VALUES (?, ?, ?, ?)
               ON CONFLICT(from_sector, to_sector) DO UPDATE SET
                 explored = MAX(warps.explored, excluded.explored),
                 updated_at = excluded.updated_at""",
            (warp.from_sector, warp.to_sector, int(warp.explored), time.time()),
        )
        self._commit()

    @override
    def set_player_status(self, status: PlayerStatus) -> None:
        cargo_json = json.dumps(
            [
                {
                    "commodity": h.commodity.value,
                    "quantity": h.quantity,
                    "cost_per_unit": h.cost_per_unit,
                }
                for h in status.cargo
            ]
        )
        self._exec(
            """INSERT INTO player_status (id, sector_id, turns_remaining, credits, cargo_json, holds_total, holds_empty)
               VALUES (1, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 sector_id = excluded.sector_id,
                 turns_remaining = excluded.turns_remaining,
                 credits = excluded.credits,
                 cargo_json = excluded.cargo_json,
                 holds_total = excluded.holds_total,
                 holds_empty = excluded.holds_empty""",
            (status.sector_id, status.turns_remaining, status.credits,
             cargo_json, status.holds_total, status.holds_empty),
        )
        self._commit()

    @override
    def add_chat_message(self, message: ChatMessage) -> None:
        self._exec(
            "INSERT INTO chat_messages (sender, message, channel, timestamp) VALUES (?, ?, ?, ?)",
            (message.sender, message.message, message.channel, message.timestamp),
        )
        self._commit()

    @override
    def get_sector(self, sector_id: int) -> Sector | None:
        row = self._exec(
            "SELECT id, region, explored FROM sectors WHERE id = ?", (sector_id,)
        ).fetchone()
        if row is None:
            return None
        return Sector(id=row[0], region=row[1], explored=bool(row[2]))

    @override
    def get_port(self, sector_id: int) -> Port | None:
        row = self._exec(
            "SELECT sector_id, name, port_class, port_type, commodities_json FROM ports WHERE sector_id = ?",
            (sector_id,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_port(row)

    @override
    def get_warps(self, sector_id: int) -> list[WarpConnection]:
        rows = self._exec(
            "SELECT from_sector, to_sector, explored FROM warps WHERE from_sector = ?",
            (sector_id,),
        ).fetchall()
        return [WarpConnection(from_sector=r[0], to_sector=r[1], explored=bool(r[2])) for r in rows]

    @override
    def get_all_warps(self) -> list[WarpConnection]:
        rows = self._exec("SELECT from_sector, to_sector, explored FROM warps").fetchall()
        return [WarpConnection(from_sector=r[0], to_sector=r[1], explored=bool(r[2])) for r in rows]

    @override
    def get_all_ports(self) -> list[Port]:
        rows = self._exec(
            "SELECT sector_id, name, port_class, port_type, commodities_json FROM ports"
        ).fetchall()
        return [_row_to_port(r) for r in rows]

    @override
    def get_player_status(self) -> PlayerStatus | None:
        row = self._exec(
            "SELECT sector_id, turns_remaining, credits, cargo_json, holds_total, holds_empty"
            " FROM player_status WHERE id = 1"
        ).fetchone()
        if row is None:
            return None
        try:
            cargo_data = json.loads(row[3])
            cargo = [
                CargoHold(
                    commodity=CommodityType(c["commodity"]),
                    quantity=c["quantity"],
                    cost_per_unit=c["cost_per_unit"],
                )
                for c in cargo_data
            ]
        except (json.JSONDecodeError, TypeError, ValueError, KeyError) as e:
            raise StorageError(f"Corrupt cargo data in player_status: {e}") from e
        return PlayerStatus(
            sector_id=row[0],
            turns_remaining=row[1],
            credits=row[2],
            cargo=cargo,
            holds_total=row[4],
            holds_empty=row[5],
        )

    @override
    def get_recent_chat(self, limit: int = 20) -> list[ChatMessage]:
        rows = self._exec(
            "SELECT sender, message, channel, timestamp FROM chat_messages ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            ChatMessage(sender=r[0], message=r[1], channel=r[2], timestamp=r[3])
            for r in rows
        ]

    @override
    def upsert_planet(self, planet: Planet) -> None:
        self._exec(
            """INSERT INTO planets (sector_id, name, planet_class, updated_at) VALUES (?, ?, ?, ?)
               ON CONFLICT(sector_id, name) DO UPDATE SET
                 planet_class = excluded.planet_class,
                 updated_at = excluded.updated_at""",
            (planet.sector_id, planet.name, planet.planet_class, time.time()),
        )
        self._commit()

    @override
    def has_planet(self, sector_id: int) -> bool:
        row = self._exec(
            "SELECT 1 FROM planets WHERE sector_id = ? LIMIT 1", (sector_id,)
        ).fetchone()
        return row is not None

    @override
    def get_safe_sector_ids(self) -> list[int]:
        rows = self._exec(
            "SELECT id FROM sectors WHERE region = 'The Federation' "
            "UNION "
            "SELECT sector_id FROM ports WHERE port_class = 0",
        ).fetchall()
        return [row[0] for row in rows]

    # --- IntelStore implementation ---

    @override
    def get_local_sectors(self) -> list[tuple[Sector, float]]:
        """Return all locally-discovered sectors with their updated_at timestamps."""
        rows = self._exec(
            "SELECT id, region, explored, updated_at FROM sectors WHERE source IS NULL"
        ).fetchall()
        return [
            (Sector(id=r[0], region=r[1], explored=bool(r[2])), r[3])
            for r in rows
        ]

    @override
    def get_local_ports(self) -> list[tuple[Port, float]]:
        """Return all locally-discovered ports with their updated_at timestamps."""
        rows = self._exec(
            "SELECT sector_id, name, port_class, port_type, commodities_json, updated_at"
            " FROM ports WHERE source IS NULL"
        ).fetchall()
        return [(_row_to_port(r[:5]), r[5]) for r in rows]

    @override
    def get_local_warps(self) -> list[tuple[WarpConnection, float]]:
        """Return all locally-discovered warps with their updated_at timestamps."""
        rows = self._exec(
            "SELECT from_sector, to_sector, explored, updated_at FROM warps WHERE source IS NULL"
        ).fetchall()
        return [
            (WarpConnection(from_sector=r[0], to_sector=r[1], explored=bool(r[2])), r[3])
            for r in rows
        ]

    @override
    def get_local_planets(self) -> list[tuple[Planet, float]]:
        """Return all locally-discovered planets with their updated_at timestamps."""
        rows = self._exec(
            "SELECT sector_id, name, planet_class, updated_at FROM planets WHERE source IS NULL"
        ).fetchall()
        return [
            (Planet(sector_id=r[0], name=r[1], planet_class=r[2]), r[3])
            for r in rows
        ]

    @override
    def import_sectors(self, sectors: list[tuple[Sector, float]], source: str) -> int:
        """Import sectors with explored-beats-unexplored merge strategy."""
        count = 0
        for sector, updated_at in sectors:
            row = self._exec(
                "SELECT explored, updated_at FROM sectors WHERE id = ?",
                (sector.id,),
            ).fetchone()
            if row is None:
                self._exec(
                    "INSERT INTO sectors (id, region, explored, source, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (sector.id, sector.region, int(sector.explored), source, updated_at),
                )
                count += 1
            else:
                existing_explored, existing_ts = bool(row[0]), row[1]
                # Explored beats unexplored
                if sector.explored and not existing_explored:
                    self._exec(
                        "UPDATE sectors SET"
                        " region = CASE WHEN ? != '' THEN ? ELSE region END,"
                        " explored = 1, source = ?, updated_at = ? WHERE id = ?",
                        (sector.region, sector.region, source, updated_at, sector.id),
                    )
                    count += 1
                elif not sector.explored and existing_explored:
                    pass
                elif updated_at > existing_ts:
                    # Same explored status, incoming is strictly fresher
                    self._exec(
                        "UPDATE sectors SET"
                        " region = CASE WHEN ? != '' THEN ? ELSE region END,"
                        " source = ?, updated_at = ? WHERE id = ?",
                        (sector.region, sector.region, source, updated_at, sector.id),
                    )
                    count += 1
        self._commit()
        return count

    @override
    def import_ports(self, ports: list[tuple[Port, float]], source: str) -> int:
        """Import ports with freshest-wins merge strategy (strict >)."""
        count = 0
        for port, updated_at in ports:
            row = self._exec(
                "SELECT updated_at FROM ports WHERE sector_id = ?",
                (port.sector_id,),
            ).fetchone()
            commodities_json = json.dumps(
                [
                    {
                        "commodity": pc.commodity.value,
                        "direction": pc.direction.value,
                        "quantity": pc.quantity,
                        "pct": pc.pct,
                    }
                    for pc in port.commodities
                ]
            )
            if row is None:
                self._exec(
                    "INSERT INTO ports (sector_id, name, port_class, port_type, commodities_json, source, updated_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (port.sector_id, port.name, port.port_class, port.port_type,
                     commodities_json, source, updated_at),
                )
                count += 1
            elif updated_at > row[0]:
                self._exec(
                    "UPDATE ports SET name = ?, port_class = ?, port_type = ?,"
                    " commodities_json = ?, source = ?, updated_at = ? WHERE sector_id = ?",
                    (port.name, port.port_class, port.port_type,
                     commodities_json, source, updated_at, port.sector_id),
                )
                count += 1
        self._commit()
        return count

    @override
    def import_warps(self, warps: list[tuple[WarpConnection, float]], source: str) -> int:
        """Import warps with additive (INSERT OR IGNORE) strategy."""
        count = 0
        for warp, updated_at in warps:
            cursor = self._exec(
                "INSERT OR IGNORE INTO warps (from_sector, to_sector, explored, source, updated_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (warp.from_sector, warp.to_sector, int(warp.explored), source, updated_at),
            )
            count += cursor.rowcount
        self._commit()
        return count

    @override
    def import_planets(self, planets: list[tuple[Planet, float]], source: str) -> int:
        """Import planets with additive (INSERT OR IGNORE) strategy."""
        count = 0
        for planet, updated_at in planets:
            cursor = self._exec(
                "INSERT OR IGNORE INTO planets (sector_id, name, planet_class, source, updated_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (planet.sector_id, planet.name, planet.planet_class, source, updated_at),
            )
            count += cursor.rowcount
        self._commit()
        return count

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()


def _row_to_port(row: tuple) -> Port:  # type: ignore[type-arg]
    try:
        commodities_data = json.loads(row[4])
        commodities = [
            PortCommodity(
                commodity=CommodityType(c["commodity"]),
                direction=TradeDirection(c["direction"]),
                quantity=c["quantity"],
                pct=c["pct"],
            )
            for c in commodities_data
        ]
    except (json.JSONDecodeError, TypeError, ValueError, KeyError) as e:
        raise StorageError(f"Corrupt commodities data for port {row[0]}: {e}") from e
    return Port(
        sector_id=row[0],
        name=row[1],
        port_class=row[2],
        port_type=row[3],
        commodities=commodities,
    )
