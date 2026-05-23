"""Composition root — centralizes all construction logic."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import final

from tw_guidance_computer.adapters.inbound.cli_commands import CliAdapter
from tw_guidance_computer.adapters.inbound.tui import HudDisplay
from tw_guidance_computer.adapters.outbound.ini_profile_store import IniProfileStore
from tw_guidance_computer.adapters.outbound.intel_identity import compute_intel_identity, validate_intel_config
from tw_guidance_computer.adapters.outbound.log_reader import TailLogReader
from tw_guidance_computer.adapters.outbound.sftp_transport import SftpTransport
from tw_guidance_computer.adapters.outbound.sqlite_store import SqliteGameStateStore
from tw_guidance_computer.application.create_profile import CreateProfile
from tw_guidance_computer.application.export_intel import ExportIntel
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
from tw_guidance_computer.application.import_intel import ImportIntel
from tw_guidance_computer.application.list_ports import ListPorts
from tw_guidance_computer.application.list_profiles import ListProfiles
from tw_guidance_computer.application.parse_log_chunk import ParseLogChunk
from tw_guidance_computer.application.ports.log_reader import LogReader
from tw_guidance_computer.application.pull_intel import PullIntel
from tw_guidance_computer.application.push_intel import PushIntel
from tw_guidance_computer.application.render_sector_art import RenderSectorArt
from tw_guidance_computer.application.search_ports import SearchPorts
from tw_guidance_computer.application.sync_intel_worker import SyncIntelWorker
from tw_guidance_computer.application.use_cases import UseCases
from tw_guidance_computer.domain.exceptions import DatabaseNotFoundError
from tw_guidance_computer.domain.models import IntelConfig, TurnThresholds


def _default_config_path() -> Path:
    """Return the default config file path."""
    return Path.home() / ".config" / "tw-guidance-computer" / "config.ini"


def _resolve_config(
    profile_name: str | None, config_path: Path | None = None
) -> tuple[Path, TurnThresholds, str, IntelConfig | None, str | None]:
    """Resolve database path, turn thresholds, intel config, and effective profile name.

    Args:
        profile_name: Profile to use, or None for the configured default.
        config_path: Override config file location (for testing).

    Returns:
        Tuple of (db_path, turn_thresholds, effective_profile_name, intel_config, intel_identity).

    Raises:
        ConfigError: If the config file is malformed.
        ProfileNotFoundError: If the requested profile doesn't exist.
        ValidationError: If threshold values are invalid.
        IntelKeyError: If intel is configured but key files are missing.
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

    # Intel config resolution
    intel_host = store.get_config_value(effective_name, "intel_host", "")
    intel_config: IntelConfig | None = None
    intel_identity: str | None = None

    if intel_host.strip():
        intel_key = os.path.expanduser(store.get_config_value(effective_name, "intel_key", ""))
        intel_port = int(store.get_config_value(effective_name, "intel_port", "22"))
        intel_sync_interval = int(store.get_config_value(effective_name, "intel_sync_interval", "300"))
        intel_sync_budget = int(store.get_config_value(effective_name, "intel_sync_budget", "30"))
        intel_max_file_size = int(store.get_config_value(effective_name, "intel_max_file_size", "10485760"))
        intel_config = IntelConfig(
            host=intel_host,
            key_path=intel_key,
            port=intel_port,
            sync_interval=intel_sync_interval,
            sync_budget=intel_sync_budget,
            max_file_size=intel_max_file_size,
        )
        validate_intel_config(intel_config)
        intel_identity = compute_intel_identity(intel_key)

    return db_path, thresholds, effective_name, intel_config, intel_identity


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
            IntelKeyError: If intel is configured but key files are missing.
        """
        db_path, thresholds, _, intel_config, intel_identity = _resolve_config(profile_name, config_path)

        if require_existing_db and not db_path.exists():
            raise DatabaseNotFoundError(
                f"No database found at {db_path}. Run tw-hud first to populate it."
            )

        self.thresholds = thresholds
        self.intel_config = intel_config

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

        # Intel wiring (only when configured)
        self.sync_worker: SyncIntelWorker | None = None
        self.push_intel: PushIntel | None = None
        self.pull_intel: PullIntel | None = None
        self._intel_store: SqliteGameStateStore | None = None

        if intel_config is not None and intel_identity is not None:
            intel_store = SqliteGameStateStore(db_path, check_same_thread=False)
            self._intel_store = intel_store
            transport = SftpTransport(intel_config)
            export_intel = ExportIntel(intel_store)
            import_intel = ImportIntel(intel_store)
            self.push_intel = PushIntel(export_intel, transport, intel_identity)
            self.pull_intel = PullIntel(import_intel, transport, intel_identity, intel_config.max_file_size)
            self.sync_worker = SyncIntelWorker(self.push_intel, self.pull_intel, intel_config)

        self.reader: TailLogReader | None = None
        if log_path is not None:
            self.reader = TailLogReader(log_path)

    def close(self) -> None:
        """Clean up resources."""
        if self.reader is not None:
            self.reader.close()
        if self._intel_store is not None:
            self._intel_store.close()
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

    def intel_context_factory(
        profile_name: str | None,
    ) -> tuple[PushIntel | None, PullIntel | None, IntelConfig | None, SqliteGameStateStore | None]:
        db_path, _, _, intel_config, intel_identity = _resolve_config(profile_name, config_path)
        if intel_config is None or intel_identity is None or not db_path.exists():
            return None, None, None, None
        intel_store_instance = SqliteGameStateStore(db_path, check_same_thread=False)
        transport = SftpTransport(intel_config)
        export_intel = ExportIntel(intel_store_instance)
        import_intel = ImportIntel(intel_store_instance)
        push = PushIntel(export_intel, transport, intel_identity)
        pull = PullIntel(import_intel, transport, intel_identity, intel_config.max_file_size)
        return push, pull, intel_config, intel_store_instance

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
        intel_context_factory=intel_context_factory,
    )


def build_hud(config_path: Path | None = None) -> HudDisplay:
    """Build the HUD adapter with all dependencies.

    Args:
        config_path: Override config file location (for testing).

    Returns:
        A fully wired HudDisplay ready to run.
    """
    create, _ = build_profile_use_cases(config_path)

    def hud_context_factory(
        profile_name: str | None,
        log_path: Path,
        parse_existing: bool,
    ) -> tuple[UseCases, LogReader, TurnThresholds, SyncIntelWorker | None, Callable[[], None]]:
        ctx = AppContext(profile_name=profile_name, config_path=config_path, log_path=log_path)
        assert ctx.reader is not None
        if parse_existing:
            full_text = ctx.reader.read_full()
            ctx.use_cases.parse_log_chunk.execute(full_text)
        return ctx.use_cases, ctx.reader, ctx.thresholds, ctx.sync_worker, ctx.close

    return HudDisplay(
        create_profile=create,
        hud_context_factory=hud_context_factory,
    )
