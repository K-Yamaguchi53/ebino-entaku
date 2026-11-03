"""Fetch the heights of the Ebino basin once, from Copernicus DEM GLO-30, and
write the coarse height grid to the repo (SPEC 14-66).

    python tools/fetch_copernicus_dem.py WORK_DIR

Needs numpy and Pillow (the app itself does not; they are imported only
when the heights are read).

The four 1°x1° tiles round the map (N31/N32, E130/E131, about 110 MB in
all) are taken from the public bucket copernicus-dem-30m on AWS (https, no
login) into WORK_DIR/tiles, which must be outside the repo. A tile already
there is used again instead of being fetched.

The heights are read in the map's own coordinates (mapdata/ebino_osm.json's
viewBox, made the same way as tools/fetch_osm_map.py: x shrunk by the
latitude, the boundary of えびの市 spanning WIDTH - 2 * PAD across, PAD on
every side). The boundary's box is not in the repo, so it is kept here as
numbers (BOUNDS); the script stops when they no longer give the map file's
viewBox.

Written to WORK_DIR (for tools/render_relief.py, never to the repo):
  heights.npy      metres, one value per map unit (about 1000 x 904)
  basin_mask.npy   1 inside the boundary of えびの市, 0 outside, a little blurred
Written to the repo:
  mapdata/relief_heights.json   every STEP-th value, in whole metres, with
                                the source line and the day the tiles were taken
"""

import json
import math
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
MAP_FILE = REPO_DIR / "mapdata" / "ebino_osm.json"
OUT_FILE = REPO_DIR / "mapdata" / "relief_heights.json"
BUCKET = "https://copernicus-dem-30m.s3.amazonaws.com"
TILES = ("N31_00_E130_00", "N31_00_E131_00", "N32_00_E130_00", "N32_00_E131_00")
USER_AGENT = "ebino-entaku/1.0 (Ebino Round Table: one-time elevation fetch for a school project)"
# The text Copernicus asks for on a product made from the DEM, word for word.
SOURCE = ("produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH "
          "2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved")

# The box round the boundary of えびの市 that tools/fetch_osm_map.py measured
# (south, north, west, east in degrees), and its screen coordinates.
BOUNDS = (31.9339410, 32.1335940, 130.7033771, 130.9733180)
WIDTH, PAD = 1000, 120
STEP = 10  # The grid in the repo: one value every STEP map units.
MASK_BLUR = 3


class Stop(Exception):
    pass


def tile_name(tile: str) -> str:
    return f"Copernicus_DSM_COG_10_{tile}_DEM"


def fetch_tile(tile: str, folder: Path) -> Path:
    """The tile's GeoTIFF in folder, fetched when it is not there yet."""
    path = folder / f"{tile_name(tile)}.tif"
    if path.exists() and path.stat().st_size > 0:
        print(f"{tile}: kept ({path.stat().st_size // 1_000_000} MB)", flush=True)
        return path
    url = f"{BUCKET}/{tile_name(tile)}/{tile_name(tile)}.tif"
    part = path.with_suffix(".part")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=120) as response, part.open("wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)
    with part.open("rb") as check:
        if check.read(4) not in (b"II*\x00", b"MM\x00*"):
            part.unlink()
            raise Stop(f"{tile}: the answer is not a TIFF")
    part.replace(path)
    print(f"{tile}: fetched ({path.stat().st_size // 1_000_000} MB, {time.monotonic() - started:.0f} s)",
          flush=True)
    return path


def screen():
    """(height of the viewBox, map (x, y) -> (lon, lat)), as fetch_osm_map.py makes them."""
    south, north, west, east = BOUNDS
    shrink = math.cos(math.radians((south + north) / 2))
    scale = (WIDTH - 2 * PAD) / ((east - west) * shrink)
    height = (north - south) * scale + 2 * PAD

    def to_lonlat(x, y):
        return (x - PAD) / (shrink * scale) + west, north - (y - PAD) / scale

    return height, to_lonlat


def heights(paths: dict[str, Path], width: float, height: float, to_lonlat):
    """Metres at every whole map unit, read between the four nearest posts.
    A tile's posts are 1/n degree apart, the first at its north-west corner."""
    import numpy as np
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
    tiles = {tile: np.asarray(Image.open(path), dtype=np.float32) for tile, path in paths.items()}
    n = tiles[TILES[0]].shape[0]
    if any(a.shape != (n, n) for a in tiles.values()):
        raise Stop("the four tiles are not the same size")
    # North up: the N32 tiles on top, E130 on the left.
    mosaic = np.block([[tiles["N32_00_E130_00"], tiles["N32_00_E131_00"]],
                       [tiles["N31_00_E130_00"], tiles["N31_00_E131_00"]]])
    mosaic = np.nan_to_num(mosaic, nan=0.0)
    lon0, lat_top = 130.0, 33.0
    xs = np.arange(0, math.floor(width) + 1, 1.0)
    ys = np.arange(0, math.ceil(height) + 1, 1.0)
    lon, lat = to_lonlat(*np.meshgrid(xs, ys))
    px, py = (lon - lon0) * n, (lat_top - lat) * n
    ix, iy = np.floor(px).astype(int), np.floor(py).astype(int)
    if ix.min() < 0 or iy.min() < 0 or ix.max() + 1 >= mosaic.shape[1] or iy.max() + 1 >= mosaic.shape[0]:
        raise Stop("the map runs off the four tiles")
    fx, fy = px - ix, py - iy
    return (mosaic[iy, ix] * (1 - fx) * (1 - fy) + mosaic[iy, ix + 1] * fx * (1 - fy)
            + mosaic[iy + 1, ix] * (1 - fx) * fy + mosaic[iy + 1, ix + 1] * fx * fy).astype(np.float32)


def basin_mask(boundary, shape):
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter

    image = Image.new("L", (shape[1], shape[0]), 0)
    ImageDraw.Draw(image).polygon([tuple(p) for p in boundary], fill=255)
    image = image.filter(ImageFilter.GaussianBlur(MASK_BLUR))
    return np.asarray(image, dtype=np.float32) / 255


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python tools/fetch_copernicus_dem.py WORK_DIR", file=sys.stderr)
        return 2
    work = Path(argv[0]).resolve()
    if work == REPO_DIR or REPO_DIR in work.parents:
        print("WORK_DIR must be outside the repo (the tiles are about 110 MB)", file=sys.stderr)
        return 2
    try:
        return run(work)
    except Stop as stop:
        print(f"stopped: {stop}", file=sys.stderr)
        return 1


def run(work: Path) -> int:
    import numpy as np

    drawing = json.loads(MAP_FILE.read_text(encoding="utf-8"))
    _, _, width, map_height = drawing["viewbox"]
    height, to_lonlat = screen()
    if width != WIDTH or abs(height - map_height) > 0.06:
        raise Stop(f"BOUNDS give a viewBox of {WIDTH} x {height:.1f}, the map file has {width} x {map_height}")

    tile_dir = work / "tiles"
    tile_dir.mkdir(parents=True, exist_ok=True)
    paths = {tile: fetch_tile(tile, tile_dir) for tile in TILES}
    # The day the tiles were taken: the newest of the four.
    fetched = max(date.fromtimestamp(path.stat().st_mtime) for path in paths.values()).isoformat()

    grid = heights(paths, width, map_height, to_lonlat)
    np.save(work / "heights.npy", grid)
    np.save(work / "basin_mask.npy", basin_mask(drawing["boundary"], grid.shape))
    coarse = grid[::STEP, ::STEP]
    out = {
        "source": SOURCE,
        "dem": "Copernicus DEM GLO-30 (" + ", ".join(TILES) + ")",
        "fetched": fetched,
        "viewbox": [0, 0, width, map_height],
        "step": STEP,
        "rows": [[int(round(float(v))) for v in row] for row in coarse],
    }
    OUT_FILE.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"grid {grid.shape[1]} x {grid.shape[0]}  metres {grid.min():.0f} to {grid.max():.0f}")
    print(f"wrote {work / 'heights.npy'} and basin_mask.npy (outside the repo)")
    print(f"wrote {OUT_FILE.relative_to(REPO_DIR)} ({OUT_FILE.stat().st_size} bytes, "
          f"{coarse.shape[1]} x {coarse.shape[0]} values)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
