"""Typed container for all use cases."""

from dataclasses import dataclass

from tw_guidance_computer.application.create_profile import CreateProfile
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
from tw_guidance_computer.application.list_profiles import ListProfiles
from tw_guidance_computer.application.parse_log_chunk import ParseLogChunk
from tw_guidance_computer.application.render_sector_art import RenderSectorArt
from tw_guidance_computer.application.search_ports import SearchPorts


@dataclass(frozen=True)
class UseCases:
    """Typed container grouping all use cases for dependency passing."""

    find_trade_pairs: FindTradePairs
    find_nearest_pair: FindNearestPair
    find_nearby_ports: FindNearbyPorts
    find_path: FindPath
    find_sell_locations: FindSellLocations
    search_ports: SearchPorts
    render_sector_art: RenderSectorArt
    parse_log_chunk: ParseLogChunk
    get_player_status: GetPlayerStatus
    get_sector_info: GetSectorInfo
    list_ports: ListPorts
    get_recent_chat: GetRecentChat
    get_database_summary: GetDatabaseSummary
    create_profile: CreateProfile | None = None
    list_profiles: ListProfiles | None = None
