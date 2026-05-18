"""SQLite implementation of the GameStateStore port."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import final, override

from tw_guidance_computer.application.ports.game_state_store import GameStateStore
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
class SqliteGameStateStore(GameStateStore):
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
            self._commit()
        except sqlite3.Error as e:
            raise StorageError(f"Failed to initialize database: {e}") from e

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
            """INSERT INTO sectors (id, region, explored) VALUES (?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 region = CASE WHEN excluded.region != '' THEN excluded.region ELSE sectors.region END,
                 explored = MAX(sectors.explored, excluded.explored)""",
            (sector.id, sector.region, int(sector.explored)),
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
            """INSERT INTO ports (sector_id, name, port_class, port_type, commodities_json)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(sector_id) DO UPDATE SET
                 name = excluded.name,
                 port_class = CASE WHEN excluded.port_class != 0 THEN excluded.port_class ELSE ports.port_class END,
                 port_type = excluded.port_type,
                 commodities_json = CASE WHEN excluded.commodities_json != '[]'
                   THEN excluded.commodities_json ELSE ports.commodities_json END""",
            (port.sector_id, port.name, port.port_class, port.port_type, commodities_json),
        )
        self._commit()

    @override
    def upsert_warp(self, warp: WarpConnection) -> None:
        self._exec(
            """INSERT INTO warps (from_sector, to_sector, explored) VALUES (?, ?, ?)
               ON CONFLICT(from_sector, to_sector) DO UPDATE SET
                 explored = MAX(warps.explored, excluded.explored)""",
            (warp.from_sector, warp.to_sector, int(warp.explored)),
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
            """INSERT INTO planets (sector_id, name, planet_class) VALUES (?, ?, ?)
               ON CONFLICT(sector_id, name) DO UPDATE SET
                 planet_class = excluded.planet_class""",
            (planet.sector_id, planet.name, planet.planet_class),
        )
        self._commit()

    @override
    def has_planet(self, sector_id: int) -> bool:
        row = self._exec(
            "SELECT 1 FROM planets WHERE sector_id = ? LIMIT 1", (sector_id,)
        ).fetchone()
        return row is not None

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
