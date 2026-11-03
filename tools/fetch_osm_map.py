"""Fetch the map of Ebino from OpenStreetMap once, and write it to the repo
(SPEC 14-7, 14-65).

    python tools/fetch_osm_map.py

Two questions to the Overpass API: first the boundary of えびの市, then, in a
box 10 km wider than it on every side, 川内川, the place points, the
municipal boundaries and the school. The result is simplified and turned into
screen coordinates (an SVG viewBox), and written to mapdata/ebino_osm.json.
The app reads that file only; it never goes out while running.

Each question is sent by POST with a User-Agent naming this work. When the
server answers 502, 504 or 429, it is asked again after 1 minute, then after
3 minutes; if that fails too, overpass.kumi.systems is asked once. Any other
failure, or the last of those, stops the script and says so. With --keep DIR
the raw answers are kept outside the repo, and an answer already kept is read
back instead of asking again.
The file is derived from OpenStreetMap data and is under ODbL 1.0.
"""

import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
OUT_FILE = REPO_DIR / "mapdata" / "ebino_osm.json"
OVERPASS = "https://overpass-api.de/api/interpreter"
FALLBACK = "https://overpass.kumi.systems/api/interpreter"
USER_AGENT = "ebino-entaku/1.0 (Ebino Round Table: one-time map fetch for a school project)"
WAIT_SECONDS = 180  # How long one question may take.
RETRY_STATUS = (429, 502, 504)
RETRY_AFTER = (60, 180)  # Seconds before the 2nd and the 3rd try at the main server.

HOME = "えびの市"
RIVER = "川内川"
SCHOOL_WORD = "飯野高等学校"
WIDEN_KM = 10
ATTRIBUTION = "© OpenStreetMap contributors"
LICENSE = "ODbL 1.0 (Open Database License) https://opendatacommons.org/licenses/odbl/1-0/"

# Screen coordinates: the boundary spans WIDTH - 2 * PAD across, with PAD on
# every side for the seats around the rim.
WIDTH = 1000
PAD = 120
BOUNDARY_MAX_POINTS = 200
# Place kinds, the larger first: a name held twice in one municipality keeps
# the larger kind.
PLACE_RANK = ("city", "town", "village", "suburb", "quarter", "neighbourhood", "hamlet",
              "isolated_dwelling", "locality")


class Stop(Exception):
    pass


asked = 0
# --keep DIR: each answer is kept there (outside the repo), and read back
# instead of asking again when the script is run once more.
keep_dir: Path | None = None


def ask_once(url: str, query: str) -> str:
    global asked
    asked += 1
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST", headers={
        "User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(request, timeout=WAIT_SECONDS + 20) as response:
        return response.read().decode("utf-8")


def overpass(query: str, name: str) -> dict:
    kept = keep_dir / f"{name}.json" if keep_dir else None
    if kept and kept.exists():
        print(f"{name}: read the kept answer", flush=True)
        return json.loads(kept.read_text(encoding="utf-8"))
    tries = [(OVERPASS, 0)] + [(OVERPASS, wait) for wait in RETRY_AFTER] + [(FALLBACK, 0)]
    for k, (url, wait) in enumerate(tries):
        if wait:
            print(f"{name}: waiting {wait} s before asking again", flush=True)
            time.sleep(wait)
        print(f"{name}: asking {urllib.parse.urlsplit(url).netloc}", flush=True)
        try:
            raw = ask_once(url, query)
            answer = json.loads(raw)
        except urllib.error.HTTPError as error:
            if error.code in RETRY_STATUS and k + 1 < len(tries):
                print(f"{name}: HTTP {error.code}", flush=True)
                continue
            raise Stop(f"{name}: question {asked} to Overpass failed: HTTP {error.code}") from error
        except Exception as error:  # Network, a timeout or a broken answer.
            raise Stop(f"{name}: question {asked} to Overpass failed: {error}") from error
        if answer.get("remark") and not answer.get("elements"):
            raise Stop(f"{name}: Overpass answered with a remark only: {answer['remark']}")
        if kept:
            kept.write_text(raw, encoding="utf-8")
        return answer
    raise Stop(f"{name}: no answer")


# --- geometry on (lon, lat) ---

def join_ways(ways: list[list[tuple[float, float]]]) -> list[list[tuple[float, float]]]:
    """Join ways that share an end point into longer lines."""
    pending = [list(way) for way in ways if len(way) >= 2]
    ends: dict[tuple, set[int]] = {}
    for i, way in enumerate(pending):
        ends.setdefault(way[0], set()).add(i)
        ends.setdefault(way[-1], set()).add(i)
    used = [False] * len(pending)

    def take(i):
        used[i] = True
        ends[pending[i][0]].discard(i)
        ends[pending[i][-1]].discard(i)
        return pending[i]

    lines = []
    for i in range(len(pending)):
        if used[i]:
            continue
        line = list(take(i))
        for _ in range(2):  # Grow at the end, then turn round and grow at the other.
            while line[0] != line[-1]:
                nexts = sorted(j for j in ends.get(line[-1], ()) if not used[j])
                if not nexts:
                    break
                way = take(nexts[0])
                line += (way if way[0] == line[-1] else way[::-1])[1:]
            line.reverse()
        lines.append(line)
    return lines


def rings_of(relation: dict) -> list[list[tuple[float, float]]]:
    """A boundary relation's outer rings, closed."""
    ways = [[(p["lon"], p["lat"]) for p in member.get("geometry", []) if p]
            for member in relation.get("members", [])
            if member.get("type") == "way" and member.get("role") in ("outer", "")]
    return [line for line in join_ways(ways) if len(line) >= 4 and line[0] == line[-1]]


def area(ring) -> float:
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:])) / 2


def inside(point, rings) -> bool:
    x, y = point
    hit = False
    for ring in rings:
        for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                hit = not hit
    return hit


def simplify(points, epsilon):
    """Douglas-Peucker."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        (x1, y1), (x2, y2) = points[first], points[last]
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        far, far_at = -1.0, None
        for k in range(first + 1, last):
            x, y = points[k]
            d = (abs(dy * x - dx * y + x2 * y1 - y2 * x1) / length) if length else math.hypot(x - x1, y - y1)
            if d > far:
                far, far_at = d, k
        if far_at is not None and far > epsilon:
            keep[far_at] = True
            stack += [(first, far_at), (far_at, last)]
    return [p for p, k in zip(points, keep) if k]


def simplify_to(points, max_points):
    """The smallest tolerance that brings a closed ring to max_points or fewer."""
    low, high = 0.0, 50.0
    best = simplify(points, high)
    for _ in range(40):
        middle = (low + high) / 2
        trial = simplify(points, middle)
        if len(trial) <= max_points:
            best, high = trial, middle
        else:
            low = middle
    return best, high


def clip_line(line, box):
    """The parts of a line inside the box, each with one point beyond each end
    so the drawn line runs to the edge."""
    x0, y0, x1, y1 = box
    inside_box = [x0 <= x <= x1 and y0 <= y <= y1 for x, y in line]
    parts, current = [], []
    for k, point in enumerate(line):
        near = inside_box[k] or (k > 0 and inside_box[k - 1]) or (k + 1 < len(line) and inside_box[k + 1])
        if near:
            current.append(point)
        elif current:
            parts.append(current)
            current = []
    if current:
        parts.append(current)
    return [part for part in parts if len(part) >= 2]


def main(argv=None) -> int:
    global keep_dir
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2 and argv[0] == "--keep":
        keep_dir = Path(argv[1])
        keep_dir.mkdir(parents=True, exist_ok=True)
    elif argv:
        print("usage: python tools/fetch_osm_map.py [--keep DIR]", file=sys.stderr)
        return 2
    try:
        return run()
    except Stop as error:
        print(f"stopped: {error}", file=sys.stderr)
        print(f"questions to Overpass: {asked}", file=sys.stderr)
        return 1


def run() -> int:
    # 1. The boundary of えびの市.
    first = overpass(f'[out:json][timeout:{WAIT_SECONDS}];'
                     f'rel["boundary"="administrative"]["admin_level"="7"]["name"="{HOME}"];out geom;', "boundary")
    homes = [e for e in first.get("elements", []) if e.get("type") == "relation"]
    if len(homes) != 1:
        raise Stop(f"{HOME}'s boundary: {len(homes)} relations found, not 1")
    home_rings = rings_of(homes[0])
    if not home_rings:
        raise Stop(f"{HOME}'s boundary has no closed outer ring")
    ring = max(home_rings, key=lambda r: abs(area(r)))
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    west, east, south, north = min(lons), max(lons), min(lats), max(lats)

    # 2. In a box 10 km wider: the river, the places, the municipalities and the school.
    mid_lat = (south + north) / 2
    dlat = WIDEN_KM / 111.0
    dlon = WIDEN_KM / (111.0 * math.cos(math.radians(mid_lat)))
    s, w, n, e = south - dlat, west - dlon, north + dlat, east + dlon
    bbox = f"({s:.5f},{w:.5f},{n:.5f},{e:.5f})"
    second = overpass(
        f'[out:json][timeout:{WAIT_SECONDS}];('
        f'way["waterway"="river"]["name"="{RIVER}"]{bbox};'
        f'node["place"]["name"]{bbox};'
        f'rel["boundary"="administrative"]["admin_level"="7"]{bbox};'
        f'nwr["amenity"="school"]["name"~"{SCHOOL_WORD}"]{bbox};'
        f');out geom;', "around")
    elements = second.get("elements", [])

    municipalities = {}
    for element in elements:
        tags = element.get("tags", {})
        if element.get("type") == "relation" and tags.get("boundary") == "administrative" and tags.get("name"):
            rings = rings_of(element)
            if rings:
                municipalities[tags["name"]] = rings
    if HOME not in municipalities:
        municipalities[HOME] = home_rings

    river_ways = [[(p["lon"], p["lat"]) for p in element.get("geometry", [])]
                  for element in elements
                  if element.get("type") == "way" and element.get("tags", {}).get("waterway") == "river"]
    if not river_ways:
        raise Stop(f"{RIVER}: no ways found")

    schools = []
    for element in elements:
        if element.get("tags", {}).get("amenity") != "school":
            continue
        if element.get("type") == "node":
            point = (element["lon"], element["lat"])
        elif "bounds" in element:
            b = element["bounds"]
            point = ((b["minlon"] + b["maxlon"]) / 2, (b["minlat"] + b["maxlat"]) / 2)
        else:
            continue
        if inside(point, home_rings):
            schools.append(point)
    if len(schools) != 1:
        raise Stop(f"school with {SCHOOL_WORD} in its name inside {HOME}: {len(schools)} found, not 1")

    # Places by municipality, the point inside the polygon.
    places: dict[str, dict[str, tuple]] = {}
    for element in sorted((x for x in elements if x.get("type") == "node" and "place" in x.get("tags", {})),
                          key=lambda x: x["id"]):
        tags = element["tags"]
        name = tags["name"].strip().removeprefix("大字").strip()
        kind = tags["place"]
        if not name or kind not in PLACE_RANK:
            continue
        point = (element["lon"], element["lat"])
        owner = next((m for m, rings in sorted(municipalities.items()) if inside(point, rings)), None)
        if owner is None:
            continue
        table = places.setdefault(owner, {})
        if name in table and PLACE_RANK.index(table[name][2]) <= PLACE_RANK.index(kind):
            continue
        table[name] = (point[0], point[1], kind)

    # 3. Screen coordinates: x shrunk by the latitude, the boundary in the middle.
    shrink = math.cos(math.radians(mid_lat))
    scale = (WIDTH - 2 * PAD) / ((east - west) * shrink)
    height = (north - south) * scale + 2 * PAD

    def to_screen(lon, lat):
        return ((lon - west) * shrink * scale + PAD, (north - lat) * scale + PAD)

    def r(point):
        return [round(point[0], 1), round(point[1], 1)]

    screen_ring = [to_screen(*p) for p in ring]
    boundary, tolerance = simplify_to(screen_ring, BOUNDARY_MAX_POINTS)
    if boundary[0] == boundary[-1]:
        boundary = boundary[:-1]
    box = (0, 0, WIDTH, height)
    river = []
    for line in join_ways(river_ways):
        for part in clip_line([to_screen(*p) for p in line], box):
            river.append(simplify(part, tolerance))
    if not river:
        raise Stop(f"{RIVER}: nothing inside the map")

    out = {
        "source": ATTRIBUTION,
        "license": LICENSE,
        "fetched": date.today().isoformat(),
        "home": HOME,
        "viewbox": [0, 0, WIDTH, round(height, 1)],
        "boundary": [r(p) for p in boundary],
        "river": [[r(p) for p in line] for line in river],
        "places": {m: {name: r(to_screen(lon, lat)) + [kind] for name, (lon, lat, kind) in sorted(table.items())}
                   for m, table in sorted(places.items())},
        "school": r(to_screen(*schools[0])),
    }
    OUT_FILE.parent.mkdir(exist_ok=True)
    OUT_FILE.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    print(f"questions to Overpass: {asked}")
    print(f"boundary points {len(out['boundary'])} (from {len(ring)})")
    print(f"river lines {len(river)}  points {sum(len(line) for line in river)}")
    print(f"places {sum(len(t) for t in places.values())}  municipalities {len(places)} "
          f"({HOME} {len(places.get(HOME, {}))})")
    print(f"school found: {len(schools)}")
    print(f"wrote {OUT_FILE.relative_to(REPO_DIR)} ({OUT_FILE.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
