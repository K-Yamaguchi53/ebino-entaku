"""The ground round the map's picture (直し41の続き 段4): mapdata/relief.webp
made small, mirrored on all four sides (three times as wide and as tall,
the picture itself in the middle), blurred and darkened toward the night's
colour, saved as mapdata/relief_blur.webp. The screen lays it under the
picture, as large as it, so the frame has no empty black round the map; it
is made here once, not blurred on the screen (Chromebooks are slow at it).

    python tools/make_relief_blur.py

Reads and writes mapdata/ only; nothing is fetched.
"""

from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

MAPDATA = Path(__file__).resolve().parent.parent / "mapdata"
SOURCE = MAPDATA / "relief.webp"
OUT = MAPDATA / "relief_blur.webp"
SHRINK = 3  # A third of the size: the ridges still show under a light blur.
BLUR = 3  # Gaussian radius, in the small picture's pixels: soft, its ridges kept.
# The picture's own edges are see-through or black (the render's margin):
# cut off before it is mirrored, so the ground goes on from the land itself.
EDGE = (0.016, 0.06, 0.016, 0.07)  # left, top, right, bottom, of the size.
NIGHT = (11, 19, 38)  # style.css --night: where the picture is see-through.
GROUND = (24, 38, 74)  # style.css --night-3: what the picture is laid over.
LIFT = 1.15  # A little lighter than the picture: land, not black; the seam still soft.
KEEP = 0.86  # How much of the picture is left over the ground.


def make(source: Path = SOURCE, out: Path = OUT) -> Path:
    picture = Image.open(source).convert("RGBA")
    w, h = picture.width // SHRINK, picture.height // SHRINK
    left, top, right, bottom = EDGE
    land = picture.crop((round(picture.width * left), round(picture.height * top),
                         round(picture.width * (1 - right)), round(picture.height * (1 - bottom))))
    small = land.resize((w, h), Image.Resampling.LANCZOS)
    # Where the picture is see-through, the night.
    ground = Image.new("RGBA", (w, h), NIGHT + (255,))
    small = Image.alpha_composite(ground, small).convert("RGB")
    across, down = ImageOps.mirror(small), ImageOps.flip(small)
    both = ImageOps.flip(across)
    tiles = [[both, down, both], [across, small, across], [both, down, both]]
    sheet = Image.new("RGB", (3 * w, 3 * h))
    for row, line in enumerate(tiles):
        for col, tile in enumerate(line):
            sheet.paste(tile, (col * w, row * h))
    sheet = sheet.filter(ImageFilter.GaussianBlur(BLUR))
    sheet = ImageEnhance.Brightness(sheet).enhance(LIFT)
    sheet = Image.blend(Image.new("RGB", sheet.size, GROUND), sheet, KEEP)
    sheet.save(out, "WEBP", quality=70, method=6)
    return out


if __name__ == "__main__":
    made = make()
    print(f"{made.name} {made.stat().st_size} bytes")
