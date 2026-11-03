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
A seat with no 地区, or whose place is not found, goes on its kind's shelf: one
block per kind, row by row in seat ID order, off the basin where the viewBox
is free (away from the rim, the river, the school's landmark, the place names,
the other points and the screen's edge), nearest a corner that has room.

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
# The shelves: one block per kind, off the basin, for the seats with no place.
CELL = 5.0  # The grid that tells which parts of the viewBox are taken.
SHELF_CLEARANCE = 20.0  # Kept free round the rim.
RIVER_CLEARANCE = 16.0
SHELF_EDGE = 12.0  # Kept free along the screen's edge.
SHELF_PAD = 12.0  # From a block's outer points to its edge.
SHELF_GAP = 16.0  # Between two shelves.
POINT_ROOM = 14.0  # Kept free round a point placed on the basin or beyond the rim.
SHELF_NAME_HEIGHT = 26.0  # The kind's name above the block.
SHELF_NAME_CHAR = 18.0  # One character of the kind's name (style.css: 17px).
SHELF_SCAN = 10.0
PLACE_NAME_CHAR = 24.5  # One character of a place name (style.css: 22px, spaced .1em).
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
    outer: bool  # On its kind's shelf, off the basin (the startup line's 外周).


@dataclass
class Placement:
    points: dict[str, SeatPoint] = field(default_factory=dict)
    not_found: int = 0
    # The one crossing line (SPEC 5-1): from the edge to that seat's point.
    crossing: dict | None = None
    shelves: list["Shelf"] = field(default_factory=list)

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


class _Room:
    """Which parts of the viewBox are taken, on a grid of CELL units: the
    basin and a margin round it, the river, the school's landmark, the place
    names, the screen's edge, the points placed so far, and the shelves."""

    def __init__(self, data: MapData):
        self.cols, self.rows = math.ceil(data.width / CELL), math.ceil(data.height / CELL)
        self.taken = bytearray(self.cols * self.rows)
        self._sums = None
        self._fill_basin(data.boundary)
        ring = data.boundary + data.boundary[:1]
        for a, b in zip(ring, ring[1:]):
            self.segment(a, b, SHELF_CLEARANCE)
        for line in data.river:
            for a, b in zip(line, line[1:]):
                self.segment(a, b, RIVER_CLEARANCE)
        if data.school:
            x, y = data.school
            self.rect(x - 50, y - 32, x + 50, y + 38)
        for place in place_names(data):
            half = len(place["name"]) * PLACE_NAME_CHAR / 2 + 4
            self.rect(place["x"] - half, place["y"] - 24, place["x"] + half, place["y"] + 8)
        self.rect(0, 0, data.width, SHELF_EDGE)
        self.rect(0, data.height - SHELF_EDGE, data.width, data.height)
        self.rect(0, 0, SHELF_EDGE, data.height)
        self.rect(data.width - SHELF_EDGE, 0, data.width, data.height)

    def _cells(self, x0, y0, x1, y1):
        return (max(0, int(x0 // CELL)), max(0, int(y0 // CELL)),
                min(self.cols - 1, int(x1 // CELL)), min(self.rows - 1, int(y1 // CELL)))

    def _row(self, row, c0, c1):
        if c1 >= c0:
            self.taken[row * self.cols + c0: row * self.cols + c1 + 1] = b"\x01" * (c1 - c0 + 1)

    def rect(self, x0, y0, x1, y1):
        c0, r0, c1, r1 = self._cells(x0, y0, x1, y1)
        for row in range(r0, r1 + 1):
            self._row(row, c0, c1)
        self._sums = None

    def segment(self, a: Point, b: Point, reach: float):
        (x1, y1), (x2, y2) = a, b
        c0, r0, c1, r1 = self._cells(min(x1, x2) - reach, min(y1, y2) - reach,
                                     max(x1, x2) + reach, max(y1, y2) + reach)
        dx, dy = x2 - x1, y2 - y1
        length = dx * dx + dy * dy
        for row in range(r0, r1 + 1):
            py = (row + 0.5) * CELL
            for col in range(c0, c1 + 1):
                px = (col + 0.5) * CELL
                t = 0.0 if not length else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length))
                if math.hypot(px - (x1 + t * dx), py - (y1 + t * dy)) <= reach:
                    self.taken[row * self.cols + col] = 1
        self._sums = None

    def _fill_basin(self, ring: tuple[Point, ...]):
        edges = list(zip(ring, ring[1:] + ring[:1]))
        for row in range(self.rows):
            y = (row + 0.5) * CELL
            xs = sorted((x2 - x1) * (y - y1) / (y2 - y1) + x1
                        for (x1, y1), (x2, y2) in edges if (y1 > y) != (y2 > y))
            for left, right in zip(xs[::2], xs[1::2]):
                self._row(row, max(0, int(left // CELL)), min(self.cols - 1, int(right // CELL)))
        self._sums = None

    def free(self, x0, y0, x1, y1) -> bool:
        """Nothing in the rectangle, which lies wholly on the screen."""
        if x0 < 0 or y0 < 0 or x1 >= self.cols * CELL or y1 >= self.rows * CELL:
            return False
        width = self.cols + 1
        if self._sums is None:  # Sums over rectangles, so each look is quick.
            sums = [0] * (width * (self.rows + 1))
            for row in range(self.rows):
                running = 0
                for col in range(self.cols):
                    running += self.taken[row * self.cols + col]
                    sums[(row + 1) * width + col + 1] = sums[row * width + col + 1] + running
            self._sums = sums
        sums = self._sums
        c0, r0, c1, r1 = int(x0 // CELL), int(y0 // CELL), int(x1 // CELL) + 1, int(y1 // CELL) + 1
        return not (sums[r1 * width + c1] - sums[r0 * width + c1] - sums[r1 * width + c0] + sums[r0 * width + c0])


@dataclass(frozen=True)
class Shelf:
    """One kind's seats off the basin, in a block, its kind's name above it."""
    kind: str
    box: tuple[float, float, float, float]  # The block and its name: x0, y0, x1, y1.
    label: Point  # Where the name starts (left end, baseline).


def _shelf_shapes(count: int) -> list[tuple[int, int]]:
    """(columns, rows) for a block of count points, neither too long nor too tall."""
    shapes = {}
    for columns in range(1, count + 1):
        rows = math.ceil(count / columns)
        if rows <= 3 * columns and columns <= 4 * rows and rows not in shapes:
            shapes[rows] = columns
    return sorted((columns, rows) for rows, columns in shapes.items()) or [(1, 1)]


def _place_shelf(room: _Room, kind: str, count: int, width: float, height: float):
    """The block nearest a corner of the screen that has room for it and its
    name, as (Shelf, slots in seat order), or None. Each point is POINT_GAP
    from the next, row by row. The same room always gives the same block."""
    name_width = len(KIND_LABELS[kind]) * SHELF_NAME_CHAR + 8
    corners = ((0, 0), (width, 0), (0, height), (width, height))
    best = None
    for columns, rows in _shelf_shapes(count):
        span_x, span_y = (columns - 1) * POINT_GAP, (rows - 1) * POINT_GAP
        ax = SHELF_EDGE + SHELF_PAD
        while ax + span_x + SHELF_PAD < width:
            ay = SHELF_EDGE + SHELF_PAD + SHELF_NAME_HEIGHT
            while ay + span_y + SHELF_PAD < height:
                block = (ax - SHELF_PAD, ay - SHELF_PAD, ax + span_x + SHELF_PAD, ay + span_y + SHELF_PAD)
                name = (block[0], block[1] - SHELF_NAME_HEIGHT, block[0] + name_width, block[1])
                middle = ((block[0] + max(block[2], name[2])) / 2, (name[1] + block[3]) / 2)
                score = (round(min(math.hypot(middle[0] - cx, middle[1] - cy) for cx, cy in corners), 3),
                         ay, ax, columns)
                if (best is None or score < best[0]) and room.free(*block) and room.free(*name):
                    best = (score, ax, ay, columns, block, name)
                ay += SHELF_SCAN
            ax += SHELF_SCAN
    if best is None:
        return None
    _, ax, ay, columns, block, name = best
    box = (block[0], name[1], max(block[2], name[2]), block[3])
    room.rect(box[0] - SHELF_GAP, box[1] - SHELF_GAP, box[2] + SHELF_GAP, box[3] + SHELF_GAP)
    slots = [(ax + (k % columns) * POINT_GAP, ay + (k // columns) * POINT_GAP) for k in range(count)]
    shelf = Shelf(kind, tuple(round(v, 1) for v in box), (round(block[0], 1), round(block[1] - 7, 1)))
    return shelf, slots


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

    room = _Room(data)
    for x, y in board.taken:
        room.rect(x - POINT_ROOM, y - POINT_ROOM, x + POINT_ROOM, y + POINT_ROOM)
    groups = [[seat for seat in outer if seat.kind == kind] for kind in KIND_LABELS]
    # The largest shelf first, so it gets the most room; then the list's order.
    for group in sorted((g for g in groups if g), key=lambda g: -len(g)):
        found = _place_shelf(room, group[0].kind, len(group), data.width, data.height)
        if found is None:  # No block fits: round a corner, still never overlapping.
            slots = [board.near((SHELF_EDGE + SHELF_PAD, SHELF_EDGE + SHELF_PAD)) for _ in group]
        else:
            shelf, slots = found
            placement.shelves.append(shelf)
            slots = [board.take(slot) for slot in slots]
        for seat, (px, py) in zip(group, slots):
            placement.points[seat.seat_id] = SeatPoint(px, py, True)
    placement.shelves.sort(key=lambda shelf: list(KIND_LABELS).index(shelf.kind))

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
        # Where each kind's block and name sit; the screen takes the name
        # itself from the same place as the seat list's headings.
        "shelves": [{"kind": shelf.kind, "box": list(shelf.box), "label": list(shelf.label)}
                    for shelf in placement.shelves],
    }
