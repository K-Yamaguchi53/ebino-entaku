"""Draw the basin as a model in the night, seen from the south, north up (SPEC 14-66, 直し31-4).
Run in Blender, after tools/fetch_copernicus_dem.py:

    blender -b --python tools/render_relief.py -- WORK_DIR [WIDTH_PX] [SAMPLES] [SEASON]

SEASON is night (the default), spring or autumn (the teacher, 11/6: the
basin's seasons, switched on the screen). Spring and autumn are the same
model and camera at dusk, coloured by height only: the paddies on the
basin's floor, the forests on the slopes, the plateau and the peaks. There
is no map of fields and forests here, so the colours are likely ones, not
the land as it is. They are written as mapdata/relief_<season>.webp; the
projection stays the night's (the same camera: checked, not written).

WORK_DIR holds heights.npy and basin_mask.npy (outside the repo); the full
picture is drawn there too (relief.png). Written to the repo:
  mapdata/relief.webp             the picture, made small
  mapdata/relief_projection.json  map (x, y, z) -> the picture's pixel

The map's coordinates (x right, y down, 1 unit about 33.4 m) are put at
Blender's X = x, Y = -y; a height is (metres - BASE_M) / M_PER_UNIT, EXAG times.
The camera is orthographic and looks north from the south, ELEV_DEG down,
as an ordinary map is read: north at the top, east on the right, Kirishima
in front at the bottom and Hitoyoshi's side at the back. The moon lights it
from the screen's upper left (the north-west), so the hills stand out and
are not read as hollows.
Cycles on the CPU; nothing here needs more than the numpy Blender carries.
"""

import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Vector

REPO_DIR = Path(__file__).resolve().parent.parent
OUT_IMAGE = REPO_DIR / "mapdata" / "relief.webp"
SEASONS = ("night", "spring", "autumn")
OUT_PROJECTION = REPO_DIR / "mapdata" / "relief_projection.json"

BASE_M, M_PER_UNIT, EXAG = 140.0, 33.4225, 2.2
STEP = 2  # Every STEP-th height becomes a vertex.
SKIRT = -14.0  # The model's bottom.
ELEV_DEG = 52.0  # How far the camera looks down.
MARGIN = 1.03
WEBP_QUALITY = 72


def socket(sockets, identifier):
    """A socket by its identifier: a Mix node has an A, a B and a Result for
    each data type, all of the same name."""
    return next(s for s in sockets if s.identifier == identifier)


def terrain(heights, mask):
    """The top (smooth) with its sides and bottom: a block cut out of the ground."""
    rows, cols = heights.shape
    z = (heights - BASE_M) / M_PER_UNIT * EXAG
    gx, gy = np.meshgrid(np.arange(cols) * STEP, np.arange(rows) * STEP)
    top = np.stack([gx.ravel(), -gy.ravel(), z.ravel()], axis=1)
    ring = ([(0, c) for c in range(cols)] + [(r, cols - 1) for r in range(1, rows)]
            + [(rows - 1, c) for c in range(cols - 2, -1, -1)] + [(r, 0) for r in range(rows - 2, 0, -1)])
    ring_idx = [r * cols + c for r, c in ring]
    bottom = top[ring_idx].copy()
    bottom[:, 2] = SKIRT
    verts = np.concatenate([top, bottom])
    faces = [(r * cols + c, (r + 1) * cols + c, (r + 1) * cols + c + 1, r * cols + c + 1)
             for r in range(rows - 1) for c in range(cols - 1)]
    nb, n = len(top), len(ring_idx)
    faces += [(ring_idx[k], ring_idx[(k + 1) % n], nb + (k + 1) % n, nb + k) for k in range(n)]
    faces.append(tuple(range(nb + n - 1, nb - 1, -1)))
    mesh = bpy.data.meshes.new("terrain")
    mesh.from_pydata(verts.tolist(), [], faces)
    mesh.update()
    for i, polygon in enumerate(mesh.polygons):
        polygon.use_smooth = i < (rows - 1) * (cols - 1)
    # Where the basin is, for the floor's warm tint.
    attribute = mesh.attributes.new("basin", "FLOAT", "POINT")
    attribute.data.foreach_set("value", np.concatenate([mask.ravel(), np.zeros(n)]).astype(np.float32))
    return mesh, verts


# Each season: the colours by height (where, linear RGB) from the basin's
# floor (0) to 1700 m (1); the basin's floor mixed toward its own colour by
# how much; the steep sides' dark; the lights (name, energy, colour, angles);
# the sky (colour, strength). The night is as it was (直し31-4).
# Heights at a glance: the floor about 230 m (0.06), the hills round it 400
# to 800 m (0.17 to 0.42), the Ebino plateau about 1200 m (0.68), the
# Kirishima peaks to 1700 m (1).
LOOKS = {
    "night": {
        "ramp": [(0.0, (0.035, 0.065, 0.12)), (0.35, (0.075, 0.12, 0.19)), (1.0, (0.20, 0.25, 0.34))],
        "basin": ((0.13, 0.14, 0.17), 0.25),
        "side": (0.012, 0.02, 0.035),
        "lights": (("moon", 1.15, (0.72, 0.80, 1.0), (62, 0, -118)), ("rim", 0.35, (1.0, 0.86, 0.6), (70, 0, 135))),
        "sky": ((0.012, 0.022, 0.045), 0.22),
    },
    # Spring at dusk. The floor's fields (below about 290 m) young green;
    # above, the slopes' fresh green with the dark of cedars and evergreens
    # in patches (most of a Kyushu hillside); the peaks pink (ミヤマキリシマ).
    "spring": {
        "ramp": [(0.0, (0.17, 0.23, 0.07)), (0.085, (0.15, 0.21, 0.06)), (0.12, (0.11, 0.21, 0.05)),
                 (0.60, (0.12, 0.22, 0.05)), (0.72, (0.14, 0.20, 0.07)), (0.84, (0.30, 0.12, 0.19)),
                 (1.0, (0.20, 0.13, 0.14))],
        "forest": ((0.035, 0.075, 0.035), 0.12),
        "basin": ((0.17, 0.23, 0.07), 0.15),
        "side": (0.018, 0.022, 0.02),
        "lights": (("sun", 3.0, (1.0, 0.88, 0.76), (70, 0, -112)), ("rim", 0.5, (0.6, 0.68, 1.0), (70, 0, 135))),
        "sky": ((0.08, 0.09, 0.14), 0.5),
    },
    # Autumn at dusk. The floor's rice golden; above, the slopes' red,
    # orange and yellow showing in patches among the dark green; the
    # plateau's grass gold; the peaks bare.
    "autumn": {
        "ramp": [(0.0, (0.36, 0.26, 0.07)), (0.085, (0.32, 0.23, 0.06)), (0.12, (0.42, 0.05, 0.015)),
                 (0.30, (0.46, 0.10, 0.015)), (0.44, (0.50, 0.20, 0.02)), (0.58, (0.50, 0.34, 0.04)),
                 (0.70, (0.42, 0.32, 0.11)), (0.86, (0.19, 0.13, 0.09)), (1.0, (0.15, 0.11, 0.09))],
        "forest": ((0.035, 0.07, 0.03), 0.0),
        "patches": (0.43, 0.50),
        "basin": ((0.36, 0.26, 0.07), 0.15),
        "side": (0.022, 0.016, 0.012),
        "lights": (("sun", 3.0, (1.0, 0.86, 0.72), (70, 0, -112)), ("rim", 0.5, (0.6, 0.68, 1.0), (70, 0, 135))),
        "sky": ((0.08, 0.09, 0.14), 0.5),
    },
}


def night_material(season="night"):
    """Colour by height, the basin's floor its own colour, the sides dark."""
    look = LOOKS[season]
    material = bpy.data.materials.new(season)
    material.use_nodes = True
    nt = material.node_tree
    for node in list(nt.nodes):
        nt.nodes.remove(node)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.92
    geometry = nt.nodes.new("ShaderNodeNewGeometry")
    position = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geometry.outputs["Position"], position.inputs[0])
    by_height = nt.nodes.new("ShaderNodeMapRange")
    by_height.inputs["From Min"].default_value = 0.0
    by_height.inputs["From Max"].default_value = (1700 - BASE_M) / M_PER_UNIT * EXAG
    nt.links.new(position.outputs["Z"], by_height.inputs["Value"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    stops = ramp.color_ramp.elements
    first, *middle, last = look["ramp"]
    stops[0].position, stops[0].color = first[0], (*first[1], 1)
    stops[1].position, stops[1].color = last[0], (*last[1], 1)
    for at, colour in middle:
        stops.new(at).color = (*colour, 1)
    nt.links.new(by_height.outputs["Result"], ramp.inputs["Fac"])
    leaves = ramp.outputs["Color"]
    if "forest" in look:
        # The cedars: dark green in patches over the leaves' colour, as a
        # wooded slope is (a noise over the model's place, a few hundred
        # metres across; the same seedless pattern every time): where the
        # noise is low all cedar, where it is high the leaves with only
        # `share` of cedar; none on the floor's fields (below 0.085).
        cedar, share = look["forest"]
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 0.045
        noise.inputs["Detail"].default_value = 4.0
        nt.links.new(geometry.outputs["Position"], noise.inputs["Vector"])
        patches = nt.nodes.new("ShaderNodeMapRange")
        # Where the noise turns from cedar to leaves: spring blends wide;
        # autumn narrow and with fewer cedars, its reds kept clear.
        patches.inputs["From Min"].default_value, patches.inputs["From Max"].default_value = \
            look.get("patches", (0.40, 0.64))
        patches.inputs["To Min"].default_value = 1.0
        patches.inputs["To Max"].default_value = share
        nt.links.new(noise.outputs["Fac"], patches.inputs["Value"])
        above_fields = nt.nodes.new("ShaderNodeMapRange")
        above_fields.inputs["From Min"].default_value = 0.085
        above_fields.inputs["From Max"].default_value = 0.12
        nt.links.new(by_height.outputs["Result"], above_fields.inputs["Value"])
        only_above = nt.nodes.new("ShaderNodeMath")
        only_above.operation = "MULTIPLY"
        nt.links.new(patches.outputs["Result"], only_above.inputs[0])
        nt.links.new(above_fields.outputs["Result"], only_above.inputs[1])
        wooded = nt.nodes.new("ShaderNodeMix")
        wooded.data_type = "RGBA"
        socket(wooded.inputs, "B_Color").default_value = (*cedar, 1)
        nt.links.new(leaves, socket(wooded.inputs, "A_Color"))
        nt.links.new(only_above.outputs[0], socket(wooded.inputs, "Factor_Float"))
        leaves = socket(wooded.outputs, "Result_Color")

    basin = nt.nodes.new("ShaderNodeAttribute")
    basin.attribute_name = "basin"
    warm = nt.nodes.new("ShaderNodeMix")
    warm.data_type = "RGBA"
    floor, floor_share = look["basin"]
    socket(warm.inputs, "B_Color").default_value = (*floor, 1)
    nt.links.new(leaves, socket(warm.inputs, "A_Color"))
    how_warm = nt.nodes.new("ShaderNodeMath")
    how_warm.operation = "MULTIPLY"
    how_warm.inputs[1].default_value = floor_share
    nt.links.new(basin.outputs["Fac"], how_warm.inputs[0])
    nt.links.new(how_warm.outputs[0], socket(warm.inputs, "Factor_Float"))

    normal = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geometry.outputs["Normal"], normal.inputs[0])
    facing_up = nt.nodes.new("ShaderNodeMapRange")
    facing_up.inputs["From Min"].default_value = 0.2
    facing_up.inputs["From Max"].default_value = 0.6
    nt.links.new(normal.outputs["Z"], facing_up.inputs["Value"])
    dark = nt.nodes.new("ShaderNodeMix")
    dark.data_type = "RGBA"
    socket(dark.inputs, "A_Color").default_value = (*look["side"], 1)
    nt.links.new(facing_up.outputs["Result"], socket(dark.inputs, "Factor_Float"))
    nt.links.new(socket(warm.outputs, "Result_Color"), socket(dark.inputs, "B_Color"))
    nt.links.new(socket(dark.outputs, "Result_Color"), bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return material


def lights(scene, season="night"):
    """The moon (at dusk, a low warm sun) from the north-west (the screen's
    upper left); a weaker rim from the north-east (the upper right), never
    from the front, so no slope is lit from below; a faint sky."""
    look = LOOKS[season]
    for name, energy, colour, angles in look["lights"]:
        light = bpy.data.lights.new(name, "SUN")
        light.energy, light.color = energy, colour
        light.angle = math.radians(1.5)
        sun = bpy.data.objects.new(name, light)
        sun.rotation_euler = Euler(tuple(math.radians(a) for a in angles))
        scene.collection.objects.link(sun)
    world = bpy.data.worlds.new(season)
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    sky, strength = look["sky"]
    background.inputs["Color"].default_value = (*sky, 1)
    background.inputs["Strength"].default_value = strength
    scene.world = world


def camera(scene, verts, width_px):
    """An orthographic camera framing the whole block; returns the projection."""
    data = bpy.data.cameras.new("camera")
    data.type = "ORTHO"
    cam = bpy.data.objects.new("camera", data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    # Looking north (Blender's +Y is the map's north): north at the picture's top.
    cam.rotation_euler = Euler((math.radians(90 - ELEV_DEG), 0, 0))
    bpy.context.view_layer.update()
    rotation = cam.matrix_world.to_3x3()
    right, up, back = Vector(rotation.col[0]), Vector(rotation.col[1]), Vector(rotation.col[2])
    xc, yc = verts @ np.array(right), verts @ np.array(up)
    w, h = xc.max() - xc.min(), yc.max() - yc.min()
    cxc, cyc = (xc.max() + xc.min()) / 2, (yc.max() + yc.min()) / 2
    ortho = w * MARGIN
    height_px = int(round(width_px * h * MARGIN / ortho))
    cam.location = right * cxc + up * cyc + back * 3000
    data.ortho_scale = ortho
    data.clip_end = 10000
    scene.render.resolution_x, scene.render.resolution_y = width_px, height_px
    scene.render.resolution_percentage = 100
    # The map's (x, y, z) at Blender's (x, -y, z), to the picture's pixel.
    k = width_px / ortho
    return {
        "res": [width_px, height_px],
        "px": [k * right.x, -k * right.y, k * right.z, width_px / 2 - k * cxc],
        "py": [-k * up.x, k * up.y, -k * up.z, height_px / 2 + k * cyc],
        "z": {"base_m": BASE_M, "m_per_unit": M_PER_UNIT, "exag": EXAG},
    }


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        print("usage: blender -b --python tools/render_relief.py -- WORK_DIR [WIDTH_PX] [SAMPLES] [SEASON]",
              file=sys.stderr)
        return 2
    season = argv[3] if len(argv) > 3 else "night"
    if season not in SEASONS:
        print(f"SEASON is one of {', '.join(SEASONS)}", file=sys.stderr)
        return 2
    out_image = OUT_IMAGE if season == "night" else OUT_IMAGE.with_name(f"relief_{season}.webp")
    work = Path(argv[0]).resolve()
    width_px = int(argv[1]) if len(argv) > 1 else 2400
    samples = int(argv[2]) if len(argv) > 2 else 32
    started = time.monotonic()
    heights = np.load(work / "heights.npy")[::STEP, ::STEP]
    mask = np.load(work / "basin_mask.npy")[::STEP, ::STEP]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    mesh, verts = terrain(heights, mask)
    block = bpy.data.objects.new("terrain", mesh)
    scene.collection.objects.link(block)
    block.data.materials.append(night_material(season))
    lights(scene, season)
    projection = camera(scene, verts, width_px)

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    settings = scene.render.image_settings
    settings.file_format, settings.color_mode = "PNG", "RGBA"
    scene.render.filepath = str(work / ("relief.png" if season == "night" else f"relief_{season}.png"))
    built = time.monotonic()
    bpy.ops.render.render(write_still=True)
    drawn = time.monotonic()

    # The repo gets the small WebP, never the PNG.
    settings.file_format, settings.color_mode, settings.quality = "WEBP", "RGBA", WEBP_QUALITY
    bpy.data.images["Render Result"].save_render(str(out_image), scene=scene)
    written = json.dumps(projection, indent=1) + "\n"
    if season == "night":
        OUT_PROJECTION.write_text(written, encoding="utf-8")
    elif OUT_PROJECTION.read_text(encoding="utf-8") != written:
        # The seasons are laid where the night is: another camera is not one.
        print("the projection is not the night's: draw the night first", file=sys.stderr)
        out_image.unlink()
        return 1
    print(f"{season}: picture {projection['res'][0]} x {projection['res'][1]}  samples {samples}")
    print(f"seconds: scene {built - started:.1f}  render {drawn - built:.1f}  all {time.monotonic() - started:.1f}")
    print(f"wrote {out_image.relative_to(REPO_DIR)} ({out_image.stat().st_size} bytes)"
          + (f" and {OUT_PROJECTION.relative_to(REPO_DIR)}" if season == "night" else ""))
    return 0


if __name__ == "__main__":
    code = main()
    if code:
        sys.exit(code)
