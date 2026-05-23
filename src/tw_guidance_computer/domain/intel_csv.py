"""Pure functions for serializing/deserializing intel data to CSV format."""

from __future__ import annotations

import csv
import hashlib
import io
import json

from tw_guidance_computer.domain.exceptions import IntelDataError
from tw_guidance_computer.domain.models.planet import Planet
from tw_guidance_computer.domain.models.port import Port, PortCommodity
from tw_guidance_computer.domain.models.sector import Sector, WarpConnection
from tw_guidance_computer.domain.models.types import CommodityType, TradeDirection


def serialize_intel(
    sectors: list[tuple[Sector, float]],
    ports: list[tuple[Port, float]],
    warps: list[tuple[WarpConnection, float]],
    planets: list[tuple[Planet, float]],
) -> str:
    """Serialize intel data to sectioned CSV with SHA-256 checksum.

    Args:
        sectors: Sector objects with their updated_at timestamps.
        ports: Port objects with their updated_at timestamps.
        warps: WarpConnection objects with their updated_at timestamps.
        planets: Planet objects with their updated_at timestamps.

    Returns:
        Complete CSV string with type headers and checksum trailer.
    """
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")

    output.write("#TYPE:sectors\n")
    writer.writerow(["id", "region", "explored", "updated_at"])
    for sector, ts in sectors:
        writer.writerow([sector.id, sector.region, int(sector.explored), ts])

    output.write("#TYPE:ports\n")
    writer.writerow(["sector_id", "name", "port_class", "port_type", "commodities_json", "updated_at"])
    for port, ts in ports:
        commodities_json = json.dumps([
            {"commodity": pc.commodity.value, "direction": pc.direction.value, "quantity": pc.quantity, "pct": pc.pct}
            for pc in port.commodities
        ])
        writer.writerow([port.sector_id, port.name, port.port_class, port.port_type, commodities_json, ts])

    output.write("#TYPE:warps\n")
    writer.writerow(["from_sector", "to_sector", "explored", "updated_at"])
    for warp, ts in warps:
        writer.writerow([warp.from_sector, warp.to_sector, int(warp.explored), ts])

    output.write("#TYPE:planets\n")
    writer.writerow(["sector_id", "name", "planet_class", "updated_at"])
    for planet, ts in planets:
        writer.writerow([planet.sector_id, planet.name, planet.planet_class, ts])

    content = output.getvalue()
    checksum = hashlib.sha256(content.encode()).hexdigest()
    return content + f"#SHA256:{checksum}\n"


IntelResult = tuple[
    list[tuple[Sector, float]],
    list[tuple[Port, float]],
    list[tuple[WarpConnection, float]],
    list[tuple[Planet, float]],
]


def deserialize_intel(
    content: str,
) -> IntelResult:
    """Parse sectioned CSV and validate checksum.

    Args:
        content: Complete CSV string with type headers and checksum trailer.

    Returns:
        Tuple of (sectors, ports, warps, planets) each with updated_at timestamps.

    Raises:
        IntelDataError: On checksum mismatch or parse failure.
    """
    # Normalize line endings — old serializer produced mixed \r\n and \n
    content = content.replace("\r\n", "\n")
    lines = content.split("\n")

    # Find and validate checksum
    checksum_line = ""
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("#SHA256:"):
            checksum_line = lines[i]
            body = "\n".join(lines[:i]) + "\n"
            break
    else:
        raise IntelDataError("Missing checksum trailer")

    expected_hash = checksum_line[len("#SHA256:"):]
    actual_hash = hashlib.sha256(body.encode()).hexdigest()
    if actual_hash != expected_hash:
        raise IntelDataError("Checksum mismatch")

    # Parse sections
    sectors: list[tuple[Sector, float]] = []
    ports: list[tuple[Port, float]] = []
    warps: list[tuple[WarpConnection, float]] = []
    planets: list[tuple[Planet, float]] = []

    current_type: str | None = None
    section_lines: list[str] = []

    for line in body.split("\n"):
        if line.startswith("#TYPE:"):
            if current_type is not None:
                _parse_section(current_type, section_lines, sectors, ports, warps, planets)
            current_type = line[len("#TYPE:"):]
            section_lines = []
        elif line.strip():
            section_lines.append(line)

    if current_type is not None:
        _parse_section(current_type, section_lines, sectors, ports, warps, planets)

    return sectors, ports, warps, planets


def _parse_section(
    section_type: str,
    lines: list[str],
    sectors: list[tuple[Sector, float]],
    ports: list[tuple[Port, float]],
    warps: list[tuple[WarpConnection, float]],
    planets: list[tuple[Planet, float]],
) -> None:
    """Parse a single CSV section into the appropriate list."""
    if not lines:
        return

    # Skip header row
    data_text = "\n".join(lines[1:])
    reader = csv.reader(io.StringIO(data_text))

    try:
        if section_type == "sectors":
            for row in reader:
                sectors.append((
                    Sector(id=int(row[0]), region=row[1], explored=bool(int(row[2]))),
                    float(row[3]),
                ))
        elif section_type == "ports":
            for row in reader:
                commodities = _parse_commodities_json(row[4])
                ports.append((
                    Port(
                        sector_id=int(row[0]),
                        name=row[1],
                        port_class=int(row[2]),
                        port_type=row[3],
                        commodities=commodities,
                    ),
                    float(row[5]),
                ))
        elif section_type == "warps":
            for row in reader:
                warps.append((
                    WarpConnection(from_sector=int(row[0]), to_sector=int(row[1]), explored=bool(int(row[2]))),
                    float(row[3]),
                ))
        elif section_type == "planets":
            for row in reader:
                planets.append((
                    Planet(sector_id=int(row[0]), name=row[1], planet_class=row[2]),
                    float(row[3]),
                ))
    except (IndexError, ValueError) as e:
        raise IntelDataError(f"Failed to parse {section_type} section: {e}") from e


def _parse_commodities_json(raw: str) -> list[PortCommodity]:
    """Parse JSON commodity list back into PortCommodity objects.

    Raises:
        IntelDataError: If JSON is invalid or fields are missing.
    """
    try:
        items = json.loads(raw)
    except (ValueError, TypeError) as e:
        raise IntelDataError(f"Invalid commodities JSON: {e}") from e

    return [
        PortCommodity(
            commodity=CommodityType(item["commodity"]),
            direction=TradeDirection(item["direction"]),
            quantity=item["quantity"],
            pct=item["pct"],
        )
        for item in items
    ]
