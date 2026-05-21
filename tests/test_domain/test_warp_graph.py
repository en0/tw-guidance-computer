"""Tests for the WarpGraph domain service."""

import pytest

from tw_guidance_computer.domain.models import WarpConnection
from tw_guidance_computer.domain.warp_graph import WarpGraph


@pytest.fixture()
def simple_graph():
    """Linear graph: 1-2-3-4."""
    return WarpGraph(
        warps=[
            WarpConnection(from_sector=1, to_sector=2),
            WarpConnection(from_sector=2, to_sector=3),
            WarpConnection(from_sector=3, to_sector=4),
        ]
    )


@pytest.fixture()
def branching_graph():
    """Graph: 1-2-3, 2-4, 4-5."""
    return WarpGraph(
        warps=[
            WarpConnection(from_sector=1, to_sector=2),
            WarpConnection(from_sector=2, to_sector=3),
            WarpConnection(from_sector=2, to_sector=4),
            WarpConnection(from_sector=4, to_sector=5),
        ]
    )


class TestNeighbors:
    def test_returns_adjacent_sectors(self, simple_graph):
        assert simple_graph.neighbors(2) == {1, 3}

    def test_endpoint_has_one_neighbor(self, simple_graph):
        assert simple_graph.neighbors(1) == {2}

    def test_unknown_sector_returns_empty(self, simple_graph):
        assert simple_graph.neighbors(999) == set()

    def test_bidirectional(self, simple_graph):
        assert 2 in simple_graph.neighbors(1)
        assert 1 in simple_graph.neighbors(2)


class TestBfsPath:
    def test_direct_path(self, simple_graph):
        assert simple_graph.bfs_path(1, 2) == [1, 2]

    def test_multi_hop_path(self, simple_graph):
        assert simple_graph.bfs_path(1, 4) == [1, 2, 3, 4]

    def test_same_sector(self, simple_graph):
        assert simple_graph.bfs_path(1, 1) == [1]

    def test_no_path_returns_none(self):
        graph = WarpGraph(
            warps=[
                WarpConnection(from_sector=1, to_sector=2),
                WarpConnection(from_sector=3, to_sector=4),
            ]
        )
        assert graph.bfs_path(1, 4) is None

    def test_reverse_direction(self, simple_graph):
        assert simple_graph.bfs_path(4, 1) == [4, 3, 2, 1]

    def test_shortest_path_chosen(self, branching_graph):
        path = branching_graph.bfs_path(1, 5)
        assert path == [1, 2, 4, 5]

    def test_empty_graph(self):
        graph = WarpGraph(warps=[])
        assert graph.bfs_path(1, 2) is None


class TestBfsDistances:
    def test_all_distances(self, simple_graph):
        distances = simple_graph.bfs_distances(1)
        assert distances == {2: 1, 3: 2, 4: 3}

    def test_max_hops_limits_search(self, simple_graph):
        distances = simple_graph.bfs_distances(1, max_hops=2)
        assert distances == {2: 1, 3: 2}
        assert 4 not in distances

    def test_unbounded_reaches_all(self, simple_graph):
        distances = simple_graph.bfs_distances(1, max_hops=None)
        assert distances == {2: 1, 3: 2, 4: 3}

    def test_excludes_start(self, simple_graph):
        distances = simple_graph.bfs_distances(1)
        assert 1 not in distances

    def test_unknown_start_returns_empty(self, simple_graph):
        distances = simple_graph.bfs_distances(999)
        assert distances == {}

    def test_max_hops_zero_returns_empty(self, simple_graph):
        distances = simple_graph.bfs_distances(1, max_hops=0)
        assert distances == {}


class TestBfsFirstMatch:
    def test_finds_nearest_target(self, branching_graph):
        result = branching_graph.bfs_first_match(1, {3, 5})
        assert result is not None
        sector, path = result
        assert sector == 3
        assert path == [1, 2, 3]

    def test_start_is_target(self, simple_graph):
        result = simple_graph.bfs_first_match(2, {2, 4})
        assert result is not None
        sector, path = result
        assert sector == 2
        assert path == [2]

    def test_no_target_reachable(self):
        graph = WarpGraph(
            warps=[
                WarpConnection(from_sector=1, to_sector=2),
                WarpConnection(from_sector=3, to_sector=4),
            ]
        )
        assert graph.bfs_first_match(1, {4}) is None

    def test_empty_targets_returns_none(self, simple_graph):
        assert simple_graph.bfs_first_match(1, set()) is None

    def test_returns_path_to_target(self, simple_graph):
        result = simple_graph.bfs_first_match(1, {4})
        assert result is not None
        sector, path = result
        assert sector == 4
        assert path == [1, 2, 3, 4]
