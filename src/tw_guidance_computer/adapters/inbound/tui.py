"""Curses-based TUI HUD for real-time game state display."""

from __future__ import annotations

import argparse
import curses
import re
import signal
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, final

from tw_guidance_computer.adapters.inbound.alert_overlay import format_alert_overlay
from tw_guidance_computer.adapters.inbound.sync_modal import format_sync_modal
from tw_guidance_computer.application.ports.log_reader import LogReader
from tw_guidance_computer.domain.exceptions import GuidanceError, ProfileExistsError
from tw_guidance_computer.domain.models import ArtCell, PlayerStatus, SafeHarborRoute, TurnThresholds

if TYPE_CHECKING:
    from tw_guidance_computer.application.create_profile import CreateProfile
    from tw_guidance_computer.application.sync_intel_worker import SyncIntelWorker
    from tw_guidance_computer.application.use_cases import UseCases

HudContextFactory = Callable[
    [str | None, Path, bool],
    tuple["UseCases", LogReader, TurnThresholds, "SyncIntelWorker | None", Callable[[], None]],
]

_ANSI_COLOR_RE = re.compile(r"\033\[38;5;(\d+)m")
_TWO_COLUMN_HEIGHT = 12
_MIN_ART_HEIGHT = 6


@final
class HudDisplay:
    """Curses TUI that shows real-time game state."""

    def __init__(
        self,
        *,
        create_profile: CreateProfile,
        hud_context_factory: HudContextFactory,
    ) -> None:
        """Initialize the HUD adapter.

        Args:
            create_profile: Use case for creating profiles.
            hud_context_factory: Factory that builds the game context from parsed args.
        """
        self._create_profile = create_profile
        self._hud_context_factory = hud_context_factory
        self._sync_worker: SyncIntelWorker | None = None
        self._reader: LogReader
        self._uc: UseCases
        self._thresholds: TurnThresholds = TurnThresholds()
        self._running = True
        self._shutting_down = False
        self._sigint_count = 0
        self._pairs_mode = "best"  # "best" or "nearest"
        self._art_cache: list[list[ArtCell]] | None = None
        self._art_sector: int | None = None
        self._art_size: tuple[int, int] = (0, 0)
        self._color_pair_map: dict[int, int] = {}
        self._next_pair_id = 10
        self._safe_harbor_cache: SafeHarborRoute | None = None
        self._safe_harbor_sector: int | None = None

    def run(self, argv: list[str] | None = None) -> None:
        """Parse arguments, build context, and start the HUD display loop.

        Args:
            argv: Command-line arguments (defaults to sys.argv[1:]).
        """
        args = self._build_parser().parse_args(argv)

        if not args.logfile.exists():
            print(f"Error: log file not found: {args.logfile}", file=sys.stderr)
            sys.exit(1)

        if args.create and args.profile:
            try:
                profile = self._create_profile.execute(args.profile)
                print(f"Note: Created profile '{profile.name}' (db: {profile.db_path})", file=sys.stderr)
            except ProfileExistsError:
                pass

        uc, reader, thresholds, sync_worker, close_fn = self._hud_context_factory(
            args.profile, args.logfile, args.parse_existing,
        )
        self._uc = uc
        self._reader = reader
        self._thresholds = thresholds
        self._sync_worker = sync_worker
        try:
            curses.wrapper(self._main_loop)
        except GuidanceError as e:
            print(f"Error: {e}", file=sys.stderr)
        finally:
            close_fn()

    def _build_parser(self) -> argparse.ArgumentParser:
        """Build the argparse parser for HUD arguments."""
        parser = argparse.ArgumentParser(description="TW2002 Guidance Computer — real-time HUD")
        parser.add_argument("logfile", type=Path, help="Path to the script session log file")
        parser.add_argument(
            "-p", "--profile", type=str, default=None,
            help="Profile to use (default: configured default)",
        )
        parser.add_argument(
            "--create", action="store_true",
            help="Create the profile if it doesn't exist",
        )
        parser.add_argument(
            "--parse-existing", action="store_true",
            help="Parse the entire existing log before starting the HUD",
        )
        return parser

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

        # SIGINT handling
        def _sigint_handler(signum: int, frame: object) -> None:
            self._sigint_count += 1
            if self._sigint_count == 1:
                self._initiate_shutdown()
            else:
                if self._sync_worker is not None:
                    self._sync_worker.request_stop()
                self._running = False

        signal.signal(signal.SIGINT, _sigint_handler)

        # Start background sync worker if configured
        if self._sync_worker is not None:
            t = threading.Thread(target=self._sync_worker.run, daemon=True)
            t.start()

        error_msg: str | None = None

        while self._running:
            try:
                # Check for new log data
                new_text = self._reader.read_new()
                if new_text:
                    self._uc.parse_log_chunk.execute(new_text)
                error_msg = None
            except GuidanceError as e:
                error_msg = str(e)

            # Check for quit key
            key = stdscr.getch()
            if key == ord("q") and not self._shutting_down:
                self._initiate_shutdown()
                if self._sync_worker is None:
                    break
            elif key == ord("t") and not self._shutting_down:
                self._pairs_mode = "nearest" if self._pairs_mode == "best" else "best"

            # Check shutdown completion
            if self._shutting_down and self._sync_worker is not None:
                status = self._sync_worker.get_status().shutdown_status
                if status == "Done.":
                    self._render_shutdown_frame(stdscr, status)
                    stdscr.refresh()
                    time.sleep(0.5)
                    break
                elif status is not None and status.startswith("Push failed:"):
                    self._render_shutdown_frame(stdscr, status)
                    stdscr.refresh()
                    time.sleep(1.5)
                    break

            # Render
            stdscr.erase()
            try:
                if self._shutting_down:
                    self._render_header(stdscr, stdscr.getmaxyx()[1], self._uc.get_player_status.execute())
                    self._render_sync_modal(stdscr)
                else:
                    self._render(stdscr)
            except GuidanceError as e:
                error_msg = str(e)
            if error_msg:
                self._safe_addstr(stdscr, stdscr.getmaxyx()[0] - 2, 0, f" ⚠ {error_msg}", curses.color_pair(4))
            stdscr.refresh()
            time.sleep(0.25)

    def _initiate_shutdown(self) -> None:
        """Begin graceful shutdown sequence."""
        if self._sync_worker is not None:
            self._shutting_down = True
            self._sync_worker.request_shutdown()
        else:
            self._running = False

    def _render_shutdown_frame(self, stdscr: curses.window, status: str) -> None:
        """Render a single frame showing the shutdown modal."""
        stdscr.erase()
        self._render_header(stdscr, stdscr.getmaxyx()[1], self._uc.get_player_status.execute())
        self._render_sync_modal(stdscr)

    def _render_sync_modal(self, stdscr: curses.window) -> None:
        """Render the shutdown sync modal overlay centered on screen."""
        max_y, max_x = stdscr.getmaxyx()
        status = self._sync_worker.get_status().shutdown_status if self._sync_worker else None
        lines = format_sync_modal(status)

        title = " Syncing Intel "
        content_width = max(len(title) + 4, max(len(line) for line in lines) + 4) if lines else len(title) + 4
        box_width = min(max(content_width + 2, 39), max_x - 4)
        box_height = 5

        start_y = max(0, (max_y - box_height) // 2)
        start_x = max(0, (max_x - box_width) // 2)

        attr = curses.color_pair(2) | curses.A_BOLD

        pad_left = (box_width - 2 - len(title)) // 2
        pad_right = box_width - 2 - len(title) - pad_left
        top_border = "╔" + "═" * pad_left + title + "═" * pad_right + "╗"
        bot_border = "╚" + "═" * (box_width - 2) + "╝"

        self._safe_addstr(stdscr, start_y, start_x, top_border, attr)
        for i in range(1, box_height - 1):
            self._safe_addstr(stdscr, start_y + i, start_x, "║" + " " * (box_width - 2) + "║", attr)
        self._safe_addstr(stdscr, start_y + box_height - 1, start_x, bot_border, attr)

        # Status line in center row
        if lines:
            status_text = lines[0][:box_width - 6]
            if status_text.startswith("Push failed:"):
                status_attr = curses.color_pair(4) | curses.A_BOLD
            else:
                status_attr = curses.color_pair(1)
            self._safe_addstr(stdscr, start_y + 2, start_x + 3, status_text, status_attr)

    def _render(self, stdscr: curses.window) -> None:
        max_y, max_x = stdscr.getmaxyx()
        status = self._uc.get_player_status.execute()

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

        # Right panel: chat (constrained to two-column area)
        two_col_bottom = 2 + _TWO_COLUMN_HEIGHT
        art_top = two_col_bottom
        art_bottom = max_y - 1  # footer row
        art_height = art_bottom - art_top

        # If art panel won't render, let COMMS use full height
        chat_bottom = two_col_bottom if art_height >= _MIN_ART_HEIGHT else max_y - 1
        self._render_chat(stdscr, right_row, panel_width, max_x, chat_bottom)

        # Art panel (below two-column area, above footer)
        if art_height >= _MIN_ART_HEIGHT:
            self._render_art_panel(stdscr, art_top, max_x, art_height, status)

        # Footer
        self._safe_addstr(stdscr, max_y - 1, 0, " [q] quit  [t] toggle pairs ", curses.A_REVERSE)

        # Safe harbor overlay (only if not shutting down — shutdown modal takes priority)
        if not self._shutting_down and status and status.turns_remaining < self._thresholds.alert:
            if self._safe_harbor_sector != status.sector_id:
                self._safe_harbor_cache = self._uc.find_safe_harbor.execute(status.sector_id)
                self._safe_harbor_sector = status.sector_id
            self._render_alert_overlay(stdscr, max_y, max_x, status.turns_remaining, status.sector_id)
        elif self._safe_harbor_cache is not None:
            self._safe_harbor_cache = None
            self._safe_harbor_sector = None

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
            if status.turns_remaining < self._thresholds.alert:
                turns_attr = curses.color_pair(4) | curses.A_BOLD
            elif status.turns_remaining < self._thresholds.red:
                turns_attr = curses.color_pair(4) | curses.A_BOLD
            elif status.turns_remaining < self._thresholds.yellow:
                turns_attr = curses.color_pair(3) | curses.A_BOLD | curses.A_REVERSE
            else:
                turns_attr = curses.color_pair(3) | curses.A_BOLD
            self._safe_addstr(stdscr, 1, col, turns, turns_attr)
            col += len(turns)
            self._safe_addstr(stdscr, 1, col, "  │  ", curses.color_pair(3))
            col += 5
            self._safe_addstr(stdscr, 1, col, credits, curses.color_pair(3) | curses.A_BOLD)
            col += len(credits)

            # Intel error indicator
            if self._sync_worker is not None:
                last_error = self._sync_worker.get_status().last_error
                if last_error:
                    err_attr = curses.color_pair(4) | curses.A_BOLD | curses.A_REVERSE | curses.A_BLINK
                    sep = "  │  "
                    if max_x >= 90:
                        indicator = f"! Intel {last_error}"
                    else:
                        indicator = f"! {last_error}"
                    if col + len(sep) + len(indicator) < max_x:
                        self._safe_addstr(stdscr, 1, col, sep, curses.color_pair(3))
                        col += len(sep)
                        self._safe_addstr(stdscr, 1, col, indicator, err_attr)
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
        recommendations = self._uc.find_sell_locations.execute(status.sector_id, carrying, max_hops=8)

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
        pairs = self._uc.find_trade_pairs.execute(min_complementary=2)
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
        status = self._uc.get_player_status.execute()
        if not status:
            self._safe_addstr(stdscr, row, col + 1, "No position known", curses.color_pair(1))
            return row + 2

        results = self._uc.find_nearest_pair.execute(status.sector_id, limit=6)
        if not results:
            self._safe_addstr(stdscr, row, col + 1, "None found yet", curses.color_pair(1))
            return row + 2

        for nearest in results:
            pair = nearest.pair
            line = (
                f" {nearest.hops}h [{pair.sector_a}]\u2194[{pair.sector_b}]"
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

        messages = self._uc.get_recent_chat.execute(limit=max_y - row - 2)
        if not messages:
            self._safe_addstr(stdscr, row, col + 1, "No messages", curses.color_pair(1))
            return

        for msg in reversed(messages):
            if row >= max_y - 1:
                break
            line = f" [{msg.channel[0]}] {msg.sender}: {msg.message}"
            self._safe_addstr(stdscr, row, col, line[:width], curses.color_pair(5))
            row += 1

    def _render_art_panel(
        self, stdscr: curses.window, top: int, width: int, height: int, status: PlayerStatus | None
    ) -> None:
        current_sector = status.sector_id if status else None
        size = (width, height)

        # Regenerate art on sector change or resize
        if self._art_cache is None or self._art_sector != current_sector or self._art_size != size:
            if current_sector is not None:
                self._art_cache = self._uc.render_sector_art.execute(current_sector, width, height)
            else:
                self._art_cache = None
            self._art_sector = current_sector
            self._art_size = size

        if self._art_cache is None:
            return

        # Separator line
        self._safe_addstr(stdscr, top, 0, "─" * width, curses.color_pair(2))

        for y, row in enumerate(self._art_cache):
            screen_y = top + 1 + y
            if screen_y >= top + height:
                break
            for x, cell in enumerate(row):
                if x >= width - 1:
                    break
                if cell.char == " ":
                    continue
                attr = self._get_color_pair(cell.color)
                try:
                    stdscr.addstr(screen_y, x, cell.char, attr)
                except curses.error:
                    pass

    def _render_alert_overlay(self, stdscr: curses.window, max_y: int, max_x: int, turns: int, sector: int) -> None:
        """Render the RED ALERT overlay centered on screen."""
        lines = format_alert_overlay(self._safe_harbor_cache, turns)

        content_width = max(len(line) for line in lines) + 4
        box_width = min(content_width + 4, max_x - 4)
        box_height = len(lines) + 4

        start_y = max(0, (max_y - box_height) // 2)
        start_x = max(0, (max_x - box_width) // 2)

        attr = curses.color_pair(4) | curses.A_BOLD

        header = " RED ALERT "
        pad_left = (box_width - 2 - len(header)) // 2
        pad_right = (box_width - 2 - len(header) + 1) // 2
        top_border = "╔" + "═" * pad_left + header + "═" * pad_right + "╗"
        bot_border = "╚" + "═" * (box_width - 2) + "╝"

        self._safe_addstr(stdscr, start_y, start_x, top_border, attr)
        for i in range(1, box_height - 1):
            self._safe_addstr(stdscr, start_y + i, start_x, "║" + " " * (box_width - 2) + "║", attr)
        self._safe_addstr(stdscr, start_y + box_height - 1, start_x, bot_border, attr)

        content_start_y = start_y + 2
        for i, line in enumerate(lines):
            if content_start_y + i >= start_y + box_height - 1:
                break
            self._safe_addstr(stdscr, content_start_y + i, start_x + 3, line[: box_width - 6], attr)

    def _get_color_pair(self, ansi_escape: str) -> int:
        if not ansi_escape:
            return 0
        m = _ANSI_COLOR_RE.match(ansi_escape)
        if not m:
            return 0
        color_num = int(m.group(1))
        if color_num not in self._color_pair_map:
            pair_id = self._next_pair_id
            self._next_pair_id += 1
            try:
                curses.init_pair(pair_id, color_num, -1)
            except curses.error:
                return 0
            self._color_pair_map[color_num] = pair_id
        return curses.color_pair(self._color_pair_map[color_num])

    def _safe_addstr(self, stdscr: curses.window, y: int, x: int, text: str, attr: int = 0) -> None:
        max_y, max_x = stdscr.getmaxyx()
        if y >= max_y or x >= max_x:
            return
        try:
            stdscr.addstr(y, x, text[: max_x - x - 1], attr)
        except curses.error:
            pass
