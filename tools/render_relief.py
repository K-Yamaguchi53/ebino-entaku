"""Draw the basin as a model in the night, seen from the south, north up (SPEC 14-66, 直し31-4).
Run in Blender, after tools/fetch_copernicus_dem.py:

    blender -b --python tools/render_relief.py -- WORK_DIR [WIDTH_PX] [SAMPLES] [SEASON] [OUT_DIR]

SEASON is night (the default), spring or autumn (the teacher, 11/6: the
basin's seasons, switched on the screen). Spring and autumn are the same
model and camera at dusk, coloured by height only: the paddies on the
basin's floor, the forests on the slopes, the plateau and the peaks. There
is no map of fields and forests here, so the colours are likely ones, not
the land as it is. They are written as mapdata/relief_<season>.webp; the
projection stays the night's (the same camera: checked, not written).

WORK_DIR holds heights.npy and basin_mask.npy (outside the repo); the full
picture is drawn there too (relief.png). Written to the repo (or to OUT_DIR,
outside it, to look at a picture before it goes in):
  mapdata/relief.webp             the picture (WebP, WEBP_QUALITY)
  mapdata/relief_projection.json  map (x, y, z) -> the picture's pixel

直し53 (the teacher, 11/7: もっときれいに。くっきり＋色も澄ませる): the
picture is WIDTH_PX across (4800), a whole number of times the projection's
own PROJECTION_PX (2400): the same camera framed by every STEP-th height as
before, so relief_projection.json is unchanged and the screen lays the larger
picture in the same box (ebino/relief.py PICTURE_TIMES): every point, name
and line stays where it was. The model is drawn from every height
(GEOMETRY_STEP 1, the DEM's own grain). The night a little brighter, the
moon stronger than the sky; autumn's browns cleared toward gold and grey;
spring with cherry trees (river banks, the hills' foot, patches on the floor)
and a little rape on the fields (blossoms()). AgX looks as LOOKS say.

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
STEP = 2  # Every STEP-th height frames the camera (the projection, as it has been since 直し31).
GEOMETRY_STEP = 1  # Every height becomes a vertex (直し53: the picture twice as wide).
PROJECTION_PX = 2400  # The projection's own width: the picture is drawn a whole number of times wider.
SKIRT = -14.0  # The model's bottom.
ELEV_DEG = 52.0  # How far the camera looks down.
MARGIN = 1.03
RIVER_REACH = 4  # Units (about 130 m) of each of the three blurs round the river.
WEBP_QUALITY = 90
NIGHT_MOON = 2.0  # Was 1.15 (直し31-4).
NIGHT_VIEW_LOOK = "AgX - Medium High Contrast"
SEASON_VIEW_LOOK = "AgX - Punchy"
VIEW_TRANSFORM = "AgX"  # Blender's own (as the pictures before 直し53 were drawn).


def socket(sockets, identifier):
    """A socket by its identifier: a Mix node has an A, a B and a Result for
    each data type, all of the same name."""
    return next(s for s in sockets if s.identifier == identifier)


def block(heights, step):
    """The block's corners: the top's vertices, then its bottom's ring."""
    rows, cols = heights.shape
    z = (heights - BASE_M) / M_PER_UNIT * EXAG
    gx, gy = np.meshgrid(np.arange(cols) * step, np.arange(rows) * step)
    top = np.stack([gx.ravel(), -gy.ravel(), z.ravel()], axis=1)
    ring = ([(0, c) for c in range(cols)] + [(r, cols - 1) for r in range(1, rows)]
            + [(rows - 1, c) for c in range(cols - 2, -1, -1)] + [(r, 0) for r in range(rows - 2, 0, -1)])
    ring_idx = [r * cols + c for r, c in ring]
    bottom = top[ring_idx].copy()
    bottom[:, 2] = SKIRT
    return top, ring_idx, np.concatenate([top, bottom])


def river_near(shape):
    """1 on the river (mapdata/ebino_osm.json's lines), falling to 0 a few
    RIVER_REACH away; one value per map unit, as heights.npy."""
    drawing = json.loads((REPO_DIR / "mapdata" / "ebino_osm.json").read_text(encoding="utf-8"))
    rows, cols = shape
    on = np.zeros(shape, dtype=np.float32)
    for line in drawing.get("river", []):
        for (x0, y0), (x1, y1) in zip(line, line[1:]):
            n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
            xs = np.clip(np.round(np.linspace(x0, x1, n)).astype(int), 0, cols - 1)
            ys = np.clip(np.round(np.linspace(y0, y1, n)).astype(int), 0, rows - 1)
            on[ys, xs] = 1.0
    near = on
    k = RIVER_REACH
    for _ in range(3):  # Three box blurs, about a bell.
        pad = np.pad(near, k, mode="edge")
        c = np.pad(np.cumsum(np.cumsum(pad, axis=0), axis=1), ((1, 0), (1, 0)))
        n = 2 * k + 1
        near = (c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]) / n ** 2
    return np.clip(near / max(float(near.max()), 1e-6) * 2.2, 0, 1).astype(np.float32)


def terrain(heights, mask, step, river=None):
    """The top (smooth) with its sides and bottom: a block cut out of the ground."""
    rows, cols = heights.shape
    top, ring_idx, verts = block(heights, step)
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
    if river is not None:
        # How near the river, for spring's cherry trees along its banks.
        attribute = mesh.attributes.new("river", "FLOAT", "POINT")
        attribute.data.foreach_set("value", np.concatenate([river.ravel(), np.zeros(n)]).astype(np.float32))
    return mesh, verts


# Each season: the colours by height (where, linear RGB) from the basin's
# floor (0) to 1700 m (1); the basin's floor mixed toward its own colour by
# how much; the steep sides' dark; the lights (name, energy, colour, angles);
# the sky (colour, strength); the view's look (Blender's AgX looks).
# Heights at a glance: the floor about 230 m (0.06), the hills round it 400
# to 800 m (0.17 to 0.42), the Ebino plateau about 1200 m (0.68), the
# Kirishima peaks to 1700 m (1).
# 直し53 (the teacher, 11/7: くっきり, the colours clearer): the night a
# little brighter, the moon stronger than the sky so the valleys and ridges
# read; autumn's reds kept, its browns (the floor, the plateau, the peaks)
# cleared toward gold and grey; spring with cherry trees and rape (blossom).
LOOKS = {
    "night": {
        "ramp": [(0.0, (0.045, 0.08, 0.145)), (0.35, (0.095, 0.145, 0.225)), (1.0, (0.25, 0.30, 0.40))],
        "basin": ((0.15, 0.165, 0.20), 0.25),
        "side": (0.012, 0.02, 0.035),
        "lights": (("moon", NIGHT_MOON, (0.72, 0.80, 1.0), (62, 0, -118)), ("rim", 0.4, (1.0, 0.86, 0.6), (70, 0, 135))),
        "sky": ((0.012, 0.022, 0.045), 0.2),
        "view_look": NIGHT_VIEW_LOOK,
    },
    # Spring at dusk. The floor's fields (below about 290 m) young green;
    # above, the slopes' fresh green with the dark of cedars and evergreens
    # in patches (most of a Kyushu hillside); the peaks pink (ミヤマキリシマ).
    # Cherry trees in bloom here and there (blossoms()).
    "spring": {
        "ramp": [(0.0, (0.23, 0.33, 0.08)), (0.085, (0.20, 0.30, 0.07)), (0.12, (0.12, 0.24, 0.05)),
                 (0.60, (0.13, 0.25, 0.05)), (0.72, (0.15, 0.22, 0.07)), (0.84, (0.32, 0.12, 0.20)),
                 (1.0, (0.21, 0.14, 0.15))],
        "forest": ((0.035, 0.08, 0.035), 0.12),
        "blossom": {"foot_from": (0.065, 0.09), "foot_to": (0.14, 0.2), "foot": 0.55, "river": 0.75,
                    "hamlet_scale": 0.05, "hamlet_cut": (0.64, 0.72), "hamlet": 0.55,
                    "thin_scale": 0.09, "thin_cut": (0.42, 0.62), "tree_scale": 0.55, "lift": 0.7, "tree_cut": (0.76, 0.84),
                    "pink": (0.98, 0.40, 0.58), "white": (1.0, 0.86, 0.90),
                    "rape_scale": 0.3, "rape_cut": (0.65, 0.71), "rape": (0.78, 0.60, 0.02)},
        "basin": ((0.23, 0.33, 0.08), 0.15),
        "side": (0.018, 0.022, 0.02),
        "lights": (("sun", 3.8, (1.0, 0.88, 0.76), (70, 0, -112)), ("rim", 0.5, (0.6, 0.68, 1.0), (70, 0, 135))),
        "sky": ((0.08, 0.09, 0.14), 0.5),
        "view_look": SEASON_VIEW_LOOK,
    },
    # Autumn at dusk. The floor's rice golden; above, the slopes' red,
    # orange and yellow showing in patches among the dark green; the
    # plateau's grass gold; the peaks bare.
    "autumn": {
        "ramp": [(0.0, (0.56, 0.35, 0.055)), (0.085, (0.50, 0.31, 0.05)), (0.12, (0.42, 0.05, 0.015)),
                 (0.30, (0.46, 0.10, 0.015)), (0.44, (0.50, 0.20, 0.02)), (0.58, (0.52, 0.36, 0.04)),
                 (0.70, (0.50, 0.38, 0.08)), (0.86, (0.21, 0.18, 0.15)), (1.0, (0.18, 0.17, 0.16))],
        "forest": ((0.03, 0.075, 0.025), 0.0),
        "patches": (0.33, 0.37),
        # The crowns: about 3 units (110 m, a clump of trees) across, a
        # few pixels in the picture; each cell one colour (where, colour),
        # the slopes leaning to one end or the other by a wider noise.
        "canopy": {"scale": 0.3, "bump": 0.45, "lean": (0.06, 2.4), "spread": 0.35,
                   "colours": [(0.0, (0.04, 0.11, 0.025)), (0.24, (0.42, 0.012, 0.012)),
                               (0.40, (0.62, 0.035, 0.012)), (0.54, (0.72, 0.17, 0.01)),
                               (0.68, (0.82, 0.40, 0.02)), (0.86, (0.70, 0.26, 0.015))]},
        "basin": ((0.56, 0.35, 0.055), 0.15),
        "side": (0.03, 0.02, 0.012),
        "lights": (("sun", 3.0, (1.0, 0.93, 0.84), (70, 0, -112)), ("rim", 0.5, (0.6, 0.68, 1.0), (70, 0, 135))),
        "sky": ((0.08, 0.09, 0.14), 0.5),
        "view_look": SEASON_VIEW_LOOK,
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
    if "canopy" in look:
        # The trees' crowns on the wooded slopes (above the fields, below
        # the plateau's grass): a cell each, its colour drawn from the
        # cell's own random value, a little dome lit by the sun.
        canopy = look["canopy"]
        cells = nt.nodes.new("ShaderNodeTexVoronoi")
        cells.inputs["Scale"].default_value = canopy["scale"]
        nt.links.new(geometry.outputs["Position"], cells.inputs["Vector"])
        random = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(cells.outputs["Color"], random.inputs[0])
        crowns = nt.nodes.new("ShaderNodeValToRGB")
        crowns.color_ramp.interpolation = "CONSTANT"
        stops = crowns.color_ramp.elements
        first, *rest = canopy["colours"]
        stops[0].position, stops[0].color = first[0], (*first[1], 1)
        stops[1].position, stops[1].color = rest[-1][0], (*rest[-1][1], 1)
        for at, colour in rest[:-1]:
            stops.new(at).color = (*colour, 1)
        # value = 0.5 + (random - 0.5) * spread + (slope's lean - 0.5) * strength
        lean_scale, lean = canopy["lean"]
        spread = canopy["spread"]
        slope_lean = nt.nodes.new("ShaderNodeTexNoise")
        slope_lean.inputs["Scale"].default_value = lean_scale
        slope_lean.inputs["Detail"].default_value = 2.0
        nt.links.new(geometry.outputs["Position"], slope_lean.inputs["Vector"])
        own = nt.nodes.new("ShaderNodeMath")
        own.operation = "MULTIPLY_ADD"
        own.inputs[1].default_value = spread
        own.inputs[2].default_value = 0.5 - 0.5 * spread - 0.5 * lean
        nt.links.new(random.outputs["X"], own.inputs[0])
        pick = nt.nodes.new("ShaderNodeMath")
        pick.operation = "MULTIPLY_ADD"
        pick.use_clamp = True
        pick.inputs[1].default_value = lean
        nt.links.new(slope_lean.outputs["Fac"], pick.inputs[0])
        nt.links.new(own.outputs[0], pick.inputs[2])
        nt.links.new(pick.outputs[0], crowns.inputs["Fac"])
        wood_from = nt.nodes.new("ShaderNodeMapRange")
        wood_from.inputs["From Min"].default_value = 0.085
        wood_from.inputs["From Max"].default_value = 0.11
        nt.links.new(by_height.outputs["Result"], wood_from.inputs["Value"])
        wood_to = nt.nodes.new("ShaderNodeMapRange")
        wood_to.inputs["From Min"].default_value = 0.56
        wood_to.inputs["From Max"].default_value = 0.66
        wood_to.inputs["To Min"].default_value = 1.0
        wood_to.inputs["To Max"].default_value = 0.0
        nt.links.new(by_height.outputs["Result"], wood_to.inputs["Value"])
        wood = nt.nodes.new("ShaderNodeMath")
        wood.operation = "MULTIPLY"
        nt.links.new(wood_from.outputs["Result"], wood.inputs[0])
        nt.links.new(wood_to.outputs["Result"], wood.inputs[1])
        wooded_slope = nt.nodes.new("ShaderNodeMix")
        wooded_slope.data_type = "RGBA"
        nt.links.new(leaves, socket(wooded_slope.inputs, "A_Color"))
        nt.links.new(crowns.outputs["Color"], socket(wooded_slope.inputs, "B_Color"))
        nt.links.new(wood.outputs[0], socket(wooded_slope.inputs, "Factor_Float"))
        leaves = socket(wooded_slope.outputs, "Result_Color")
        dome = nt.nodes.new("ShaderNodeBump")
        dome.invert = True
        dome.inputs["Distance"].default_value = 1.0
        nt.links.new(cells.outputs["Distance"], dome.inputs["Height"])
        dome_strength = nt.nodes.new("ShaderNodeMath")
        dome_strength.operation = "MULTIPLY"
        dome_strength.inputs[1].default_value = canopy["bump"]
        nt.links.new(wood.outputs[0], dome_strength.inputs[0])
        nt.links.new(dome_strength.outputs[0], dome.inputs["Strength"])
        nt.links.new(dome.outputs["Normal"], bsdf.inputs["Normal"])
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

    if "blossom" in look:
        leaves = blossoms(nt, look["blossom"], geometry, by_height, leaves)

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


def blossoms(nt, blossom, geometry, by_height, leaves):
    """Spring's cherry trees (pale pink and white) in clumps: along the
    river, at the foot of the hills round the floor and in a few patches on
    the floor (where hamlets keep them); rape's yellow in strips on the
    fields. A tree is a Voronoi cell picked by its own random value where
    the place asks for trees: likely places, not the land's own record."""
    def node(kind, **inputs):
        made = nt.nodes.new(kind)
        for key, value in inputs.items():
            made.inputs[key].default_value = value
        return made

    def op(operation, a, b=None):
        made = nt.nodes.new("ShaderNodeMath")
        made.operation = operation
        for i, value in enumerate((a, b)):
            if value is None:
                continue
            if isinstance(value, (int, float)):
                made.inputs[i].default_value = value
            else:
                nt.links.new(value, made.inputs[i])
        return made.outputs[0]

    def band(value, lo, hi, out_lo=0.0, out_hi=1.0):
        made = node("ShaderNodeMapRange", **{"From Min": lo, "From Max": hi, "To Min": out_lo, "To Max": out_hi})
        nt.links.new(value, made.inputs["Value"])
        return made.outputs["Result"]

    def mix(a, b, factor):
        made = nt.nodes.new("ShaderNodeMix")
        made.data_type = "RGBA"
        for name, value in (("A_Color", a), ("B_Color", b)):
            if isinstance(value, tuple):
                socket(made.inputs, name).default_value = (*value, 1)
            else:
                nt.links.new(value, socket(made.inputs, name))
        nt.links.new(factor, socket(made.inputs, "Factor_Float"))
        return socket(made.outputs, "Result_Color")

    height = by_height.outputs["Result"]
    river = nt.nodes.new("ShaderNodeAttribute")
    river.attribute_name = "river"
    # The foot of the hills: just above the floor's fields.
    foot = op("MULTIPLY", band(height, *blossom["foot_from"]), band(height, *blossom["foot_to"], 1.0, 0.0))
    hamlets = node("ShaderNodeTexNoise", Scale=blossom["hamlet_scale"], Detail=2.0)
    nt.links.new(geometry.outputs["Position"], hamlets.inputs["Vector"])
    hamlet = op("MULTIPLY", band(hamlets.outputs["Fac"], *blossom["hamlet_cut"]), band(height, 0.11, 0.08))
    where = op("MAXIMUM", op("MULTIPLY", river.outputs["Fac"], blossom["river"]),
               op("MAXIMUM", op("MULTIPLY", foot, blossom["foot"]), op("MULTIPLY", hamlet, blossom["hamlet"])))
    # Patchy, never a band: a wider noise thins it here and there.
    thin = node("ShaderNodeTexNoise", Scale=blossom["thin_scale"], Detail=1.0)
    nt.links.new(geometry.outputs["Position"], thin.inputs["Vector"])
    where = op("MULTIPLY", where, band(thin.outputs["Fac"], *blossom["thin_cut"]))
    # The crowns: a fine noise's high places, more of them where the place
    # asks for trees, so they gather into irregular groves; pink or white
    # by a second noise.
    crowns = node("ShaderNodeTexNoise", Scale=blossom["tree_scale"], Detail=4.0, Roughness=0.65)
    nt.links.new(geometry.outputs["Position"], crowns.inputs["Vector"])
    lifted = op("MULTIPLY_ADD", where, blossom["lift"])
    nt.links.new(crowns.outputs["Fac"], lifted.node.inputs[2])
    tree = band(lifted, *blossom["tree_cut"])
    tint = node("ShaderNodeTexNoise", Scale=blossom["tree_scale"] * 2.0, Detail=1.0)
    nt.links.new(geometry.outputs["Position"], tint.inputs["Vector"])
    leaves = mix(leaves, mix(blossom["pink"], blossom["white"], band(tint.outputs["Fac"], 0.4, 0.6)), tree)
    # Rape: thin yellow strips on the fields (a stretched noise), a little.
    strips = node("ShaderNodeTexNoise", Scale=blossom["rape_scale"], Detail=1.0)
    stretch = nt.nodes.new("ShaderNodeMapping")
    stretch.inputs["Scale"].default_value = (1.0, 4.0, 1.0)
    nt.links.new(geometry.outputs["Position"], stretch.inputs["Vector"])
    nt.links.new(stretch.outputs["Vector"], strips.inputs["Vector"])
    rape = op("MULTIPLY", band(strips.outputs["Fac"], *blossom["rape_cut"]), band(height, 0.085, 0.07))
    return mix(leaves, blossom["rape"], rape)


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
        print("usage: blender -b --python tools/render_relief.py -- WORK_DIR [WIDTH_PX] [SAMPLES] [SEASON] [OUT_DIR]",
              file=sys.stderr)
        return 2
    season = argv[3] if len(argv) > 3 else "night"
    if season not in SEASONS:
        print(f"SEASON is one of {', '.join(SEASONS)}", file=sys.stderr)
        return 2
    # OUT_DIR (outside the repo) to try a picture before it goes into mapdata/.
    out_dir = Path(argv[4]).resolve() if len(argv) > 4 else OUT_IMAGE.parent
    out_image = out_dir / (OUT_IMAGE.name if season == "night" else f"relief_{season}.webp")
    out_projection = out_dir / OUT_PROJECTION.name
    work = Path(argv[0]).resolve()
    width_px = int(argv[1]) if len(argv) > 1 else 2 * PROJECTION_PX
    samples = int(argv[2]) if len(argv) > 2 else 384
    times = width_px / PROJECTION_PX
    if times != int(times) or times < 1:
        print(f"WIDTH_PX is a whole number of times {PROJECTION_PX}", file=sys.stderr)
        return 2
    started = time.monotonic()
    heights = np.load(work / "heights.npy")
    mask = np.load(work / "basin_mask.npy")
    # The camera framed by every STEP-th height, as before (the projection
    # unchanged); the model drawn from the heights inside that frame.
    framing = heights[::STEP, ::STEP]
    rows, cols = ((n - 1) * STEP + 1 for n in framing.shape)
    _, _, frame_verts = block(framing, STEP)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    cut = (slice(0, rows, GEOMETRY_STEP), slice(0, cols, GEOMETRY_STEP))
    river = river_near(heights.shape)[cut] if "blossom" in LOOKS[season] else None
    mesh, _ = terrain(heights[cut], mask[cut], GEOMETRY_STEP, river)
    model = bpy.data.objects.new("terrain", mesh)
    scene.collection.objects.link(model)
    model.data.materials.append(night_material(season))
    lights(scene, season)
    projection = camera(scene, frame_verts, PROJECTION_PX)
    # The same view drawn larger: the orthographic camera's width fits the
    # picture's, so every pixel is `times` pixels and nothing moves.
    scene.render.resolution_x = width_px
    scene.render.resolution_y = projection["res"][1] * int(times)

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.view_settings.view_transform = VIEW_TRANSFORM
    try:
        scene.view_settings.look = LOOKS[season].get("view_look", "None")
    except TypeError as wrong:
        print(wrong, file=sys.stderr)
        return 2
    settings = scene.render.image_settings
    settings.file_format, settings.color_mode = "PNG", "RGBA"
    scene.render.filepath = str(work / ("relief.png" if season == "night" else f"relief_{season}.png"))
    built = time.monotonic()
    bpy.ops.render.render(write_still=True)
    drawn = time.monotonic()

    # The repo gets the WebP, never the PNG.
    settings.file_format, settings.color_mode, settings.quality = "WEBP", "RGBA", WEBP_QUALITY
    bpy.data.images["Render Result"].save_render(str(out_image), scene=scene)
    written = json.dumps(projection, indent=1) + "\n"
    if OUT_PROJECTION.is_file() and OUT_PROJECTION.read_text(encoding="utf-8") != written:
        # Every picture is laid where the map's points are: another camera is not one.
        print("the projection is not mapdata/relief_projection.json's", file=sys.stderr)
        out_image.unlink()
        return 1
    if not out_projection.is_file():
        out_projection.write_text(written, encoding="utf-8")
    print(f"{season}: picture {width_px} x {scene.render.resolution_y}  samples {samples}"
          f"  projection {projection['res'][0]} x {projection['res'][1]}")
    print(f"seconds: scene {built - started:.1f}  render {drawn - built:.1f}  all {time.monotonic() - started:.1f}")
    print(f"wrote {out_image} ({out_image.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    code = main()
    if code:
        sys.exit(code)
