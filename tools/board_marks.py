"""Versioned, controlled overlays on full screenshots, before square extraction.

These are synthetic visual conditions, not evidence of a legal move, check or
the exact native rendering of a platform. Original screenshots stay immutable.
"""

import hashlib
from io import BytesIO
import re

import numpy as np
from PIL import Image, ImageDraw

from tools.capture_lichess import expand_placement

RENDERER = "controlled-overlay-v1"
KINDS = ("last-move", "selection", "check", "circle", "move-dot")
COLORS = {"last-move": [205, 210, 0, 72], "selection": [20, 155, 85, 85],
          "check": [240, 25, 20, 160], "circle": [28, 154, 60, 190],
          "move-dot": [25, 30, 25, 100]}


def mark_conditions(marks):
    """Unique kinds in drawing order; multiple arrows belong to one condition."""
    return list(dict.fromkeys(m["kind"] for m in marks))


def validate_marks(marks, placement=None):
    if not isinstance(marks, list) or not marks:
        raise ValueError("Marks must be a nonempty list.")
    rows = expand_placement(placement) if placement is not None else None
    seen = set()
    for mark in marks:
        if isinstance(mark, dict) and mark.get("kind") == "arrow":
            from tools.arrow_marks import validate_arrow
            validate_arrow(mark)
            continue
        if not isinstance(mark, dict) or set(mark) != {"kind", "squares", "rgba"}:
            raise ValueError("A mark requires exactly kind, squares and rgba.")
        kind, squares, rgba = mark["kind"], mark["squares"], mark["rgba"]
        if kind not in KINDS or kind in seen:
            raise ValueError("Choose distinct supported mark kinds.")
        seen.add(kind)
        if (not isinstance(squares, list) or not squares
                or any(not isinstance(s, str) or not re.fullmatch("[a-h][1-8]", s) for s in squares)
                or len(set(squares)) != len(squares)):
            raise ValueError("Mark squares must be distinct chess coordinates.")
        if kind == "last-move" and len(squares) != 2:
            raise ValueError("Last-move requires two distinct squares.")
        if kind == "selection" and len(squares) != 1:
            raise ValueError("Selection requires one square.")
        if kind == "check" and (len(squares) > 2 or rows is not None and any(
                rows[8-int(s[1])][ord(s[0])-97] not in "Kk" for s in squares)):
            raise ValueError("A check indicator must be placed on a king.")
        if (not isinstance(rgba, list) or len(rgba) != 4
                or any(type(c) is not int or not 0 <= c <= 255 for c in rgba) or rgba[3] == 0):
            raise ValueError("RGBA must contain four byte values and nonzero opacity.")


def mark_plan(placement, kind, key):
    """Deterministic bucket sampling, independent of view and source partition.

    Sample piece/background buckets rather than mostly-empty square locations.
    Check is necessarily king-specific; other marks cover all thirteen classes.
    The selected squares are visual stress tests, not legal-move annotations.
    """
    if kind not in KINDS:
        raise ValueError("Unknown mark kind.")
    rng = np.random.default_rng(int.from_bytes(hashlib.sha256(str(key).encode()).digest()[:8], "big"))
    buckets = {}
    for row, line in enumerate(expand_placement(placement)):
        for col, piece in enumerate(line):
            buckets.setdefault((piece, (row + col) % 2), []).append(f"{'abcdefgh'[col]}{8-row}")
    if kind == "check":
        options = [s for (piece, _), squares in buckets.items() if piece in "Kk" for s in squares]
        if not options:
            raise ValueError("Check variants require a king.")
        squares = [options[int(rng.integers(len(options)))]]
    else:
        count = {"last-move": 2, "selection": 1, "circle": 6, "move-dot": 6}[kind]
        keys = list(buckets)
        squares = []
        for index in rng.permutation(len(keys)):
            choices = buckets[keys[index]]
            squares.append(choices[int(rng.integers(len(choices)))])
            if len(squares) == count:
                break
    result = [{"kind": kind, "squares": squares, "rgba": COLORS[kind].copy()}]
    validate_marks(result, placement)
    return result


def render_marks(image, bounds, orientation, marks, placement=None):
    """Alpha-composite marks in input pixels; leave everything outside the board intact."""
    validate_marks(marks, placement)
    if orientation not in ("white-bottom", "black-bottom") or image.mode != "RGB":
        raise ValueError("Expected RGB pixels and an explicit orientation.")
    if set(bounds) != {"x", "y", "width", "height"} or any(
            type(v) not in (int, float) or not np.isfinite(v) for v in bounds.values()):
        raise ValueError("Invalid mark bounds.")
    x, y, width, height = (bounds[k] for k in ("x", "y", "width", "height"))
    if min(x, y) < 0 or min(width, height) < 128 or x + width > image.width or y + height > image.height:
        raise ValueError("Mark bounds are outside the image or too small.")
    # Round exclusive edges exactly as square-dataset normalization does.
    xs = [round(x + i * width / 8) for i in range(9)]
    ys = [round(y + i * height / 8) for i in range(9)]
    output = image.copy()
    for mark in marks:
        overlay = Image.new("RGBA", image.size)
        draw = ImageDraw.Draw(overlay)
        if mark["kind"] == "arrow":
            from tools.arrow_marks import draw_arrow
            draw_arrow(overlay, mark, bounds, orientation)
        for square in mark.get("squares", []):
            row, col = 8 - int(square[1]), ord(square[0]) - 97
            if orientation == "black-bottom":
                row, col = 7-row, 7-col
            left, top, right, bottom = xs[col], ys[row], xs[col+1], ys[row+1]
            side = min(right-left, bottom-top)
            color = tuple(mark["rgba"])
            if mark["kind"] in ("last-move", "selection"):
                draw.rectangle((left, top, right-1, bottom-1), fill=color)
            elif mark["kind"] == "check":
                # Radial glow; a controlled overlay, not a native browser CSS assertion.
                for radius in range(max(1, int(side * .49)), 0, -1):
                    alpha = round(color[3] * (1 - radius / (side * .5)))
                    cx, cy = (left+right)/2, (top+bottom)/2
                    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=(*color[:3], alpha))
            else:
                fraction = .42 if mark["kind"] == "circle" else .13
                radius = side * fraction
                cx, cy = (left+right)/2, (top+bottom)/2
                box = (cx-radius, cy-radius, cx+radius, cy+radius)
                if mark["kind"] == "circle":
                    draw.ellipse(box, outline=color, width=max(1, round(side*.045)))
                else:
                    draw.ellipse(box, fill=color)
        merged = Image.alpha_composite(output.convert("RGBA"), overlay).convert("RGB")
        overlay.close()
        output.close()
        output = merged
    return output


def mark_png(png, bounds, orientation, marks, placement):
    with Image.open(BytesIO(png)) as source, source.convert("RGB") as rgb:
        with render_marks(rgb, bounds, orientation, marks, placement) as marked:
            stream = BytesIO()
            marked.save(stream, format="PNG")
    result = stream.getvalue()
    version = RENDERER
    if any(m["kind"] == "arrow" for m in marks):
        from tools.arrow_marks import RENDERER as version
    return result, {"renderer": version, "marks": marks,
                    "baseImageSha256": hashlib.sha256(png).hexdigest(),
                    "method": "synthetic alpha overlays before normalization; not native platform marks"}
