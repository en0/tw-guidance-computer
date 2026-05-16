"""Curses-based TUI HUD for real-time game state display."""

from __future__ import annotations

import curses
import time
from typing import final

from tw_guidance_computer.application.find_nearest_pair import FindNearestPair
from tw_guidance_computer.application.find_sell_locations import FindSellLocations
from tw_guidance_computer.application.find_trade_pairs import FindTradePairs
from tw_guidance_computer.application.parse_log_chunk import ParseLogChunk
from tw_guidance_computer.application.ports.game_state_store import GameStateStore
from tw_guidance_computer.application.ports.log_reader import LogReader
from tw_guidance_computer.domain.models import PlayerStatus


@final
class HudDisplay:
    """Curses TUI that shows real-time game state."""

    def __init__(
        self,
        store: GameStateStore,
        reader: LogReader,
        parser: ParseLogChunk,
    ) -> None:
        """Initialize the HUD.

        Args:
            store: Game state store for queries.
            reader: Log reader for new data.
            parser: Parser to process log chunks.
        """
        self._store = store
        self._reader = reader
        self._parser = parser
        self._find_pairs = FindTradePairs(store)
        self._find_nearest = FindNearestPair(store)
        self._find_sell = FindSellLocations(store)
        self._running = True
        self._pairs_mode = "best"  # "best" or "nearest"

    def run(self) -> None:
        """Start the HUD display loop."""
        curses.wrapper(self._main_loop)

    def _main_loop(self, stdscr: curses.window) -> None:
        curses.curs_set(0)
        stdscr.nodelay(True)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_CYAN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_RED, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)

        while self._running:
            # Check for new log data
            new_text = self._reader.read_new()
            if new_text:
                self._parser.execute(new_text)

            # Check for quit key
            key = stdscr.getch()
            if key == ord("q"):
                self._running = False
                break
            elif key == ord("t"):
                self._pairs_mode = "nearest" if self._pairs_mode == "best" else "best"

            # Render
            stdscr.erase()
            self._render(stdscr)
            stdscr.refresh()
            time.sleep(0.25)

    def _render(self, stdscr: curses.window) -> None:
        max_y, max_x = stdscr.getmaxyx()
        status = self._store.get_player_status()

        # Header
        self._render_header(stdscr, max_x, status)

        # Layout: left panel (status + inventory), right panel (trade advisor + chat)
        panel_width = max_x // 2
        row = 2

        # Left panel: inventory
        row = self._render_inventory(stdscr, row, panel_width, status)

        # Left panel: sell recommendations
        row = self._render_sell_advice(stdscr, row, panel_width, status)

        # Right panel: trade pairs
        right_row = 2
        right_row = self._render_trade_pairs(stdscr, right_row, panel_width, max_x)

        # Right panel: chat
        self._render_chat(stdscr, right_row, panel_width, max_x, max_y)

        # Footer
        self._safe_addstr(stdscr, max_y - 1, 0, " [q] quit  [t] toggle pairs ", curses.A_REVERSE)

    def _render_header(self, stdscr: curses.window, max_x: int, status: PlayerStatus | None) -> None:
        header = " TW2002 GUIDANCE COMPUTER "
        self._safe_addstr(stdscr, 0, 0, "═" * max_x, curses.color_pair(2))
        self._safe_addstr(stdscr, 0, (max_x - len(header)) // 2, header, curses.color_pair(2) | curses.A_BOLD)

        if status:
            loc = f"Sector: {status.sector_id}"
            turns = f"Turns: {status.turns_remaining}"
            credits = f"Credits: {status.credits:,}"
            # Render sector and separator
            col = 1
            self._safe_addstr(stdscr, 1, col, loc, curses.color_pair(3) | curses.A_BOLD)
            col += len(loc)
            self._safe_addstr(stdscr, 1, col, "  │  ", curses.color_pair(3))
            col += 5
            # Turns with color warning
            if status.turns_remaining < 50:
                turns_attr = curses.color_pair(4) | curses.A_BOLD  # red
            elif status.turns_remaining < 100:
                turns_attr = curses.color_pair(3) | curses.A_BOLD | curses.A_REVERSE  # yellow inverse
            else:
                turns_attr = curses.color_pair(3) | curses.A_BOLD
            self._safe_addstr(stdscr, 1, col, turns, turns_attr)
            col += len(turns)
            self._safe_addstr(stdscr, 1, col, "  │  ", curses.color_pair(3))
            col += 5
            self._safe_addstr(stdscr, 1, col, credits, curses.color_pair(3) | curses.A_BOLD)
        else:
            self._safe_addstr(stdscr, 1, 0, " Waiting for data...", curses.color_pair(3))

    def _render_inventory(self, stdscr: curses.window, row: int, width: int, status: PlayerStatus | None) -> int:
        self._safe_addstr(stdscr, row, 0, "─── CARGO ───", curses.color_pair(2))
        row += 1

        if not status or not status.cargo:
            self._safe_addstr(stdscr, row, 1, "Empty", curses.color_pair(1))
            row += 1
        else:
            total_investment = 0.0
            for hold in status.cargo:
                cost_str = f"@ {hold.cost_per_unit:.1f}/u" if hold.cost_per_unit > 0 else ""
                line = f" {hold.commodity.value:<10} x{hold.quantity:>3} {cost_str}"
                self._safe_addstr(stdscr, row, 0, line, curses.color_pair(1))
                total_investment += hold.total_cost
                row += 1
            if total_investment > 0:
                self._safe_addstr(stdscr, row, 1, f"Invested: {total_investment:,.0f} cr", curses.color_pair(3))
                row += 1

        if status:
            self._safe_addstr(stdscr, row, 1, f"Holds: {status.holds_empty} empty", curses.color_pair(1))
            row += 1

        row += 1
        return row

    def _render_sell_advice(self, stdscr: curses.window, row: int, width: int, status: PlayerStatus | None) -> int:
        self._safe_addstr(stdscr, row, 0, "─── SELL NEARBY ───", curses.color_pair(2))
        row += 1

        if not status or not status.cargo:
            self._safe_addstr(stdscr, row, 1, "Nothing to sell", curses.color_pair(1))
            return row + 2

        carrying = [h.commodity for h in status.cargo]
        recommendations = self._find_sell.execute(status.sector_id, carrying, max_hops=8)

        if not recommendations:
            self._safe_addstr(stdscr, row, 1, "No known buyers nearby", curses.color_pair(4))
            return row + 2

        for rec in recommendations[:5]:
            commodities = ", ".join(c.value[0] for c in rec.commodities_accepted)
            line = f" [{rec.sector_id}] {rec.port_name} ({rec.hops}h) buys: {commodities}"
            self._safe_addstr(stdscr, row, 0, line[:width - 1], curses.color_pair(1))
            row += 1

        row += 1
        return row

    def _render_trade_pairs(self, stdscr: curses.window, row: int, left_width: int, max_x: int) -> int:
        col = left_width + 1
        width = max_x - col - 1
        if self._pairs_mode == "best":
            title = "─── BEST PAIRS [t=nearest] ───"
        else:
            title = "─── NEAREST PAIRS [t=best] ───"
        self._safe_addstr(stdscr, row, col, title, curses.color_pair(2))
        row += 1

        if self._pairs_mode == "nearest":
            return self._render_nearest_pairs(stdscr, row, col, width)
        return self._render_best_pairs(stdscr, row, col, width)

    def _render_best_pairs(self, stdscr: curses.window, row: int, col: int, width: int) -> int:
        pairs = self._find_pairs.execute(min_complementary=2)
        if not pairs:
            self._safe_addstr(stdscr, row, col + 1, "None found yet", curses.color_pair(1))
            return row + 2

        for pair in pairs[:6]:
            line = (
                f" [{pair.sector_a}]\u2194[{pair.sector_b}]"
                f" {pair.complementary_count}/3 {pair.port_a_type}|{pair.port_b_type}"
            )
            self._safe_addstr(stdscr, row, col, line[:width], curses.color_pair(1))
            row += 1

        row += 1
        return row

    def _render_nearest_pairs(self, stdscr: curses.window, row: int, col: int, width: int) -> int:
        status = self._store.get_player_status()
        if not status:
            self._safe_addstr(stdscr, row, col + 1, "No position known", curses.color_pair(1))
            return row + 2

        results = self._find_nearest.execute(status.sector_id, limit=6)
        if not results:
            self._safe_addstr(stdscr, row, col + 1, "None found yet", curses.color_pair(1))
            return row + 2

        for hops, pair in results:
            line = (
                f" {hops}h [{pair.sector_a}]\u2194[{pair.sector_b}]"
                f" {pair.complementary_count}/3 {pair.port_a_type}|{pair.port_b_type}"
            )
            self._safe_addstr(stdscr, row, col, line[:width], curses.color_pair(1))
            row += 1

        row += 1
        return row

    def _render_chat(self, stdscr: curses.window, row: int, left_width: int, max_x: int, max_y: int) -> None:
        col = left_width + 1
        width = max_x - col - 1
        self._safe_addstr(stdscr, row, col, "─── COMMS ───", curses.color_pair(5))
        row += 1

        messages = self._store.get_recent_chat(limit=max_y - row - 2)
        if not messages:
            self._safe_addstr(stdscr, row, col + 1, "No messages", curses.color_pair(1))
            return

        for msg in reversed(messages):
            if row >= max_y - 1:
                break
            line = f" [{msg.channel[0]}] {msg.sender}: {msg.message}"
            self._safe_addstr(stdscr, row, col, line[:width], curses.color_pair(5))
            row += 1

    def _safe_addstr(self, stdscr: curses.window, y: int, x: int, text: str, attr: int = 0) -> None:
        max_y, max_x = stdscr.getmaxyx()
        if y >= max_y or x >= max_x:
            return
        try:
            stdscr.addstr(y, x, text[: max_x - x - 1], attr)
        except curses.error:
            pass
