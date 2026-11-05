"""The school's building as a 3D picture on the map (直し25-1).

The pictures are not in the repo: they stay in the folder EBINO_SCHOOL_DIR
names (or its sprite/ folder) until the school allows them to be published.
Only these three files are read there, nothing else:

    school_relief.png   the building as the relief picture's camera sees it
    school_flat.png     the building as the flat map's camera sees it
    school_yard.png     the building and its sports ground, large, for the
                        right of the screen (直し33-2), seen as the map is
    school_sprite.json  for the two small pictures, the spot in each (px)
                        that is the school's point on the map
                        ("school_point_px"); for the large one, where seats
                        go on it: the ring's windows ("windows_px") and the
                        ground's four corners ("field_px"); and, to put it
                        on the map put larger (直し37-1: SCHOOL_SCALE times
                        its real size in static/map.js), its pixels to
                        a metre across ("px_per_m") and the ring's middle
                        on the ground ("ring_centre_px"), the school's
                        point on the map

The pictures are drawn at about twice the size they are shown. With no
folder, a missing or broken file, the school keeps its line mark and the
right of the screen a plain drawing of a building and a ground, as before.
"""

import json
import math
import os
import struct
from pathlib import Path

ENV = "EBINO_SCHOOL_DIR"
SPRITE = "school_sprite.json"
PICTURES = {"relief": "school_relief.png", "flat": "school_flat.png", "yard": "school_yard.png"}
YARD_MOST_WINDOWS = 200  # More is not a picture this app drew.
URL = "/school/"  # Each picture is served at URL + its file name, from the folder only.
PNG_HEAD = b"\x89PNG\r\n\x1a\n"


def folder_from_env() -> Path | None:
    """The folder EBINO_SCHOOL_DIR names, or its sprite/ folder when the
    files are there; None when it is not set or holds no sprite file."""
    value = os.environ.get(ENV, "").strip()
    if not value:
        return None
    for folder in (Path(value), Path(value) / "sprite"):
        if (folder / SPRITE).is_file():
            return folder
    return None


def png_size(data: bytes) -> tuple[int, int]:
    """A PNG's width and height, from its IHDR chunk."""
    if data[:8] != PNG_HEAD or data[12:16] != b"IHDR":
        raise ValueError("not a PNG")
    width, height = struct.unpack(">II", data[16:24])
    if not (0 < width <= 4096 and 0 < height <= 4096):
        raise ValueError("a PNG of a size not drawn")
    return width, height


def _number(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("not a number")
    return float(value)


def _picture(folder: Path, kind: str, about: dict) -> dict | None:
    name = PICTURES[kind]
    try:
        width, height = png_size((folder / name).read_bytes())
        entry = about[kind]
        point = [_number(v) for v in entry["school_point_px"]]
        if len(point) != 2:
            raise ValueError("a point has two numbers")
        # The point as on the picture itself, should its size differ from the file's.
        said = (_number(entry.get("width", width)), _number(entry.get("height", height)))
        point = [point[0] * width / said[0], point[1] * height / said[1]]
    except (OSError, ValueError, KeyError, TypeError, IndexError, ZeroDivisionError):
        return None
    if not (0 <= point[0] <= width and 0 <= point[1] <= height):
        return None
    return {"image": URL + name, "width": width, "height": height, "point": [round(v, 2) for v in point]}


def _points(value, most: int) -> list[list[float]]:
    if not isinstance(value, list) or not 0 < len(value) <= most:
        raise ValueError("not a list of points")
    out = []
    for point in value:
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError("a point has two numbers")
        out.append([round(_number(v), 2) for v in point])
    return out


def _yard(folder: Path, about: dict) -> dict | None:
    """The large picture of the building and its ground (直し33-2), with
    where its seats go, or None."""
    try:
        width, height = png_size((folder / PICTURES["yard"]).read_bytes())
        entry = about["yard"]
        windows = _points(entry["windows_px"], YARD_MOST_WINDOWS)
        field = _points(entry["field_px"], 4)
        if len(field) != 4:
            raise ValueError("a ground has four corners")
        ring = _points([entry["ring_centre_px"]], 1)[0]
        px_per_m = _number(entry["px_per_m"])
        if not px_per_m > 0:
            raise ValueError("a scale is more than nothing")
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if not all(0 <= x <= width and 0 <= y <= height for x, y in windows + field + [ring]):
        return None
    return {"image": URL + PICTURES["yard"], "width": width, "height": height, "windows": windows, "field": field,
            "ring": ring, "px_per_m": px_per_m}


def load(folder: Path | None) -> dict | None:
    """{"relief", "flat", "yard": picture or None} for the screen, the
    first two {"image", "width", "height", "point"}, the yard {"image",
    "width", "height", "windows", "field", "ring", "px_per_m"}; None with none."""
    if folder is None:
        return None
    try:
        about = json.loads((folder / SPRITE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(about, dict):
        return None
    pictures = {kind: _picture(folder, kind, about) for kind in ("relief", "flat")}
    pictures["yard"] = _yard(folder, about)
    return pictures if any(pictures.values()) else None


class SchoolPicture:
    """The pictures found at start-up, and where to serve them from."""

    def __init__(self, folder: Path | None):
        self.view = load(folder)
        self.folder = folder if self.view else None

    def file(self, path: str) -> bytes | None:
        """The bytes for URL + a picture's name, or None (any other path)."""
        if self.folder is None or not path.startswith(URL):
            return None
        name = path[len(URL):]
        kind = next((kind for kind, file in PICTURES.items() if file == name), None)
        if kind is None or not self.view.get(kind):
            return None
        try:
            return (self.folder / name).read_bytes()
        except OSError:
            return None

    def report(self) -> str:
        """The start-up line: which pictures there are."""
        if not self.view:
            return "校舎の絵なし（線の印）"
        return "校舎の絵あり（" + "・".join(kind for kind, picture in self.view.items() if picture) + "）"
