"""Composition root — centralizes all construction logic."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from tw_guidance_computer.adapters.outbound.ini_profile_store import IniProfileStore
    from tw_guidance_computer.application.create_profile import CreateProfile
    from tw_guidance_computer.application.list_profiles import ListProfiles

from tw_guidance_computer.adapters.outbound.log_reader import TailLogReader
from tw_guidance_computer.adapters.outbound.sqlite_store import SqliteGameStateStore
from tw_guidance_computer.application.find_nearby_ports import FindNearbyPorts
from tw_guidance_computer.application.find_nearest_pair import FindNearestPair
from tw_guidance_computer.application.find_path import FindPath
from tw_guidance_computer.application.find_sell_locations import FindSellLocations
from tw_guidance_computer.application.find_trade_pairs import FindTradePairs
from tw_guidance_computer.application.get_database_summary import GetDatabaseSummary
from tw_guidance_computer.application.get_player_status import GetPlayerStatus
from tw_guidance_computer.application.get_recent_chat import GetRecentChat
from tw_guidance_computer.application.get_sector_info import GetSectorInfo
from tw_guidance_computer.application.list_ports import ListPorts
from tw_guidance_computer.application.parse_log_chunk import ParseLogChunk
from tw_guidance_computer.application.render_sector_art import RenderSectorArt
from tw_guidance_computer.application.search_ports import SearchPorts
from tw_guidance_computer.application.use_cases import UseCases


@final
class AppContext:
    """Holds the fully wired application graph."""

    def __init__(self, db_path: Path, log_path: Path | None = None) -> None:
        """Build the dependency graph.

        Args:
            db_path: Path to the SQLite database.
            log_path: Path to the session log file (None for CLI-only).
        """
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
        )

        self.reader: TailLogReader | None = None
        if log_path is not None:
            self.reader = TailLogReader(log_path)

    def close(self) -> None:
        """Clean up resources."""
        if self.reader is not None:
            self.reader.close()
        self.store.close()


def default_config_path() -> Path:
    """Return the default config file path."""
    return Path.home() / ".config" / "tw-guidance-computer" / "config.ini"


def resolve_db_path(profile_name: str | None, config_path: Path | None = None) -> Path:
    """Resolve the database path for the given profile.

    Args:
        profile_name: Profile to use, or None for the configured default.
        config_path: Override config file location (for testing).

    Returns:
        Resolved database path.

    Raises:
        ConfigError: If the config file is malformed.
        ProfileNotFoundError: If the requested profile doesn't exist.
    """
    from tw_guidance_computer.adapters.outbound.ini_profile_store import IniProfileStore

    store = IniProfileStore(config_path or default_config_path())
    store.ensure_config_exists()
    effective_name = profile_name or store.list_profiles().default_name
    profile = store.get_profile(effective_name)
    return Path(profile.db_path)


def build_profile_use_cases(
    config_path: Path | None = None,
) -> tuple[IniProfileStore, CreateProfile, ListProfiles]:
    """Build profile-related use cases for CLI commands.

    Args:
        config_path: Override config file location (for testing).

    Returns:
        Tuple of (store, CreateProfile, ListProfiles).
    """
    from tw_guidance_computer.adapters.outbound.ini_profile_store import IniProfileStore
    from tw_guidance_computer.application.create_profile import CreateProfile
    from tw_guidance_computer.application.list_profiles import ListProfiles

    store = IniProfileStore(config_path or default_config_path())
    store.ensure_config_exists()
    return store, CreateProfile(store), ListProfiles(store)
