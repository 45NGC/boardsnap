"""Collect the two additional digital profiles using the original fixed partitions.

Run as python -m tools.capture_profiles PROFILE --output-root NEW_DIRECTORY.
No runtime recognition or evaluation labels are used to annotate these captures.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlencode

from tools.capture_lichess import (VIEWPORT, SPLITS, capture_position, expand_placement,
                                   load_manifest, validate_bounds)

PROFILES = ("lichess-cburnett-blue-v1", "chesscom-default-green-v1")
ROOT = Path(__file__).resolve().parents[1]


READ_CHESSCOM = """board => {
 const box=board.getBoundingClientRect(), rows=Array.from({length:8},()=>Array(8).fill('.'));
 for (const p of board.querySelectorAll('.piece')) {
  const code=[...p.classList].find(c=>/^[wb][pnbrqk]$/.test(c));
  const rect=p.getBoundingClientRect();
  const fx=(rect.x-box.x)/(box.width/8), fy=(rect.y-box.y)/(box.height/8);
  const x=Math.round(fx), y=Math.round(fy);
  if(!code || x<0 || x>7 || y<0 || y>7 || Math.abs(fx-x)>.02 || Math.abs(fy-y)>.02 || rows[y][x]!=='.')
   throw Error('Invalid rendered piece bounds or code');
  rows[y][x]=code[0]==='w'?code[1].toUpperCase():code[1];
 }
 return rows.map(r=>r.join(''));
}"""


ARTWORK = """async board => {
 await document.fonts.ready;
 const urls=new Set([board,...board.querySelectorAll('.piece')].map(e=>{
  const match=getComputedStyle(e).backgroundImage.match(/url\\(["']?(.*?)["']?\\)/);
  if(!match) throw Error('Missing artwork');
  return match[1];
 }));
 await Promise.all([...urls].map(url=>new Promise((resolve,reject)=>{
  const i=new Image(); i.onload=resolve; i.onerror=reject; i.src=url;
 })));
 return [...urls].sort();
}"""


def capture_chesscom(page, position, color, folder, browser_version):
    url = "https://www.chess.com/analysis?" + urlencode({"fen": position["piecePlacement"]})
    response = page.goto(url, wait_until="domcontentloaded")
    if response is None or not response.ok:
        raise ValueError("Chess.com request failed")
    board = page.locator("wc-chess-board")
    board.wait_for(state="visible")
    # Close the onboarding and cookie dialogs, without accepting tracking.
    page.wait_for_timeout(1500)
    for selector in ('button[aria-label="Close"]', '#onetrust-reject-all-handler'):
        locator = page.locator(selector)
        if locator.count() and locator.first.is_visible():
            locator.first.evaluate("e => e.click()")
    page.wait_for_timeout(500)
    if board.evaluate("e => Boolean(e.state.isFlipped)") != (color == "black"):
        page.locator('[aria-label="Flip Board"]').evaluate("e => e.click()")
    page.wait_for_function("([b,flipped]) => Boolean(b.state.isFlipped) === flipped",
                           arg=[board.element_handle(), color == "black"])
    # Exclude analysis arrows and answers, retaining the actual board and UI.
    page.add_style_tag(content=".arrows, .highlight, .element-pool, .evaluation-bar, "
                       "textarea, input { visibility: hidden !important; }")
    calibration = position["piecePlacement"] == "8/8/8/8/8/8/8/8"
    if calibration:
        # The analysis UI replaces kingless FENs with the starting position.
        # Record this calibration-only DOM edit explicitly in the sidecar.
        board.locator(".piece").evaluate_all("es => es.forEach(e => e.remove())")
    artwork = board.evaluate(ARTWORK)
    if not any('/9rdwe/' in u for u in artwork) or any(
            '/150/' in u and '/ejgfv/' not in u for u in artwork):
        raise ValueError("Live Chess.com artwork differs from the captured profile")
    expected = expand_placement(position["piecePlacement"])
    if color == "black":
        expected = [row[::-1] for row in expected[::-1]]
    page.wait_for_timeout(300)
    if board.evaluate(READ_CHESSCOM) != expected:
        raise ValueError(f"Rendered pieces differ from {position['groupId']} ({color}): {board.evaluate(READ_CHESSCOM)}")
    bounds = board.bounding_box()
    validate_bounds(bounds, VIEWPORT)
    # Check that the board is not covered by onboarding/consent overlays.
    visible = board.evaluate("""e => {
     const b=e.getBoundingClientRect();
     return [.1,.5,.9].every(x=>[.1,.5,.9].every(y=>{
      const hit=document.elementFromPoint(b.x+x*b.width,b.y+y*b.height);
      return hit===e || e.contains(hit);
     }));
    }""")
    if not visible:
        raise ValueError("A dialog covers the board")
    page.mouse.move(0, 0)
    png = page.screenshot(type="png", animations="disabled", scale="css")
    if board.bounding_box() != bounds:
        raise ValueError("Board moved during capture")
    name = f"{position['groupId']}-{color}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.png").write_bytes(png)
    annotation = dict(image=f"{name}.png", profileId=PROFILES[1], groupId=position['groupId'],
                      split=position['split'], orientation=f"{color}-bottom", boardBounds=bounds,
                      imageSize=VIEWPORT, piecePlacement=position['piecePlacement'],
                      sha256=hashlib.sha256(png).hexdigest(), source={
                          "url": url, "capturedAt": datetime.now(timezone.utc).isoformat(),
                          "browser": f"Chromium {browser_version}", "artwork": artwork,
                          "method": "Live analysis board; DOM piece geometry verified",
                          "pageModification": "Onboarding dismissed, tracking rejected; analysis arrows, highlights, evaluation bar and input fields hidden" + ("; piece DOM nodes removed for the empty tuning calibration board" if calibration else ""),
                      })
    (folder / f"{name}.json").write_text(json.dumps(annotation, indent=2) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=PROFILES)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = load_manifest(ROOT / "tools/capture.example.json")
    manifest["profileId"] = args.profile
    manifest["notes"] = (
        "Live captures with the original cross-profile position partitions; not a representative benchmark. "
        "Chess.com omits the rejected corner diagnostic pos-005 and records a DOM-cleared empty tuning calibration pos-004."
        if args.profile == PROFILES[1] else
        "Live lichess blue/cburnett captures with original cross-profile partitions, not recolored brown captures. "
        "Ten positions in both views; this is a small regression pilot, not a representative benchmark."
    )
    if args.profile == PROFILES[1]:
        manifest["positions"] = [p for p in manifest["positions"] if p["groupId"] != "pos-005"]
    targets = {split: args.output_root / prefix / args.profile for split, prefix in SPLITS.items()}
    if any(path.exists() for path in targets.values()):
        parser.error("Profile destination exists; choose a fresh output root")
    from playwright.sync_api import sync_playwright
    args.output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output_root, prefix="capture-") as temporary:
        staging = Path(temporary)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                context = browser.new_context(viewport=VIEWPORT, device_scale_factor=1,
                                              locale="en-GB", color_scheme="light")
                page = context.new_page()
                page.set_default_timeout(30000)
                for position in manifest["positions"]:
                    for color in ("white", "black"):
                        print(args.profile, position['groupId'], color, file=sys.stderr, flush=True)
                        if args.profile == PROFILES[0]:
                            capture_position(page, position, color, staging / position['split'],
                                             browser.version, profile_id=args.profile)
                        else:
                            capture_chesscom(page, position, color, staging / position['split'], browser.version)
            finally:
                browser.close()
        for split, target in targets.items():
            folder = staging / split
            subset = dict(manifest, positions=[p for p in manifest['positions'] if p['split'] == split])
            (folder / 'manifest.json').write_text(json.dumps(subset, indent=2) + '\n')
            target.parent.mkdir(parents=True, exist_ok=True)
            folder.rename(target)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
