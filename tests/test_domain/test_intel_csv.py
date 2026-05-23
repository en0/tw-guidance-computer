import hashlib

import pytest

from tw_guidance_computer.domain.exceptions import IntelDataError
from tw_guidance_computer.domain.intel_csv import deserialize_intel, serialize_intel
from tw_guidance_computer.domain.models import (
    CommodityType,
    Planet,
    Port,
    PortCommodity,
    Sector,
    TradeDirection,
    WarpConnection,
)


@pytest.fixture()
def sample_sectors():
    return [
        (Sector(id=616, region="uncharted space", explored=True), 1716400000.0),
        (Sector(id=100, region="The Federation", explored=False), 1716400001.0),
    ]


@pytest.fixture()
def sample_ports():
    return [
        (
            Port(
                sector_id=616,
                name="Trader Vic's",
                port_class=6,
                port_type="SBS",
                commodities=[
                    PortCommodity(
                        commodity=CommodityType.FUEL_ORE, direction=TradeDirection.SELLING, quantity=500, pct=100
                    ),
                    PortCommodity(
                        commodity=CommodityType.ORGANICS, direction=TradeDirection.BUYING, quantity=300, pct=50
                    ),
                    PortCommodity(
                        commodity=CommodityType.EQUIPMENT, direction=TradeDirection.SELLING, quantity=200, pct=75
                    ),
                ],
            ),
            1716400000.0,
        ),
    ]


@pytest.fixture()
def sample_warps():
    return [
        (WarpConnection(from_sector=616, to_sector=544, explored=True), 1716400000.0),
        (WarpConnection(from_sector=616, to_sector=564, explored=False), 1716400000.0),
    ]


@pytest.fixture()
def sample_planets():
    return [
        (Planet(sector_id=616, name="es", planet_class="M"), 1716400000.0),
    ]


class TestSerializeIntel:
    def test_produces_sectioned_csv(self, sample_sectors, sample_ports, sample_warps, sample_planets):
        result = serialize_intel(sample_sectors, sample_ports, sample_warps, sample_planets)
        assert "#TYPE:sectors\n" in result
        assert "#TYPE:ports\n" in result
        assert "#TYPE:warps\n" in result
        assert "#TYPE:planets\n" in result

    def test_includes_checksum_trailer(self, sample_sectors, sample_ports, sample_warps, sample_planets):
        result = serialize_intel(sample_sectors, sample_ports, sample_warps, sample_planets)
        assert result.rstrip("\n").split("\n")[-1].startswith("#SHA256:")

    def test_checksum_is_valid(self, sample_sectors, sample_ports, sample_warps, sample_planets):
        result = serialize_intel(sample_sectors, sample_ports, sample_warps, sample_planets)
        lines = result.split("\n")
        # Find checksum line
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].startswith("#SHA256:"):
                body = "\n".join(lines[:i]) + "\n"
                expected = lines[i][len("#SHA256:"):]
                actual = hashlib.sha256(body.encode()).hexdigest()
                assert actual == expected
                return
        pytest.fail("No checksum line found")

    def test_empty_data_sets(self):
        result = serialize_intel([], [], [], [])
        assert "#TYPE:sectors\n" in result
        assert "#SHA256:" in result

    def test_port_name_with_comma(self):
        port = Port(sector_id=1, name="Port Alpha, Beta", port_class=3, port_type="SSB", commodities=[])
        result = serialize_intel([], [(port, 1.0)], [], [])
        assert "Port Alpha, Beta" in result


class TestDeserializeIntel:
    def test_round_trip_sectors(self, sample_sectors):
        content = serialize_intel(sample_sectors, [], [], [])
        sectors, ports, warps, planets = deserialize_intel(content)
        assert len(sectors) == 2
        assert sectors[0][0].id == 616
        assert sectors[0][0].region == "uncharted space"
        assert sectors[0][0].explored is True
        assert sectors[0][1] == 1716400000.0
        assert sectors[1][0].id == 100
        assert sectors[1][0].explored is False

    def test_round_trip_ports_with_commodities(self, sample_ports):
        content = serialize_intel([], sample_ports, [], [])
        _, ports, _, _ = deserialize_intel(content)
        assert len(ports) == 1
        port, ts = ports[0]
        assert port.sector_id == 616
        assert port.name == "Trader Vic's"
        assert port.port_class == 6
        assert port.port_type == "SBS"
        assert len(port.commodities) == 3
        assert port.commodities[0].commodity == CommodityType.FUEL_ORE
        assert port.commodities[0].direction == TradeDirection.SELLING
        assert port.commodities[0].quantity == 500
        assert port.commodities[0].pct == 100
        assert ts == 1716400000.0

    def test_round_trip_warps(self, sample_warps):
        content = serialize_intel([], [], sample_warps, [])
        _, _, warps, _ = deserialize_intel(content)
        assert len(warps) == 2
        assert warps[0][0].from_sector == 616
        assert warps[0][0].to_sector == 544
        assert warps[0][0].explored is True
        assert warps[1][0].explored is False

    def test_round_trip_planets(self, sample_planets):
        content = serialize_intel([], [], [], sample_planets)
        _, _, _, planets = deserialize_intel(content)
        assert len(planets) == 1
        assert planets[0][0].sector_id == 616
        assert planets[0][0].name == "es"
        assert planets[0][0].planet_class == "M"

    def test_round_trip_all(self, sample_sectors, sample_ports, sample_warps, sample_planets):
        content = serialize_intel(sample_sectors, sample_ports, sample_warps, sample_planets)
        sectors, ports, warps, planets = deserialize_intel(content)
        assert len(sectors) == 2
        assert len(ports) == 1
        assert len(warps) == 2
        assert len(planets) == 1

    def test_port_name_with_comma_round_trip(self):
        port = Port(sector_id=1, name="Port Alpha, Beta", port_class=3, port_type="SSB", commodities=[])
        content = serialize_intel([], [(port, 2.0)], [], [])
        _, ports, _, _ = deserialize_intel(content)
        assert ports[0][0].name == "Port Alpha, Beta"

    def test_empty_data_round_trip(self):
        content = serialize_intel([], [], [], [])
        sectors, ports, warps, planets = deserialize_intel(content)
        assert sectors == []
        assert ports == []
        assert warps == []
        assert planets == []

    def test_missing_checksum_raises(self):
        with pytest.raises(IntelDataError, match="Missing checksum trailer"):
            deserialize_intel("#TYPE:sectors\nid,region,explored,updated_at\n")

    def test_checksum_mismatch_raises(self):
        content = serialize_intel([], [], [], [])
        corrupted = content.replace(content.split("#SHA256:")[1], "0" * 64 + "\n")
        with pytest.raises(IntelDataError, match="Checksum mismatch"):
            deserialize_intel(corrupted)

    def test_crlf_content_validates_checksum(self, sample_sectors):
        """Files with \\r\\n line endings are normalized before checksum validation."""
        # Simulate: content with \r\n, checksum computed AFTER normalization
        # (this is what happens when read_text() normalizes and the serializer used \n)
        content = serialize_intel(sample_sectors, [], [], [])
        # Inject \r\n — simulating a file that somehow got \r\n but checksum is over \n content
        crlf_content = content.replace("\n", "\r\n")
        # After normalization, body matches original \n content, checksum still valid
        sectors, _, _, _ = deserialize_intel(crlf_content)
        assert len(sectors) == 2

    def test_corrupt_sector_data_raises(self):
        # Build valid content but with bad sector data
        body = "#TYPE:sectors\nid,region,explored,updated_at\nnot_a_number,region,1,1.0\n"
        checksum = hashlib.sha256(body.encode()).hexdigest()
        content = body + f"#SHA256:{checksum}\n"
        with pytest.raises(IntelDataError, match="Failed to parse sectors"):
            deserialize_intel(content)

    def test_corrupt_port_commodities_json_raises(self):
        body = (
            "#TYPE:ports\nsector_id,name,port_class,port_type,commodities_json,updated_at\n"
            "1,Test,3,SSB,not_json,1.0\n"
        )
        checksum = hashlib.sha256(body.encode()).hexdigest()
        content = body + f"#SHA256:{checksum}\n"
        with pytest.raises(IntelDataError, match="Invalid commodities JSON"):
            deserialize_intel(content)
