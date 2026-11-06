"""The basin drawn as a model, seen from the south with north up as on an
ordinary map (直し31-4), under the map (SPEC 14-66).

Three files in the repo, made once by tools/fetch_copernicus_dem.py and
tools/render_relief.py; nothing is fetched while the app runs:
  mapdata/relief.webp             the picture
  mapdata/relief_projection.json  map (x, y, z) -> the picture's pixel
  mapdata/relief_heights.json     a coarse grid of heights in metres, with
                                  the Copernicus source line

The seats' points are placed by seat_map.py as before; the screen moves
them onto the picture by itself. When any of the three is missing, cannot be
read, or does not fit the map, there is no picture and the screen keeps the
flat map (and with no map, the seat list): the app still starts. Nothing here
holds a seat's words.

The seasons (the teacher, 11/6): the same model at dusk in spring and in
autumn, mapdata/relief_<season>.webp with its blurred ground
relief_blur_<season>.webp (tools/render_relief.py, tools/make_relief_blur.py),
switched on the screen. Each is offered only when both files are there and
the picture is the night's size (the same camera): else the night alone.
"""

import json
import math
from pathlib import Path

RELIEF_DIR = Path(__file__).resolve().parent.parent / "mapdata"
IMAGE = "relief.webp"
PROJECTION = "relief_projection.json"
HEIGHTS = "relief_heights.json"
IMAGE_PATH = "/relief.webp"  # Where the screen asks for the picture.
BLUR_PATH = "/relief_blur.webp"  # The night's ground round it (make_relief_blur.py).
MAX_IMAGE_BYTES = 1_000_000
SEASONS = ("spring", "autumn")  # Besides the night, in the switch's order.


def season_files(season: str) -> tuple[str, str]:
    """The season's picture and its ground, as named in mapdata/ and served."""
    return f"relief_{season}.webp", f"relief_blur_{season}.webp"


def looks(folder: Path, size: tuple[int, int]) -> list[dict]:
    """The pictures the screen may switch between: the night first, then
    each season whose two files are there and whose picture is the night's
    size (a season that is not is left out, never shown misplaced)."""
    found = [{"id": "night", "image": IMAGE_PATH, "blur": BLUR_PATH}]
    for season in SEASONS:
        image, blur = season_files(season)
        try:
            data = (folder / image).read_bytes()
            if not (folder / blur).is_file() or len(data) > MAX_IMAGE_BYTES or webp_size(data) != size:
                continue
        except (OSError, ValueError):
            continue
        found.append({"id": season, "image": f"/{image}", "blur": f"/{blur}"})
    return found


def _number(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("not a number")
    return float(value)


def webp_size(data: bytes) -> tuple[int, int]:
    """A WebP's width and height from its header; ValueError when it is not one."""
    if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError("not a WebP")
    chunk = data[12:16]
    if chunk == b"VP8X":
        return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little")
    if chunk == b"VP8L" and data[20] == 0x2F:
        bits = int.from_bytes(data[21:25], "little")
        return 1 + (bits & 0x3FFF), 1 + ((bits >> 14) & 0x3FFF)
    if chunk == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
        return int.from_bytes(data[26:28], "little") & 0x3FFF, int.from_bytes(data[28:30], "little") & 0x3FFF
    raise ValueError("unknown WebP")


def parse_relief(image: bytes, projection: dict, heights: dict, viewbox: tuple[float, float]) -> dict:
    """What the screen gets; ValueError (or KeyError, TypeError) on anything
    malformed or not fitting the map's viewBox (width, height)."""
    width_px, height_px = (int(v) for v in projection["res"])
    if width_px <= 0 or height_px <= 0 or len(image) > MAX_IMAGE_BYTES:
        raise ValueError("bad picture")
    if webp_size(image) != (width_px, height_px):
        raise ValueError("the picture is not the size the projection says")
    px = [_number(v) for v in projection["px"]]
    py = [_number(v) for v in projection["py"]]
    z = projection["z"]
    z = {"base_m": _number(z["base_m"]), "m_per_unit": _number(z["m_per_unit"]), "exag": _number(z["exag"])}
    if len(px) != 4 or len(py) != 4 or z["m_per_unit"] <= 0 or z["exag"] <= 0:
        raise ValueError("bad projection")
    step = _number(heights["step"])
    rows = [[_number(v) for v in row] for row in heights["rows"]]
    source = heights["source"]
    if not isinstance(source, str) or not source.strip() or step <= 0:
        raise ValueError("no source")
    if len(rows) < 2 or len(rows[0]) < 2 or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("bad grid")
    _, _, width, height = (_number(v) for v in heights["viewbox"])
    # The grid must cover the map it was made for.
    if (abs(width - viewbox[0]) > 0.5 or abs(height - viewbox[1]) > 0.5
            or (len(rows[0]) - 1) * step < width - step or (len(rows) - 1) * step < height - step):
        raise ValueError("the grid is not the map's")
    return {"image": IMAGE_PATH, "res": [width_px, height_px], "px": px, "py": py, "z": z,
            "step": step, "rows": rows, "source": source.strip()}


def load_relief(viewbox: tuple[float, float], folder: Path | None = None) -> dict | None:
    """None when a file is missing, cannot be read or does not fit: the flat
    map is shown, and the app starts all the same."""
    folder = folder or RELIEF_DIR
    try:
        data = parse_relief((folder / IMAGE).read_bytes(),
                            json.loads((folder / PROJECTION).read_text(encoding="utf-8")),
                            json.loads((folder / HEIGHTS).read_text(encoding="utf-8")), viewbox)
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError):
        return None
    data["looks"] = looks(folder, tuple(data["res"]))
    return data
