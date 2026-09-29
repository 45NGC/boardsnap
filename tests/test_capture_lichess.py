"""Dataset validation and optional, offline browser checks for the capture tool."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct

import pytest

# Load the repository utility without installing tools as an engine package or
# depending on whether pytest was launched through `python -m`.
_script = Path(__file__).resolve().parents[1] / "tools/capture_lichess.py"
_spec = importlib.util.spec_from_file_location("capture_lichess", _script)
assert _spec is not None and _spec.loader is not None
capture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(capture)


PLACEMENT = "R7/8/8/8/8/8/8/7k"


def manifest_file(tmp_path, positions=None):
    path = tmp_path / "positions.json"
    path.write_text(json.dumps({
        "profileId": capture.PROFILE,
        "positions": positions if positions is not None else [
            {"groupId": "pos-001", "split": "tuning", "piecePlacement": PLACEMENT}
        ],
    }), encoding="utf-8")
    return path


@pytest.mark.unit
def test_example_manifest_is_valid():
    path = Path(__file__).resolve().parents[1] / "tools/capture.example.json"
    positions = capture.load_manifest(path)["positions"]
    assert len(positions) == 10
    assert sum(position["split"] == "tuning" for position in positions) == 8
    assert sum(position["split"] == "evaluation" for position in positions) == 2
    placements = [position["piecePlacement"] for position in positions]
    assert "8/8/8/8/8/8/8/8" in placements
    assert set(capture.SYMBOLS) <= set("".join(placements))


@pytest.mark.unit
@pytest.mark.parametrize("placement", [
    None, [], "8/8", "9/8/8/8/8/8/8/8", "8/8/8/8/8/8/8/7x",
    "44/8/8/8/8/8/8/8", "R7/8/8/8/8/8/8/7k w - - 0 1",
])
def test_rejects_invalid_placement(placement):
    with pytest.raises(ValueError):
        capture.expand_placement(placement)


@pytest.mark.unit
@pytest.mark.parametrize("field,value", [
    ("groupId", "../outside"), ("groupId", "../"), ("groupId", ""),
    ("groupId", 1), ("split", "training"), ("split", []),
])
def test_rejects_unsafe_manifest_values(tmp_path, field, value):
    position = {"groupId": "pos-001", "split": "tuning", "piecePlacement": PLACEMENT}
    position[field] = value
    with pytest.raises(ValueError):
        capture.load_manifest(manifest_file(tmp_path, [position]))


@pytest.mark.unit
@pytest.mark.parametrize("same_group", [True, False])
def test_prevents_position_or_group_leakage(tmp_path, same_group):
    positions = [
        {"groupId": "a", "split": "tuning", "piecePlacement": PLACEMENT},
        {"groupId": "a" if same_group else "b", "split": "evaluation",
         "piecePlacement": "8/8/8/8/8/8/8/8" if same_group else PLACEMENT},
    ]
    with pytest.raises(ValueError, match="Duplicate"):
        capture.load_manifest(manifest_file(tmp_path, positions))


@pytest.mark.unit
def test_validate_only_does_not_create_output(tmp_path, capsys):
    root = tmp_path / "output"
    assert capture.main([str(manifest_file(tmp_path)), "--output-root", str(root), "--validate-only"]) == 0
    assert not root.exists()
    assert "Valid manifest" in capsys.readouterr().out


@pytest.mark.unit
def test_existing_partition_is_never_overwritten(tmp_path, capsys):
    folder = capture.destination(tmp_path, "evaluation")
    folder.mkdir(parents=True)
    sample = folder / "keep.png"
    sample.write_bytes(b"original")
    assert capture.main([str(manifest_file(tmp_path)), "--output-root", str(tmp_path)]) == 2
    assert sample.read_bytes() == b"original"
    assert "already exists" in capsys.readouterr().err


@pytest.mark.unit
@pytest.mark.parametrize("content", ["{", "[]", "null", '{"profileId":"unknown"}'])
def test_invalid_manifest_has_clear_cli_error(tmp_path, capsys, content):
    path = tmp_path / "invalid.json"
    path.write_text(content, encoding="utf-8")
    assert capture.main([str(path), "--validate-only"]) == 2
    assert "Invalid capture request" in capsys.readouterr().err


@pytest.mark.unit
@pytest.mark.parametrize("bounds", [
    {"x": -1, "y": 0, "width": 512, "height": 512},
    {"x": 1000, "y": 0, "width": 512, "height": 512},
    {"x": 0, "y": 900, "width": 512, "height": 512},
    {"x": 0, "y": 0, "width": 512, "height": 500},
    {"x": 0, "y": 0, "width": 100, "height": 100},
])
def test_rejects_clipped_or_unsuitable_boards(bounds):
    with pytest.raises(ValueError):
        capture.validate_bounds(bounds, capture.VIEWPORT)


def require_browser_tests():
    if os.environ.get("BOARDSNAP_BROWSER_TESTS") != "1":
        pytest.skip("Set BOARDSNAP_BROWSER_TESTS=1 to run offline Chromium tests")
    return pytest.importorskip("playwright.sync_api")


@pytest.fixture
def browser_page():
    playwright = require_browser_tests()
    with playwright.sync_playwright() as engine:
        browser = engine.chromium.launch()
        try:
            context = browser.new_context(viewport=capture.VIEWPORT, device_scale_factor=1)
            yield context.new_page(), browser.version
        finally:
            browser.close()


def editor_html(color):
    # A tiny local DOM fixture, not a lichess screenshot or recognition dataset.
    white_xy, black_xy = ((0, 0), (448, 448)) if color == "white" else ((448, 448), (0, 0))
    return f"""<!doctype html><html><head><style>
    .cg-wrap {{ width:512px; height:512px; }}
    cg-board {{ display:block; position:absolute; left:64px; top:80px; width:512px; height:512px; }}
    cg-board, piece {{ background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='64' height='64'%3E%3Crect width='64' height='64' fill='tan'/%3E%3C/svg%3E"); }}
    piece {{ display:block; position:absolute; width:64px; height:64px; }}
    </style></head><body data-board="brown" data-piece-set="cburnett" class="coords-in">
    <div class="main-board"><div class="cg-wrap orientation-{color}"><cg-board>
    <piece class="white rook" style="left:{white_xy[0]}px;top:{white_xy[1]}px"></piece>
    <piece class="black king" style="left:{black_xy[0]}px;top:{black_xy[1]}px"></piece>
    </cg-board></div></div><div class="copyables"><input value="{PLACEMENT} w - - 0 1"></div>
    </body></html>"""


@pytest.mark.integration
@pytest.mark.parametrize("color", ["white", "black"])
def test_offline_browser_captures_real_png_and_canonical_annotation(browser_page, tmp_path, color):
    page, browser_version = browser_page
    page.route("**/*", lambda route: route.fulfill(body=editor_html(color), content_type="text/html"))
    position = {"groupId": "corners", "split": "tuning", "piecePlacement": PLACEMENT}
    capture.capture_position(page, position, color, tmp_path, browser_version)
    png = (tmp_path / f"corners-{color}.png").read_bytes()
    annotation = json.loads((tmp_path / f"corners-{color}.json").read_text())
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", png[16:24]) == (1280, 1000)
    assert annotation["boardBounds"] == {"x": 64, "y": 80, "width": 512, "height": 512}
    assert annotation["piecePlacement"] == PLACEMENT
    assert annotation["orientation"] == f"{color}-bottom"
    assert annotation["sha256"] == hashlib.sha256(png).hexdigest()
    assert page.locator(".copyables").evaluate("e => getComputedStyle(e).visibility") == "hidden"


@pytest.mark.integration
@pytest.mark.parametrize("fault", ["wrong-pieces", "wrong-fen", "wrong-theme", "overlay"])
def test_browser_rejects_mislabeled_or_occluded_samples(browser_page, tmp_path, fault):
    page, browser_version = browser_page
    html = editor_html("white")
    if fault == "wrong-pieces":
        html = html.replace('class="white rook"', 'class="white queen"')
    elif fault == "wrong-fen":
        html = html.replace(f'value="{PLACEMENT}', 'value="8/8/8/8/8/8/8/8')
    elif fault == "wrong-theme":
        html = html.replace('data-board="brown"', 'data-board="blue"')
    else:
        html = html.replace("</cg-board>", '<square class="selected"></square></cg-board>')
    page.route("**/*", lambda route: route.fulfill(body=html, content_type="text/html"))
    position = {"groupId": "corners", "split": "tuning", "piecePlacement": PLACEMENT}
    with pytest.raises(ValueError):
        capture.capture_position(page, position, "white", tmp_path, browser_version)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.integration
def test_failed_batch_does_not_publish_partial_dataset(tmp_path, monkeypatch):
    require_browser_tests()
    original_capture = capture.capture_position
    calls = 0

    def fail_after_first_capture(page, position, color, folder, browser_version):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("Interrupted batch")
        page.route("**/*", lambda route: route.fulfill(body=editor_html(color), content_type="text/html"))
        original_capture(page, position, color, folder, browser_version)
        assert (folder / "corners-white.png").exists()

    monkeypatch.setattr(capture, "capture_position", fail_after_first_capture)
    manifest = {"positions": [{"groupId": "corners", "split": "tuning", "piecePlacement": PLACEMENT}]}
    with pytest.raises(ValueError, match="Interrupted batch"):
        capture.capture_dataset(manifest, tmp_path)
    assert calls == 2
    assert list(tmp_path.iterdir()) == []
