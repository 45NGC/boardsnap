"""Capture a small, pre-partitioned dataset from the live lichess editor."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlencode


PROFILE = "lichess-cburnett-brown-v1"
VIEWPORT = {"width": 1280, "height": 1000}
SPLITS = {"tuning": Path("data/tuning"), "evaluation": Path("tests/fixtures/evaluation")}
BOARD = ".main-board cg-board"
SYMBOLS = "PNBRQKpnbrqk"


def expand_placement(placement: str) -> list[str]:
    """Validate canonical piece placement without requiring a legal position."""
    if not isinstance(placement, str) or len(placement.split("/")) != 8:
        raise ValueError("piecePlacement must contain exactly eight ranks")
    rows = []
    for rank in placement.split("/"):
        row = ""
        previous_digit = False
        for symbol in rank:
            if symbol in "12345678":
                if previous_digit:
                    raise ValueError("Use one digit for each run of empty squares")
                row += "." * int(symbol)
                previous_digit = True
            elif symbol in SYMBOLS:
                row += symbol
                previous_digit = False
            else:
                raise ValueError(f"Invalid piecePlacement symbol: {symbol!r}")
        if len(row) != 8:
            raise ValueError("Each piecePlacement rank must describe eight squares")
        rows.append(row)
    return rows


def load_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("profileId") != PROFILE:
        raise ValueError(f"The manifest must specify profileId {PROFILE!r}")
    positions = manifest.get("positions")
    if not isinstance(positions, list) or not positions:
        raise ValueError("positions must be a nonempty list")
    groups, placements = set(), set()
    for position in positions:
        if not isinstance(position, dict):
            raise ValueError("Each position must be an object")
        group = position.get("groupId")
        if not isinstance(group, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", group):
            raise ValueError("groupId must be a safe lowercase identifier (1–64 characters)")
        if group in groups:
            raise ValueError(f"Duplicate groupId: {group}")
        split = position.get("split")
        if not isinstance(split, str) or split not in SPLITS:
            raise ValueError(f"Invalid split for {group}: use tuning or evaluation")
        placement = position.get("piecePlacement")
        expand_placement(placement)
        if placement in placements:
            raise ValueError("Duplicate position: keep all orientations in a single group")
        groups.add(group)
        placements.add(placement)
    return manifest


def destination(root: Path, split: str) -> Path:
    return root / SPLITS[split] / PROFILE


def check_destinations(root: Path) -> None:
    # Refuse another batch under this profile, even if only one split is requested.
    # This prevents accidental reuse across partitions on subsequent runs.
    for split in SPLITS:
        path = destination(root, split)
        if path.exists():
            raise ValueError(f"Destination already exists: {path}. Use a fresh output root.")


def editor_url(placement: str, color: str) -> str:
    # The editor accepts piece placement alone; do not invent additional FEN fields.
    return "https://lichess.org/editor?" + urlencode({"fen": placement, "color": color})


def validate_bounds(bounds: dict, viewport: dict) -> None:
    x, y, width, height = (bounds[key] for key in ("x", "y", "width", "height"))
    if width < 256 or abs(width - height) > 0.1:
        raise ValueError("Expected a square board at least 256 pixels wide")
    if x < 0 or y < 0 or x + width > viewport["width"] or y + height > viewport["height"]:
        raise ValueError("The board is not fully inside the screenshot")


# Read the rendered pieces rather than trusting only the editor's text field.
# This is annotation from the DOM, not image recognition.
READ_BOARD = """board => {
    const box = board.getBoundingClientRect();
    const rows = Array.from({length: 8}, () => Array(8).fill('.'));
    const roles = {pawn:'p', knight:'n', bishop:'b', rook:'r', queen:'q', king:'k'};
    for (const piece of board.querySelectorAll('piece')) {
        const rect = piece.getBoundingClientRect();
        if (!rect.width || !rect.height || getComputedStyle(piece).visibility === 'hidden') continue;
        const role = Object.keys(roles).find(r => piece.classList.contains(r));
        const white = piece.classList.contains('white');
        if (!role || (!white && !piece.classList.contains('black'))) throw Error('Unknown piece');
        const x = (rect.x - box.x) / (box.width / 8);
        const y = (rect.y - box.y) / (box.height / 8);
        const col = Math.round(x), row = Math.round(y);
        if (Math.abs(x-col) > .02 || Math.abs(y-row) > .02 ||
            col < 0 || col > 7 || row < 0 || row > 7 || rows[row][col] !== '.')
            throw Error('Pieces are moving, overlapping, or outside the grid');
        rows[row][col] = white ? roles[role].toUpperCase() : roles[role];
    }
    return rows.map(row => row.join(''));
}"""


WAIT_FOR_ARTWORK = """async board => {
    await document.fonts.ready;
    const urls = new Set();
    for (const el of [board, ...board.querySelectorAll('piece')]) {
        let hasImage = false;
        for (const pseudo of [null, '::before', '::after']) {
            const bg = getComputedStyle(el, pseudo).backgroundImage;
            for (const match of bg.matchAll(/url\\(["']?(.*?)["']?\\)/g)) {
                urls.add(match[1]); hasImage = true;
            }
        }
        if (!hasImage) throw Error('Missing board or piece artwork');
    }
    await Promise.all([...urls].map(url => new Promise((resolve, reject) => {
        const image = new Image();
        const timer = setTimeout(() => reject(Error('Artwork load timed out')), 15000);
        image.onload = () => { clearTimeout(timer); resolve(); };
        image.onerror = () => { clearTimeout(timer); reject(Error('Artwork failed to load')); };
        image.src = url;
    })));
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
}"""


def capture_position(page, position: dict, color: str, folder: Path, browser_version: str,
                     profile_id: str = PROFILE) -> None:
    placement = position["piecePlacement"]
    url = editor_url(placement, color)
    response = page.goto(url, wait_until="domcontentloaded")
    if response is None or not response.ok:
        raise ValueError(f"Editor request failed: {response.status if response else 'no response'}")
    board = page.locator(BOARD)
    board.wait_for(state="visible")
    page.locator(f".main-board .cg-wrap.orientation-{color}").wait_for(state="visible")
    if profile_id == "lichess-cburnett-blue-v1" and page.locator("body").get_attribute("data-board") != "blue":
        page.locator(".dasher .toggle").evaluate("e => e.click()")
        page.locator("#dasher_app button.sub").filter(has_text="Board").evaluate("e => e.click()")
        page.locator('#dasher_app button[title="blue"]').evaluate("e => e.click()")
        page.wait_for_function("document.body.dataset.board === 'blue'")
        page.locator(".dasher .toggle").evaluate("e => e.click()")
    profile = page.locator("body").evaluate(
        "e => ({board:e.dataset.board, pieces:e.dataset.pieceSet, "
        "is3d:e.classList.contains('is3d'), coordinates:e.classList.contains('coords-in')})"
    )
    expected_theme = "blue" if profile_id == "lichess-cburnett-blue-v1" else "brown"
    if profile != {"board": expected_theme, "pieces": "cburnett", "is3d": False, "coordinates": True}:
        raise ValueError(f"The live editor no longer matches {profile_id}: {profile}")
    actual = page.locator(".copyables input").first.input_value().split()[0]
    if actual != placement:
        raise ValueError(f"Editor loaded a different position: {actual}")
    # Keep page context, but hide the answer so the dataset cannot learn to read it.
    page.add_style_tag(content=".copyables, cg-resize { visibility: hidden !important; }")
    board.evaluate(WAIT_FOR_ARTWORK)
    expected = expand_placement(placement)
    if color == "black":
        expected = [row[::-1] for row in expected[::-1]]
    if board.evaluate(READ_BOARD) != expected:
        raise ValueError("Rendered pieces do not match the requested position/orientation")
    if page.locator(".main-board cg-board square, .main-board svg g > *").count():
        raise ValueError("Unexpected highlights or drawing overlays on the board")
    page.mouse.move(0, 0)
    bounds = board.bounding_box()
    if bounds is None:
        raise ValueError("Board has no visible bounds")
    validate_bounds(bounds, VIEWPORT)
    png = page.screenshot(type="png", full_page=False, animations="disabled", scale="css")
    if board.bounding_box() != bounds:
        raise ValueError("Board moved while capturing; no sample was saved")
    name = f"{position['groupId']}-{color}"
    annotation = {
        "image": f"{name}.png",
        "profileId": profile_id,
        "groupId": position["groupId"],
        "split": position["split"],
        "orientation": f"{color}-bottom",
        "boardBounds": bounds,
        "imageSize": VIEWPORT,
        "piecePlacement": placement,
        "source": {
            "url": url,
            "capturedAt": datetime.now(timezone.utc).isoformat(),
            "method": "Playwright screenshot of the live lichess editor",
            "browser": f"Chromium {browser_version}",
            "playwright": version("playwright"),
            "deviceScaleFactor": 1,
            "colorScheme": "light",
            "locale": "en-GB",
            "pageModification": "FEN/URL fields and board resize handle hidden using CSS visibility",
        },
        "sha256": hashlib.sha256(png).hexdigest(),
    }
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.png").write_bytes(png)
    (folder / f"{name}.json").write_text(json.dumps(annotation, indent=2) + "\n", encoding="utf-8")


def capture_dataset(manifest: dict, root: Path, headed: bool = False) -> None:
    from playwright.sync_api import sync_playwright

    check_destinations(root)
    root.mkdir(parents=True, exist_ok=True)
    # Publish only after every capture succeeds. Failed captures leave no dataset.
    with tempfile.TemporaryDirectory(prefix="boardsnap-capture-", dir=root) as temporary:
        staging = Path(temporary)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not headed)
            try:
                context = browser.new_context(
                    viewport=VIEWPORT, device_scale_factor=1, locale="en-GB", color_scheme="light"
                )
                page = context.new_page()
                page.set_default_timeout(30000)
                for position in manifest["positions"]:
                    for color in ("white", "black"):
                        print(f"Capturing {position['groupId']} ({color}-bottom)", file=sys.stderr)
                        capture_position(page, position, color, staging / position["split"], browser.version)
                        page.wait_for_timeout(1000)
            finally:
                browser.close()
        check_destinations(root)
        for split in SPLITS:
            folder = staging / split
            if folder.exists():
                # Each partition gets only its own positions, including provenance notes.
                subset = dict(manifest, positions=[p for p in manifest["positions"] if p["split"] == split])
                (folder / "manifest.json").write_text(json.dumps(subset, indent=2) + "\n", encoding="utf-8")
                target = destination(root, split)
                target.parent.mkdir(parents=True, exist_ok=True)
                folder.rename(target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSON manifest with known positions and splits")
    parser.add_argument("--output-root", type=Path, default=Path("."), help="Dataset root (default: current directory)")
    parser.add_argument("--validate-only", action="store_true", help="Check the manifest and destinations without a browser")
    parser.add_argument("--headed", action="store_true", help="Show Chromium while capturing")
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        check_destinations(args.output_root)
    except (OSError, ValueError) as error:
        print(f"Invalid capture request: {error}", file=sys.stderr)
        return 2
    if args.validate_only:
        print(f"Valid manifest: {len(manifest['positions'])} positions, two orientations each.")
        return 0
    try:
        capture_dataset(manifest, args.output_root, args.headed)
    except ImportError:
        print("Install capture dependencies: python -m pip install -e '.[capture]'", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Capture failed: {error}", file=sys.stderr)
        return 1
    print(f"Saved {2 * len(manifest['positions'])} annotated PNGs under {args.output_root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
