"""Composition root — centralizes all construction logic."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import final

from tw_guidance_computer.adapters.inbound.cli_commands import CliAdapter
from tw_guidance_computer.adapters.outbound.ini_profile_store import IniProfileStore
from tw_guidance_computer.adapters.outbound.log_reader import TailLogReader
from tw_guidance_computer.adapters.outbound.sqlite_store import SqliteGameStateStore
from tw_guidance_computer.application.create_profile import CreateProfile
from tw_guidance_computer.application.find_nearby_ports import FindNearbyPorts
from tw_guidance_computer.application.find_nearest_pair import FindNearestPair
from tw_guidance_computer.application.find_path import FindPath
from tw_guidance_computer.application.find_safe_harbor import FindSafeHarbor
from tw_guidance_computer.application.find_sell_locations import FindSellLocations
from tw_guidance_computer.application.find_trade_pairs import FindTradePairs
from tw_guidance_computer.application.get_database_summary import GetDatabaseSummary
from tw_guidance_computer.application.get_player_status import GetPlayerStatus
from tw_guidance_computer.application.get_recent_chat import GetRecentChat
from tw_guidance_computer.application.get_sector_info import GetSectorInfo
from tw_guidance_computer.application.list_ports import ListPorts
from tw_guidance_computer.application.list_profiles import ListProfiles
from tw_guidance_computer.application.parse_log_chunk import ParseLogChunk
from tw_guidance_computer.application.render_sector_art import RenderSectorArt
from tw_guidance_computer.application.search_ports import SearchPorts
from tw_guidance_computer.application.use_cases import UseCases
from tw_guidance_computer.domain.exceptions import DatabaseNotFoundError
from tw_guidance_computer.domain.models import TurnThresholds


def _default_config_path() -> Path:
    """Return the default config file path."""
    return Path.home() / ".config" / "tw-guidance-computer" / "config.ini"


def _resolve_config(
    profile_name: str | None, config_path: Path | None = None
) -> tuple[Path, TurnThresholds, str]:
    """Resolve database path, turn thresholds, and effective profile name.

    Args:
        profile_name: Profile to use, or None for the configured default.
        config_path: Override config file location (for testing).

    Returns:
        Tuple of (db_path, turn_thresholds, effective_profile_name).

    Raises:
        ConfigError: If the config file is malformed.
        ProfileNotFoundError: If the requested profile doesn't exist.
        ValidationError: If threshold values are invalid.
    """
    store = IniProfileStore(config_path or _default_config_path())
    store.ensure_config_exists()
    effective_name = profile_name or store.list_profiles().default_name
    profile = store.get_profile(effective_name)
    db_path = Path(profile.db_path)

    yellow = int(store.get_config_value(effective_name, "turn_warning_yellow", "200"))
    red = int(store.get_config_value(effective_name, "turn_warning_red", "100"))
    alert = int(store.get_config_value(effective_name, "turn_alert_threshold", "50"))
    thresholds = TurnThresholds(yellow=yellow, red=red, alert=alert)

    return db_path, thresholds, effective_name


@final
class AppContext:
    """Holds the fully wired application graph."""

    def __init__(
        self,
        *,
        profile_name: str | None = None,
        config_path: Path | None = None,
        log_path: Path | None = None,
        require_existing_db: bool = False,
    ) -> None:
        """Build the dependency graph.

        Resolves config internally from the profile name.

        Args:
            profile_name: Profile to use, or None for the configured default.
            config_path: Override config file location (for testing).
            log_path: Path to the session log file (None for CLI-only).
            require_existing_db: If True, raise DatabaseNotFoundError when DB missing.

        Raises:
            ConfigError: If the config file is malformed.
            ProfileNotFoundError: If the requested profile doesn't exist.
            ValidationError: If threshold values are invalid.
            DatabaseNotFoundError: If require_existing_db and DB doesn't exist.
        """
        db_path, thresholds, _ = _resolve_config(profile_name, config_path)

        if require_existing_db and not db_path.exists():
            raise DatabaseNotFoundError(
                f"No database found at {db_path}. Run tw-hud first to populate it."
            )

        self.thresholds = thresholds

        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.store = SqliteGameStateStore(db_path)

        find_trade_pairs = FindTradePairs(self.store)
        self.use_cases = UseCases(
            find_trade_pairs=find_trade_pairs,
            find_nearest_pair=FindNearestPair(self.store, find_trade_pairs),
            find_nearby_ports=FindNearbyPorts(self.store),
            find_path=FindPath(self.store),
            find_sell_locations=FindSellLocations(self.store),
            search_ports=SearchPorts(self.store),
            render_sector_art=RenderSectorArt(self.store),
            parse_log_chunk=ParseLogChunk(self.store),
            get_player_status=GetPlayerStatus(self.store),
            get_sector_info=GetSectorInfo(self.store),
            list_ports=ListPorts(self.store),
            get_recent_chat=GetRecentChat(self.store),
            get_database_summary=GetDatabaseSummary(self.store),
            find_safe_harbor=FindSafeHarbor(self.store),
        )

        self.reader: TailLogReader | None = None
        if log_path is not None:
            self.reader = TailLogReader(log_path)

    def close(self) -> None:
        """Clean up resources."""
        if self.reader is not None:
            self.reader.close()
        self.store.close()


def build_profile_use_cases(
    config_path: Path | None = None,
) -> tuple[CreateProfile, ListProfiles]:
    """Build profile-related use cases for CLI commands.

    Args:
        config_path: Override config file location (for testing).

    Returns:
        Tuple of (CreateProfile, ListProfiles).
    """
    store = IniProfileStore(config_path or _default_config_path())
    store.ensure_config_exists()
    return CreateProfile(store), ListProfiles(store)


def build_cli(config_path: Path | None = None) -> CliAdapter:
    """Build the CLI adapter with all dependencies.

    Args:
        config_path: Override config file location (for testing).

    Returns:
        A fully wired CliAdapter ready to run.
    """
    create, list_profiles = build_profile_use_cases(config_path)

    def game_context_factory(
        profile_name: str | None,
    ) -> tuple[UseCases, Callable[[], None]]:
        ctx = AppContext(
            profile_name=profile_name,
            config_path=config_path,
            require_existing_db=True,
        )
        return ctx.use_cases, ctx.close

    return CliAdapter(
        create_profile=create,
        list_profiles=list_profiles,
        game_context_factory=game_context_factory,
    )
