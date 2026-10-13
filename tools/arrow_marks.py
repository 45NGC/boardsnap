"""Reproducible full-board arrow geometry and controlled occlusion scenarios."""

from functools import lru_cache
import hashlib
import json
import math
import re

import cv2
import numpy as np
from PIL import Image, ImageDraw

from tools.capture_lichess import expand_placement

RENDERER = "controlled-arrows-v1"
CASES = ("arrow-empty", "arrow-piece", "arrow-crossed", "arrow-combined")
GEOMETRIES = ("horizontal", "vertical", "diagonal", "knight")
PALETTE = ((30, 160, 65), (240, 145, 25), (45, 110, 220), (215, 50, 65))
WIDTHS = (.08, .14, .22)
ALPHAS = (96, 144, 192)


def coordinate(square):
    return ord(square[0])-97, 8-int(square[1])


def square(x, y):
    return f"{'abcdefgh'[x]}{8-y}"


def geometry(mark):
    x, y = coordinate(mark["from"])
    a, b = coordinate(mark["to"])
    return "knight" if mark["path"] == "knight" else "vertical" if x == a else "horizontal" if y == b else "diagonal"


def validate_arrow(mark):
    required = {"kind", "from", "to", "path", "width", "rgba"}
    if not isinstance(mark, dict) or set(mark) not in (required, required | {"bend"}):
        raise ValueError("Arrow requires kind, from, to, path, width, rgba and optionally a knight bend.")
    if mark["kind"] != "arrow" or any(not isinstance(mark[k], str) or not re.fullmatch("[a-h][1-8]", mark[k]) for k in ("from", "to")):
        raise ValueError("Arrow endpoints must be chess coordinates.")
    x, y = coordinate(mark["from"])
    a, b = coordinate(mark["to"])
    dx, dy = abs(a-x), abs(b-y)
    if mark["path"] == "straight":
        if "bend" in mark or not (dx or dy) or not (dx == 0 or dy == 0 or dx == dy):
            raise ValueError("Straight arrows must be horizontal, vertical or diagonal and nonzero.")
    elif mark["path"] == "knight":
        if sorted((dx, dy)) != [1, 2] or mark.get("bend") not in ("horizontal-first", "vertical-first"):
            raise ValueError("Knight arrows require a 2-by-1 move and an explicit bend.")
    else:
        raise ValueError("Unknown arrow path.")
    if type(mark["width"]) not in (int, float) or not math.isfinite(mark["width"]) or not .04 <= mark["width"] <= .30:
        raise ValueError("Arrow width must be between .04 and .30 square sides.")
    color = mark["rgba"]
    if (not isinstance(color, list) or len(color) != 4 or any(type(c) is not int or not 0 <= c <= 255 for c in color)
            or color[3] == 0):
        raise ValueError("Arrow RGBA requires four bytes and nonzero opacity.")


def points(mark):
    x, y = coordinate(mark["from"])
    a, b = coordinate(mark["to"])
    result = [(x+.5, y+.5)]
    if mark["path"] == "knight":
        result.append((a+.5, y+.5) if mark["bend"] == "horizontal-first" else (x+.5, b+.5))
    return [*result, (a+.5, b+.5)]


def draw_arrow(layer, mark, bounds, orientation, *, mask=False):
    """Draw one continuous shaft/bend/head; compose separate arrows in drawing order."""
    side = min(bounds["width"], bounds["height"])/8
    vertices = points(mark)
    if orientation == "black-bottom":
        vertices = [(8-x, 8-y) for x, y in vertices]
    vertices = [(bounds["x"]+x*bounds["width"]/8, bounds["y"]+y*bounds["height"]/8) for x, y in vertices]
    pen = ImageDraw.Draw(layer)
    color = 255 if mask else tuple(mark["rgba"])
    width = max(1, round(mark["width"] * side))
    end = np.array(vertices[-1])
    vector = end - vertices[-2]
    vector /= np.linalg.norm(vector)
    normal = np.array([-vector[1], vector[0]])
    length = max(.30, mark["width"]*2.1) * side
    half_head = mark["width"] * 1.5 * side
    base = end-vector*length
    # Shaft stops inside the head; no blunt line endpoint protrudes past its tip.
    pen.line([*vertices[:-1], tuple(base+vector*width*.4)], fill=color, width=width, joint="curve")
    pen.polygon([tuple(end), tuple(base+normal*half_head), tuple(base-normal*half_head)], fill=color)
    for x, y in vertices[:-1]:
        r = width/2
        pen.ellipse((x-r, y-r, x+r, y+r), fill=color)


@lru_cache(maxsize=8192)
def _affected(serialized, halo):
    mark = json.loads(serialized)
    with Image.new("L", (512, 512)) as mask:
        draw_arrow(mask, mark, {"x": 0, "y": 0, "width": 512, "height": 512}, "white-bottom", mask=True)
        pixels = np.asarray(mask)
        if halo:
            pixels = cv2.dilate(pixels, np.ones((2*halo+1, 2*halo+1), np.uint8))
        grid = pixels.reshape(8, 64, 8, 64)
        return tuple(np.flatnonzero(grid.any(axis=(1, 3))).tolist())


def affected_indices(mark, halo=4):
    """Canonical cells touched by shaft, bend or head, plus a resize safety halo."""
    validate_arrow(mark)
    return _affected(json.dumps(mark, sort_keys=True), halo)


def arrows_overlap(first, second):
    bounds = {"x": 0, "y": 0, "width": 512, "height": 512}
    with Image.new("L", (512, 512)) as a, Image.new("L", (512, 512)) as b:
        draw_arrow(a, first, bounds, "white-bottom", mask=True)
        draw_arrow(b, second, bounds, "white-bottom", mask=True)
        return bool(np.any((np.asarray(a) > 0) & (np.asarray(b) > 0)))


def validate_coverage(placement, marks, details):
    """Reject scenario labels inconsistent with the full arrow mask or placement."""
    case = details.get("case")
    arrows = [m for m in marks if m["kind"] == "arrow"]
    if case not in CASES or not arrows:
        raise ValueError("Missing arrow coverage or unknown scenario.")
    covered = sorted({i for m in arrows for i in affected_indices(m)})
    flat = "".join(expand_placement(placement))
    occupied = [i for i in covered if flat[i] != "."]
    empty = [i for i in covered if flat[i] == "."]
    if (details.get("arrowCoveredIndices") != covered or details.get("occupiedCoveredIndices") != occupied
            or details.get("emptyCoveredIndices") != empty
            or details.get("geometries") != sorted({geometry(m) for m in arrows})):
        raise ValueError("Arrow mask, geometry and coverage labels disagree.")
    if case == "arrow-empty" and occupied or case in ("arrow-piece", "arrow-combined") and not occupied:
        raise ValueError("Arrow occupancy does not match its scenario.")
    if case == "arrow-crossed" and (len(arrows) < 2 or not any(
            arrows_overlap(a, b) for i, a in enumerate(arrows) for b in arrows[i+1:])):
        raise ValueError("Crossed arrows must overlap in pixels.")
    if case == "arrow-combined" and all(m["kind"] == "arrow" for m in marks):
        raise ValueError("Combined scenario needs an additional highlight or mark.")


@lru_cache(maxsize=4)
def endpoints(kind):
    result = []
    for y in range(8):
        for x in range(8):
            for b in range(8):
                for a in range(8):
                    dx, dy = abs(a-x), abs(b-y)
                    valid = {"horizontal": dy == 0 and dx > 0,
                             "vertical": dx == 0 and dy > 0,
                             "diagonal": dx == dy and dx > 0,
                             "knight": sorted((dx, dy)) == [1, 2]}[kind]
                    if valid:
                        result.append((square(x, y), square(a, b)))
    return result


def make_arrow(start, end, kind, rng):
    color = PALETTE[int(rng.integers(len(PALETTE)))]
    result = {"kind": "arrow", "from": start, "to": end, "path": "knight" if kind == "knight" else "straight",
              "width": WIDTHS[int(rng.integers(len(WIDTHS)))],
              "rgba": [*color, ALPHAS[int(rng.integers(len(ALPHAS)))]]}
    if kind == "knight":
        result["bend"] = ("horizontal-first", "vertical-first")[int(rng.integers(2))]
    return result


def arrow_plan(placement, case, key):
    """Choose geometry before inspecting occupancy; report unavailable empty routes.

    No legality is asserted. Piece labels select test conditions, never predictions.
    Empty means every covered cell (including the resize halo) is empty.
    """
    if case not in CASES:
        raise ValueError("Unknown arrow scenario.")
    seed = int.from_bytes(hashlib.sha256(str(key).encode()).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    flat = "".join(expand_placement(placement))
    kind = GEOMETRIES[seed % len(GEOMETRIES)]
    if case == "arrow-crossed":
        x, y = int(rng.integers(2, 6)), int(rng.integers(2, 6))
        if seed % 2:
            pairs = [(square(x-2, y), square(x+2, y)), (square(x, y-2), square(x, y+2))]
            kinds = ["horizontal", "vertical"]
        else:
            pairs = [(square(x-2, y-2), square(x+2, y+2)), (square(x-2, y+2), square(x+2, y-2))]
            kinds = ["diagonal", "diagonal"]
        marks = [make_arrow(*pair, direction, rng) for pair, direction in zip(pairs, kinds)]
    else:
        candidates = endpoints(kind)
        chosen = None
        for index in rng.permutation(len(candidates)):
            arrow = make_arrow(*candidates[index], kind, rng)
            touched = affected_indices(arrow)
            occupied = any(flat[i] != "." for i in touched)
            if (case == "arrow-empty" and not occupied) or (case != "arrow-empty" and occupied):
                chosen = arrow
                break
        if chosen is None:
            return None, {"case": case, "requestedGeometry": kind, "reason": "No route satisfies the requested occupancy."}
        marks = [chosen]
        if case == "arrow-combined":
            from tools.board_marks import COLORS
            # Put the arrow on the highlighted cells, rather than separate unrelated marks.
            marks = [{"kind": "last-move", "squares": [chosen["from"], chosen["to"]], "rgba": COLORS["last-move"].copy()},
                     {"kind": "circle", "squares": [chosen["to"]], "rgba": COLORS["circle"].copy()}, chosen]
    arrows = [m for m in marks if m["kind"] == "arrow"]
    touched = sorted({i for m in arrows for i in affected_indices(m)})
    return marks, {"case": case, "geometries": sorted({geometry(m) for m in arrows}),
                   "arrowCoveredIndices": touched,
                   "occupiedCoveredIndices": [i for i in touched if flat[i] != "."],
                   "emptyCoveredIndices": [i for i in touched if flat[i] == "."],
                   "coverageDefinition": "canonical cells intersecting arrow masks plus a 4px halo at 512px board size"}
