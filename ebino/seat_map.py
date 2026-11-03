"""The map of the basin, and where each seat's point goes (SPEC 4, 5-1, 14-7, 14-65).

The map data is a file in the repo (mapdata/ebino_osm.json), made once from
OpenStreetMap by tools/fetch_osm_map.py; nothing is fetched while the app
runs. When the file is missing or cannot be read, there is no map and the
screen keeps the seat list alone: the app still starts.

A seat's point comes from the seat table's 地区 (「市名＋地名」):
1. the municipality's name at the head is taken off (the longest name in the
   map data that the district starts with),
2. 「大字」 is taken off, and the rest is looked up in that municipality's
   place table as it is,
3. failing that, with 「字」 taken off or put on,
4. failing that, the place is not found.

A place in えびの市 puts the point there; several seats at one place spread
round it in a spiral, in seat ID order, so the point shows a district, never
an address (SPEC 4). A place in another municipality puts the point just
beyond the basin's rim, in that place's direction from the basin's middle.
A seat with no 地区, or whose place is not found, goes round the outside of
the map (between the rim and the screen's edge), its kind together.

No point is closer than POINT_GAP to another, and the same seats always give
the same points. Nothing here holds a company or a display name: the screen
takes each seat's label from the seat list.
"""

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from .seat_label import KIND_LABELS

MAP_FILE = Path(__file__).resolve().parent.parent / "mapdata" / "ebino_osm.json"

POINT_GAP = 19.0  # Centre to centre, in viewBox units.
SPIRAL_STEP = 11.0
OUTSIDE_STEP = 26.0  # How far beyond the rim a seat of another municipality sits.
EDGE_INSET = 22.0  # The first track round the outside, from the screen's edge.
TRACK_STEP = 22.0
KIND_GAP_SLOTS = 2  # Empty slots between two kinds on the outside track.
RIM_CLEARANCE = 12.0  # An outside slot this close to the rim is skipped.
# The few place names drawn faintly on the map: these kinds, the larger first.
BIG_PLACE_KINDS = ("town", "suburb", "village", "quarter")
MAX_PLACE_NAMES = 8
PLACE_NAME_GAP = 110.0
GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))

Point = tuple[float, float]


@dataclass(frozen=True)
class MapData:
    width: float
    height: float
    boundary: tuple[Point, ...]
    river: tuple[tuple[Point, ...], ...]
    # {municipality: {place name without 大字: (x, y, place kind)}}
    places: dict[str, dict[str, tuple[float, float, str]]]
    home: str  # The municipality whose boundary is drawn: えびの市.
    school: Point | None
    source: str
    license: str
    fetched: str


def _point(value) -> Point:
    x, y = value[0], value[1]
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (x, y)):
        raise ValueError("bad point")
    return (float(x), float(y))


def parse_map(raw: dict) -> MapData:
    """Raises ValueError (or KeyError, TypeError) on anything malformed."""
    _, _, width, height = (float(v) for v in raw["viewbox"])
    boundary = tuple(_point(p) for p in raw["boundary"])
    if len(boundary) < 3 or width <= 0 or height <= 0:
        raise ValueError("no boundary")
    river = tuple(tuple(_point(p) for p in line) for line in raw["river"])
    places = {}
    for municipality, table in raw["places"].items():
        places[str(municipality)] = {str(name): (*_point(value), str(value[2]))
                                     for name, value in table.items()}
    school = _point(raw["school"]) if raw.get("school") else None
    source, license_ = str(raw["source"]), str(raw["license"])
    if not source or not license_:
        raise ValueError("no source")
    return MapData(width, height, boundary, river, places, str(raw["home"]), school, source, license_,
                   str(raw.get("fetched", "")))


def load_map(path: Path | None = None) -> MapData | None:
    """None when there is no map file or it cannot be read: the seat list
    alone is shown, and the app starts all the same."""
    try:
        return parse_map(json.loads((path or MAP_FILE).read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError):
        return None


# --- finding a seat's place ---

def find_place(district: str, data: MapData) -> tuple[str, str] | None:
    """(municipality, place name) for a seat's 地区, or None when not found."""
    district = district.strip()
    municipality = next((m for m in sorted(data.places, key=len, reverse=True) if district.startswith(m)), None)
    if municipality is None:
        return None
    rest = district[len(municipality):].strip().removeprefix("大字").strip()
    if not rest:
        return None
    table = data.places[municipality]
    for name in (rest, rest.removeprefix("字") if rest.startswith("字") else "字" + rest):
        if name and name in table:
            return municipality, name
    return None


# --- geometry ---

def centroid(ring: tuple[Point, ...]) -> Point:
    area = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        cross = x1 * y2 - x2 * y1
        area += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if abs(area) < 1e-9:
        return (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))
    return (cx / (3 * area), cy / (3 * area))


def inside(point: Point, ring: tuple[Point, ...]) -> bool:
    x, y = point
    hit = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def distance_to_ring(point: Point, ring: tuple[Point, ...]) -> float:
    px, py = point
    best = math.inf
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        dx, dy = x2 - x1, y2 - y1
        length = dx * dx + dy * dy
        t = 0.0 if not length else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length))
        best = min(best, math.hypot(px - (x1 + t * dx), py - (y1 + t * dy)))
    return best


def _direction(start: Point, toward: Point) -> Point:
    dx, dy = toward[0] - start[0], toward[1] - start[1]
    length = math.hypot(dx, dy)
    return (0.0, -1.0) if length < 1e-9 else (dx / length, dy / length)


def rim_point(center: Point, toward: Point, ring: tuple[Point, ...]) -> Point:
    """Where the line from the middle toward a place leaves the basin for the
    last time (the rim in that direction)."""
    (cx, cy), (dx, dy) = center, _direction(center, toward)
    far = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        ex, ey = x2 - x1, y2 - y1
        denominator = dx * ey - dy * ex
        if abs(denominator) < 1e-12:
            continue
        t = ((x1 - cx) * ey - (y1 - cy) * ex) / denominator
        u = ((x1 - cx) * dy - (y1 - cy) * dx) / denominator
        if t > 0 and 0 <= u <= 1:
            far = max(far, t)
    return (cx + far * dx, cy + far * dy)


def edge_point(center: Point, toward: Point, width: float, height: float) -> Point:
    """Where the line from the middle through a point meets the screen's edge."""
    (cx, cy), (dx, dy) = center, _direction(center, toward)
    reach = math.inf
    for d, c, size in ((dx, cx, width), (dy, cy, height)):
        if d > 1e-12:
            reach = min(reach, (size - c) / d)
        elif d < -1e-12:
            reach = min(reach, -c / d)
    return (cx + reach * dx, cy + reach * dy)


# --- placing ---

@dataclass(frozen=True)
class SeatPoint:
    x: float
    y: float
    outer: bool


@dataclass
class Placement:
    points: dict[str, SeatPoint] = field(default_factory=dict)
    not_found: int = 0
    # The one crossing line (SPEC 5-1): from the edge to that seat's point.
    crossing: dict | None = None

    @property
    def outer(self) -> int:
        return sum(1 for p in self.points.values() if p.outer)

    def report(self) -> str:
        """Counts only: no place name, no seat ID."""
        return f"地図　点 {len(self.points)}・外周 {self.outer}・地名が見つからない {self.not_found}"


class _Board:
    """The points placed so far; a new one never comes closer than POINT_GAP."""

    def __init__(self, width: float, height: float):
        self.width, self.height = width, height
        self.taken: list[Point] = []

    def free(self, point: Point) -> bool:
        x, y = point
        margin = POINT_GAP / 2
        if not (margin <= x <= self.width - margin and margin <= y <= self.height - margin):
            return False
        return all(math.hypot(x - a, y - b) >= POINT_GAP - 1e-9 for a, b in self.taken)

    def take(self, point: Point) -> Point:
        point = (round(point[0], 1), round(point[1], 1))
        self.taken.append(point)
        return point

    def near(self, anchor: Point) -> Point:
        """The first free spot on a spiral round the anchor."""
        ax, ay = anchor
        for i in range(5000):
            r = SPIRAL_STEP * math.sqrt(i)
            spot = (ax + r * math.cos(i * GOLDEN_ANGLE), ay + r * math.sin(i * GOLDEN_ANGLE))
            if self.free((round(spot[0], 1), round(spot[1], 1))):
                return self.take(spot)
        raise ValueError("no room on the map")


def _track_slots(width: float, height: float, inset: float) -> list[Point]:
    """Slots POINT_GAP apart round a rectangle inset from the screen's edge,
    clockwise from the top left corner."""
    corners = [(inset, inset), (width - inset, inset), (width - inset, height - inset), (inset, height - inset)]
    slots = []
    for (x1, y1), (x2, y2) in zip(corners, corners[1:] + corners[:1]):
        steps = max(1, int(math.hypot(x2 - x1, y2 - y1) // POINT_GAP))
        slots += [(x1 + (x2 - x1) * k / steps, y1 + (y2 - y1) * k / steps) for k in range(steps)]
    return slots


def _outside_slots(data: MapData):
    """Every slot round the outside, track after track inward, skipping slots
    on or too near the basin."""
    inset = EDGE_INSET
    while inset < min(data.width, data.height) / 2:
        for slot in _track_slots(data.width, data.height, inset):
            if not inside(slot, data.boundary) and distance_to_ring(slot, data.boundary) >= RIM_CLEARANCE:
                yield slot
        inset += TRACK_STEP


def place_seats(data: MapData, seats) -> Placement:
    """Every seat given gets a point. Pass the seats on the map only."""
    seats = sorted(seats, key=lambda seat: seat.seat_id)
    center = centroid(data.boundary)
    board = _Board(data.width, data.height)
    placement = Placement()
    outer = []
    for seat in seats:
        if not seat.district.strip():
            outer.append(seat)
            continue
        found = find_place(seat.district, data)
        if found is None:
            placement.not_found += 1
            outer.append(seat)
            continue
        municipality, name = found
        x, y, _ = data.places[municipality][name]
        if municipality != data.home:
            rx, ry = rim_point(center, (x, y), data.boundary)
            dx, dy = _direction(center, (x, y))
            x, y = rx + OUTSIDE_STEP * dx, ry + OUTSIDE_STEP * dy
        px, py = board.near((x, y))
        placement.points[seat.seat_id] = SeatPoint(px, py, False)

    slots = _outside_slots(data)
    started = False
    for kind in KIND_LABELS:
        group = [seat for seat in outer if seat.kind == kind]
        if not group:
            continue
        if started:  # A few empty slots between two kinds.
            for _ in range(KIND_GAP_SLOTS):
                next(slots, None)
        started = True
        for seat in group:
            for slot in slots:
                if board.free((round(slot[0], 1), round(slot[1], 1))):
                    px, py = board.take(slot)
                    placement.points[seat.seat_id] = SeatPoint(px, py, True)
                    break
            else:
                raise ValueError("no room round the map")

    target = next((seat.seat_id for seat in seats if seat.is_crossing_target), None)
    if target is not None:
        point = placement.points[target]
        start = edge_point(center, (point.x, point.y), data.width, data.height)
        placement.crossing = {"seat_id": target, "from": [round(start[0], 1), round(start[1], 1)],
                              "to": [point.x, point.y]}
    return placement


def place_names(data: MapData) -> list[dict]:
    """A few large place names in えびの市, kept apart, drawn faintly."""
    table = data.places.get(data.home, {})
    candidates = sorted(((BIG_PLACE_KINDS.index(kind), name, x, y) for name, (x, y, kind) in table.items()
                         if kind in BIG_PLACE_KINDS))
    chosen: list[dict] = []
    for _, name, x, y in candidates:
        if len(chosen) == MAX_PLACE_NAMES:
            break
        if all(math.hypot(x - c["x"], y - c["y"]) >= PLACE_NAME_GAP for c in chosen):
            chosen.append({"name": name, "x": x, "y": y})
    return chosen


def map_view(data: MapData, placement: Placement, school_label: str) -> dict:
    """The map part of /api/setup: the drawing, never a seat's label."""
    return {
        "viewbox": [0, 0, data.width, data.height],
        "boundary": [list(p) for p in data.boundary],
        "river": [[list(p) for p in line] for line in data.river],
        "places": place_names(data),
        "source": data.source,
        # A landmark, not a seat: no light, no words, not counted.
        "school": ({"x": data.school[0], "y": data.school[1], "label": school_label}
                   if data.school and school_label else None),
        "crossing": placement.crossing,
    }
