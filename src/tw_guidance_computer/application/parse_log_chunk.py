"""Use case: parse a chunk of log text and update game state."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import final

from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.domain.models import (
    CargoHold,
    CargoManifest,
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


@dataclass
class _SyncPoint:
    """Parsed sync point data from <Info> or status bar."""

    sector: int
    turns: int
    holds_total: int
    holds_empty: int
    credits: int
    cargo: CargoManifest = field(default_factory=CargoManifest)


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
        self._cargo: CargoManifest = CargoManifest()
        self._holds_total: int = 0
        self._holds_empty: int = 0

    def execute(self, text: str) -> None:
        """Parse a chunk of log text and persist extracted data.

        Args:
            text: ANSI-stripped log text to parse.
        """
        self._extract_sectors_and_warps(text)
        self._extract_ports(text)
        self._extract_planets(text)
        self._extract_commerce_reports(text)
        # Sync points reset cargo state; track position of last one
        sync_pos = self._extract_sync_points(text)
        self._extract_player_state(text)
        # Only process transactions after the last sync point
        tx_text = text[sync_pos:] if sync_pos > 0 else text
        self._extract_transactions(tx_text)
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

    def _extract_planets(self, text: str) -> None:
        planet_re = re.compile(r"Planets?\s*:\s*\(([A-Z])\)\s*(.+)")
        sector_re = re.compile(r"Sector\s+:\s+(\d+)")

        for m in planet_re.finditer(text):
            planet_class = m.group(1)
            planet_name = m.group(2).strip()

            # Find the sector this planet belongs to
            preceding = text[max(0, m.start() - 300) : m.start()]
            sec_match = list(sector_re.finditer(preceding))
            if not sec_match:
                continue
            sector_id = int(sec_match[-1].group(1))

            self._store.upsert_planet(
                Planet(
                    sector_id=sector_id,
                    name=planet_name,
                    planet_class=planet_class,
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

    def _extract_sync_points(self, text: str) -> int:
        """Parse <Info> block and compact status bar. Returns position of last sync point."""
        last_sync_pos = 0

        # Collect all sync points with their positions, apply in document order
        syncs: list[tuple[int, _SyncPoint]] = []

        # <Info> block
        info_re = re.compile(
            r"<Info>\s*\n"
            r"(?:.*\n)*?"  # skip trader name, rank, corp, ship lines
            r"Current Sector\s*:\s*(\d+)\s*\n"
            r"Turns left\s*:\s*(\d+)\s*\n"
            r"Total Holds\s*:\s*(\d+)\s*-\s*(.+?)\s*\n"
            r"(?:.*\n)*?"  # skip fighters, shields
            r"Credits\s*:\s*([0-9,]+)"
        )
        for m in info_re.finditer(text):
            holds_desc = m.group(4)
            empty_m = re.search(r"Empty=(\d+)", holds_desc)
            syncs.append((m.end(), _SyncPoint(
                sector=int(m.group(1)),
                turns=int(m.group(2)),
                holds_total=int(m.group(3)),
                holds_empty=int(empty_m.group(1)) if empty_m else 0,
                credits=int(m.group(5).replace(",", "")),
                cargo=CargoManifest(holdings=_parse_holds_description(holds_desc)),
            )))

        # Compact status bar
        bar_re = re.compile(
            r"Sect\s+(\d+)"
            r"\s*│\s*Turns\s+([0-9,]+)"
            r"\s*│\s*Creds\s+([0-9,]+)"
            r"\s*│\s*Figs\s+[0-9,]+"
            r"\s*│\s*Shlds\s+[0-9,]+"
            r"\s*│\s*Hlds\s+([0-9,]+)"
            r"\s*│\s*Ore\s+(\d+)"
            r"\s*│\s*Org\s+(\d+)"
            r"\s*│\s*Equ\s+(\d+)"
            r"\s*│\s*Col\s+(\d+)"
        )
        for m in bar_re.finditer(text):
            ore = int(m.group(5))
            org = int(m.group(6))
            equ = int(m.group(7))
            col = int(m.group(8))
            holds_total = int(m.group(4).replace(",", ""))
            bar_cargo: list[CargoHold] = []
            if ore > 0:
                bar_cargo.append(CargoHold(commodity=CommodityType.FUEL_ORE, quantity=ore, cost_per_unit=0.0))
            if org > 0:
                bar_cargo.append(CargoHold(commodity=CommodityType.ORGANICS, quantity=org, cost_per_unit=0.0))
            if equ > 0:
                bar_cargo.append(CargoHold(commodity=CommodityType.EQUIPMENT, quantity=equ, cost_per_unit=0.0))
            syncs.append((m.end(), _SyncPoint(
                sector=int(m.group(1)),
                turns=int(m.group(2).replace(",", "")),
                holds_total=holds_total,
                holds_empty=holds_total - (ore + org + equ + col),
                credits=int(m.group(3).replace(",", "")),
                cargo=CargoManifest(holdings=bar_cargo),
            )))

        # Apply in document order — last one wins
        for pos, data in sorted(syncs):
            self._current_sector = data.sector
            self._turns_remaining = data.turns
            self._holds_total = data.holds_total
            self._holds_empty = data.holds_empty
            self._credits = data.credits
            self._cargo = data.cargo
            last_sync_pos = pos

        return last_sync_pos

    def _extract_player_state(self, text: str) -> None:
        # Track turns — process all turn-related patterns in document order
        turn_patterns = [
            (re.compile(r"(\d+)\s+turns? left"), "set"),
            (re.compile(r"You have\s+(\d+)\s+turns? this Stardate"), "set"),
            (re.compile(r"You don't have any turns left"), "zero"),
            (re.compile(r"You recover\s+(\d+)\s+of your turns"), "add"),
        ]
        # Collect all matches with positions
        turn_events: list[tuple[int, str, int]] = []
        for pattern, action in turn_patterns:
            for m in pattern.finditer(text):
                if action == "zero":
                    turn_events.append((m.start(), action, 0))
                elif action == "add":
                    turn_events.append((m.start(), action, int(m.group(1))))
                else:
                    turn_events.append((m.start(), action, int(m.group(1))))
        # Apply in document order
        for _, action, value in sorted(turn_events):
            if action == "set" or action == "zero":
                self._turns_remaining = value
            elif action == "add":
                self._turns_remaining = (self._turns_remaining or 0) + value

        # Track credits
        for m in re.finditer(r"You have\s+([0-9,]+)\s+credits", text):
            self._credits = int(m.group(1).replace(",", ""))

        # Track empty holds
        for m in re.finditer(r"You have\s+[0-9,]+\s+credits and\s+(\d+)\s+empty cargo holds", text):
            self._holds_empty = int(m.group(1))

        # Track current sector from command prompt
        for m in re.finditer(r"\[(\d+)\]\s*\(\?=Help\)", text):
            self._current_sector = int(m.group(1))

    def _extract_transactions(self, text: str) -> None:
        """Parse buy/sell transactions for cargo tracking with cost basis."""
        # Match: "How many holds of X do you want to buy/sell [N]?"
        # followed by "Agreed, N units." within a short window (no intervening prompts)
        prompt_re = re.compile(
            r"How many holds of (Fuel Ore|Organics|Equipment) do you want to (buy|sell) \[(\d+)\]\?"
        )

        for m in prompt_re.finditer(text):
            # Only look for "Agreed" within 100 chars — if it's not there, trade was declined
            window = text[m.end() : m.end() + 100]
            agreed_m = re.search(r"Agreed,\s*(\d+)\s*units?", window)
            if not agreed_m:
                continue

            commodity = _parse_commodity_type(m.group(1))
            direction = m.group(2)
            quantity = int(agreed_m.group(1))

            # Find the final accepted price after "Agreed"
            after_agreed = text[m.end() + agreed_m.end() : m.end() + agreed_m.end() + 500]
            price = _extract_final_price(after_agreed, direction)

            if direction == "buy":
                cost_per_unit = price / quantity if price > 0 else 0.0
                self._cargo = self._cargo.add(commodity, quantity, cost_per_unit)
            else:
                self._cargo = self._cargo.remove(commodity, quantity)

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
                    cargo=self._cargo.holdings,
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


def _parse_holds_description(desc: str) -> list[CargoHold]:
    """Parse holds description like 'Fuel Ore=20 Empty=48' into cargo list."""
    cargo: list[CargoHold] = []
    for name, ctype in [
        ("Fuel Ore", CommodityType.FUEL_ORE),
        ("Organics", CommodityType.ORGANICS),
        ("Equipment", CommodityType.EQUIPMENT),
    ]:
        m = re.search(rf"{name}=(\d+)", desc)
        if m:
            cargo.append(CargoHold(commodity=ctype, quantity=int(m.group(1)), cost_per_unit=0.0))
    return cargo


def _extract_final_price(text_after_agreed: str, direction: str) -> float:
    """Extract the final accepted price from haggling text.

    Looks for the last price mentioned before an acceptance message.
    """
    # Price offers: "We'll sell/buy them for N credits." or "Our final offer is N credits."
    price_re = re.compile(r"(?:for|is)\s+([0-9,]+)\s+credits")
    # Acceptance messages that end the haggling
    accept_re = re.compile(
        r"(?:Very well|Agreed!|You are a shrewd|SOLD!|Cheapskate|Oh well|"
        r"If only more honest|You insult my intelligence)"
    )

    accept_m = accept_re.search(text_after_agreed)
    if not accept_m:
        return 0.0

    # Find the last price before the acceptance
    search_region = text_after_agreed[: accept_m.start()]
    prices = list(price_re.finditer(search_region))
    if prices:
        return float(prices[-1].group(1).replace(",", ""))
    return 0.0
