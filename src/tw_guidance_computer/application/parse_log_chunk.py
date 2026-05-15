"""Use case: parse a chunk of log text and update game state."""

from __future__ import annotations

import re
from typing import final

from tw_guidance_computer.application.ports.game_state_store import GameStateStore
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


@final
class ParseLogChunk:
    """Parse raw log text and update the game state store.

    This is the core parsing engine. It processes ANSI-stripped text
    and extracts sectors, ports, warps, inventory, and chat.
    """

    def __init__(self, store: GameStateStore) -> None:
        """Initialize with a game state store.

        Args:
            store: The persistent game state store.
        """
        self._store = store
        self._current_sector: int | None = None
        self._turns_remaining: int | None = None
        self._credits: int | None = None
        self._cargo: list[CargoHold] = []
        self._holds_total: int = 0
        self._holds_empty: int = 0

    def execute(self, text: str) -> None:
        """Parse a chunk of log text and persist extracted data.

        Args:
            text: ANSI-stripped log text to parse.
        """
        self._extract_sectors_and_warps(text)
        self._extract_ports(text)
        self._extract_commerce_reports(text)
        self._extract_player_state(text)
        self._extract_chat(text)
        self._update_player_status()

    def _extract_sectors_and_warps(self, text: str) -> None:
        sector_re = re.compile(
            r"Sector\s+:\s+(\d+)\s+in\s+(.+?)\."
        )
        warp_re = re.compile(
            r"Warps to Sector\(s\)\s*:\s*(.+?)(?:Stop|Auto|Command|\n|$)"
        )

        # Find all sector displays and their associated warps
        for m in sector_re.finditer(text):
            sector_id = int(m.group(1))
            region = m.group(2).strip().rstrip(".")
            region = re.sub(r"\s*\((?:unexplored|Not Scanning)\)\s*$", "", region)
            region = re.sub(r"\s*$", "", region)

            self._store.upsert_sector(Sector(id=sector_id, region=region, explored=True))
            self._current_sector = sector_id

            # Look for warps after this sector display
            after = text[m.end() : m.end() + 500]
            warp_match = warp_re.search(after)
            if warp_match:
                warp_text = warp_match.group(1)
                all_sectors = re.findall(r"\d+", warp_text)
                unexplored = set(re.findall(r"\((\d+)\)", warp_text))

                for w in all_sectors:
                    w_id = int(w)
                    if w_id == 0:
                        continue
                    is_explored = w not in unexplored
                    self._store.upsert_sector(
                        Sector(id=w_id, explored=is_explored)
                    )
                    self._store.upsert_warp(
                        WarpConnection(
                            from_sector=sector_id,
                            to_sector=w_id,
                            explored=is_explored,
                        )
                    )

    def _extract_ports(self, text: str) -> None:
        port_re = re.compile(
            r"Ports\s+:\s+(.+?),\s+Class\s+(\d+)\s+\(([^)]+)\)"
        )
        sector_re = re.compile(r"Sector\s+:\s+(\d+)")

        for m in port_re.finditer(text):
            port_name = m.group(1).strip()
            port_class = int(m.group(2))
            port_type = m.group(3).strip()

            # Find the sector this port belongs to
            preceding = text[max(0, m.start() - 300) : m.start()]
            sec_match = list(sector_re.finditer(preceding))
            if not sec_match:
                continue
            sector_id = int(sec_match[-1].group(1))

            self._store.upsert_port(
                Port(
                    sector_id=sector_id,
                    name=port_name,
                    port_class=port_class,
                    port_type=port_type,
                )
            )

    def _extract_commerce_reports(self, text: str) -> None:
        commerce_re = re.compile(
            r"Commerce report for\s+(.+?):\s+\d{2}:\d{2}:\d{2}"
        )
        item_re = re.compile(
            r"(Fuel Ore|Organics|Equipment)\s+(Selling|Buying)\s+(\d+)\s+(\d+)%"
        )
        prompt_re = re.compile(r"\[(\d+)\]")

        for m in commerce_re.finditer(text):
            port_name = m.group(1).strip()

            # Find sector from preceding command prompt
            preceding = text[max(0, m.start() - 500) : m.start()]
            prompts = list(prompt_re.finditer(preceding))
            if not prompts:
                continue
            sector_id = int(prompts[-1].group(1))

            # Parse commodity lines
            after = text[m.end() : m.end() + 500]
            commodities: list[PortCommodity] = []
            for item_m in item_re.finditer(after):
                commodity = _parse_commodity_type(item_m.group(1))
                direction = (
                    TradeDirection.SELLING
                    if item_m.group(2) == "Selling"
                    else TradeDirection.BUYING
                )
                quantity = int(item_m.group(3))
                pct = int(item_m.group(4))
                commodities.append(
                    PortCommodity(
                        commodity=commodity,
                        direction=direction,
                        quantity=quantity,
                        pct=pct,
                    )
                )

            if commodities:
                # Derive type code from commodities
                type_code = ""
                for c in [CommodityType.FUEL_ORE, CommodityType.ORGANICS, CommodityType.EQUIPMENT]:
                    for pc in commodities:
                        if pc.commodity == c:
                            type_code += "S" if pc.direction == TradeDirection.SELLING else "B"
                            break

                self._store.upsert_port(
                    Port(
                        sector_id=sector_id,
                        name=port_name,
                        port_class=0,
                        port_type=type_code,
                        commodities=commodities,
                    )
                )

    def _extract_player_state(self, text: str) -> None:
        # Track turns remaining
        turns_re = re.compile(r"(\d+)\s+turns? left")
        for m in turns_re.finditer(text):
            self._turns_remaining = int(m.group(1))

        # Track credits
        credits_re = re.compile(r"You have\s+([0-9,]+)\s+credits")
        for m in credits_re.finditer(text):
            self._credits = int(m.group(1).replace(",", ""))

        # Track empty holds
        holds_re = re.compile(r"You have\s+[0-9,]+\s+credits and\s+(\d+)\s+empty cargo holds")
        for m in holds_re.finditer(text):
            self._holds_empty = int(m.group(1))

        # Track current sector from command prompt
        prompt_re = re.compile(r"\[(\d+)\]\s*\(\?=Help\)")
        for m in prompt_re.finditer(text):
            self._current_sector = int(m.group(1))

        # Track purchases (cost basis)
        # TODO(TW-1): implement cost basis tracking from haggling sequences

        # Track sells

        # Simple cargo tracking from "OnBoard" column in commerce reports
        onboard_re = re.compile(
            r"(Fuel Ore|Organics|Equipment)\s+(?:Selling|Buying)\s+\d+\s+\d+%\s+(\d+)"
        )
        cargo: list[CargoHold] = []
        for m in onboard_re.finditer(text):
            qty = int(m.group(2))
            if qty > 0:
                commodity = _parse_commodity_type(m.group(1))
                cargo.append(CargoHold(commodity=commodity, quantity=qty, cost_per_unit=0.0))

        if cargo:
            self._cargo = cargo

    def _extract_chat(self, text: str) -> None:
        # Sub-space radio messages
        radio_re = re.compile(
            r"(?:Incoming message on channel|Sub-Space Radio)\s*.*?from\s+(.+?):\s*(.+?)$",
            re.MULTILINE,
        )
        for m in radio_re.finditer(text):
            self._store.add_chat_message(
                ChatMessage(
                    sender=m.group(1).strip(),
                    message=m.group(2).strip(),
                    channel="radio",
                )
            )

        # Fed comm-link messages
        fed_re = re.compile(
            r"Fed Comm-Link.*?from\s+(.+?):\s*(.+?)$",
            re.MULTILINE,
        )
        for m in fed_re.finditer(text):
            self._store.add_chat_message(
                ChatMessage(
                    sender=m.group(1).strip(),
                    message=m.group(2).strip(),
                    channel="fed",
                )
            )

    def _update_player_status(self) -> None:
        if self._current_sector is not None:
            self._store.set_player_status(
                PlayerStatus(
                    sector_id=self._current_sector,
                    turns_remaining=self._turns_remaining or 0,
                    credits=self._credits or 0,
                    cargo=self._cargo,
                    holds_total=self._holds_total,
                    holds_empty=self._holds_empty,
                )
            )


def _parse_commodity_type(name: str) -> CommodityType:
    mapping = {
        "Fuel Ore": CommodityType.FUEL_ORE,
        "Organics": CommodityType.ORGANICS,
        "Equipment": CommodityType.EQUIPMENT,
    }
    return mapping[name]
