"""Use case: parse a chunk of log text and update game state."""

from __future__ import annotations

import re
from typing import final

from tw_guidance_computer.application.ports.game_state_writer import GameStateWriter
from tw_guidance_computer.domain.models import (
    Planet,
    PlayerStatus,
    Port,
    Sector,
    WarpConnection,
)

_PROMPT_RE = re.compile(r"\[(\d+)\]\s*\(\?=Help\)")
_SECTOR_RE = re.compile(r"Sector\s+:\s+(\d+)\s+in\s+(.+?)\.")
_PORT_RE = re.compile(r"Ports\s+:\s+(.+?),\s+Class\s+(\d+)\s+\(([^)]+)\)")
_PLANET_RE = re.compile(r"Planets?\s*:\s*\(([A-Z])\)\s*(.+)")
_WARP_RE = re.compile(r"Warps to Sector\(s\)\s*:\s*([\d\s\-()]+)")
_NAV_PREFIX_RE = re.compile(r"^\s*\([TS*\d]\)")
_TURNS_STARDATE_RE = re.compile(r"You have (\d+) turns? this Stardate")
_TURNS_DEDUCTED_RE = re.compile(r"One turn deducted, (\d+) turns left")
_CREDITS_RE = re.compile(r"You have ([0-9,]+) credits")
_BAR_RE = re.compile(r"Sect\s+(\d+)\u2502Turns\s+([0-9,]+)\u2502Creds\s+([0-9,]+)")


@final
class ParseLogChunk:
    """Parse raw log text and update the game state store.

    This is the core parsing engine. It processes ANSI-stripped text
    and extracts sectors, ports, warps, turns, and credits.
    """

    def __init__(self, store: GameStateWriter) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store
        self._current_sector: int | None = None
        self._turns_remaining: int | None = None
        self._credits: int | None = None
        self._pending_sector: int | None = None

    def execute(self, text: str) -> None:
        """Parse a chunk of log text and persist extracted data.

        Args:
            text: ANSI-stripped log text to parse.
        """
        self._extract_sector_displays(text)
        self._extract_prompts(text)
        self._extract_turns(text)
        self._extract_credits(text)
        self._extract_status_bar(text)
        self._update_player_status()

    def _extract_prompts(self, text: str) -> None:
        for m in _PROMPT_RE.finditer(text):
            self._current_sector = int(m.group(1))

    def _extract_sector_displays(self, text: str) -> None:
        lines = text.splitlines()
        i = 0

        # Check if first lines are a continuation of a previous sector display
        if self._pending_sector is not None:
            while i < len(lines):
                sub = lines[i]

                warp_m = _WARP_RE.search(sub)
                if warp_m:
                    self._process_warps(self._pending_sector, warp_m.group(1))
                    self._pending_sector = None
                    i += 1
                    break

                if _NAV_PREFIX_RE.match(sub) or _SECTOR_RE.search(sub) or _PROMPT_RE.search(sub):
                    self._pending_sector = None
                    break

                port_m = _PORT_RE.search(sub)
                if port_m:
                    self._store.upsert_port(Port(
                        sector_id=self._pending_sector,
                        name=port_m.group(1).strip(),
                        port_class=int(port_m.group(2)),
                        port_type=port_m.group(3).strip(),
                    ))
                    i += 1
                    continue

                planet_m = _PLANET_RE.search(sub)
                if planet_m:
                    self._store.upsert_planet(Planet(
                        sector_id=self._pending_sector,
                        name=planet_m.group(2).strip(),
                        planet_class=planet_m.group(1),
                    ))
                    i += 1
                    continue

                # Unrecognized line — stop looking for continuation
                self._pending_sector = None
                break

        while i < len(lines):
            line = lines[i]
            # Skip nav menu lines
            if _NAV_PREFIX_RE.match(line):
                i += 1
                # Skip indented Ports/Planets lines that follow nav entries
                while i < len(lines) and lines[i].startswith("    "):
                    i += 1
                continue

            sector_m = _SECTOR_RE.search(line)
            if not sector_m:
                i += 1
                continue

            sector_id = int(sector_m.group(1))
            region = sector_m.group(2).strip()

            self._store.upsert_sector(Sector(id=sector_id, region=region, explored=True))
            self._current_sector = sector_id

            # Scan subsequent lines for port, planet, warps until next sector or prompt
            i += 1
            found_warps = False
            while i < len(lines):
                sub = lines[i]

                warp_m = _WARP_RE.search(sub)
                if warp_m:
                    self._process_warps(sector_id, warp_m.group(1))
                    found_warps = True
                    i += 1
                    break

                if _NAV_PREFIX_RE.match(sub) or _SECTOR_RE.search(sub) or _PROMPT_RE.search(sub):
                    break

                port_m = _PORT_RE.search(sub)
                if port_m:
                    self._store.upsert_port(Port(
                        sector_id=sector_id,
                        name=port_m.group(1).strip(),
                        port_class=int(port_m.group(2)),
                        port_type=port_m.group(3).strip(),
                    ))
                    i += 1
                    continue

                planet_m = _PLANET_RE.search(sub)
                if planet_m:
                    self._store.upsert_planet(Planet(
                        sector_id=sector_id,
                        name=planet_m.group(2).strip(),
                        planet_class=planet_m.group(1),
                    ))
                    i += 1
                    continue

                i += 1

            # If we ran out of lines without finding warps, remember for next chunk
            if not found_warps and i >= len(lines):
                self._pending_sector = sector_id

    def _process_warps(self, sector_id: int, warp_text: str) -> None:
        all_sectors = re.findall(r"\d+", warp_text)
        unexplored = set(re.findall(r"\((\d+)\)", warp_text))
        warps: list[WarpConnection] = []
        for w in all_sectors:
            w_id = int(w)
            if w_id == 0:
                continue
            is_explored = w not in unexplored
            self._store.upsert_sector(Sector(id=w_id, explored=is_explored))
            warps.append(WarpConnection(from_sector=sector_id, to_sector=w_id, explored=is_explored))
        self._store.replace_warps_from_sector(sector_id, warps)

    def _extract_turns(self, text: str) -> None:
        for m in _TURNS_STARDATE_RE.finditer(text):
            self._turns_remaining = int(m.group(1))
        for m in _TURNS_DEDUCTED_RE.finditer(text):
            self._turns_remaining = int(m.group(1))

    def _extract_credits(self, text: str) -> None:
        for m in _CREDITS_RE.finditer(text):
            # Skip bank pattern: "credits in your account"
            after = text[m.end():m.end() + 30]
            if "in your account" in after:
                continue
            self._credits = int(m.group(1).replace(",", ""))

    def _extract_status_bar(self, text: str) -> None:
        for m in _BAR_RE.finditer(text):
            self._current_sector = int(m.group(1))
            self._turns_remaining = int(m.group(2).replace(",", ""))
            self._credits = int(m.group(3).replace(",", ""))

    def _update_player_status(self) -> None:
        if self._current_sector is not None:
            self._store.set_player_status(PlayerStatus(
                sector_id=self._current_sector,
                turns_remaining=self._turns_remaining or 0,
                credits=self._credits or 0,
                cargo=[],
                holds_total=0,
                holds_empty=0,
            ))
