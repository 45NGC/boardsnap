# Capturing lichess samples

For the new three-partition plan, use [configurable platform captures](configurable-capture.md).
This page documents the original fixed-profile collection tool.

**English** | [Spanish](../es/capture-data.md) · [Overview](README.md)

This guide records the original brown-profile implementation. See [evaluated profiles](profiles.md) for subsequent digital styles, the experimental book profile and current coverage.

`tools/capture_lichess.py` collects screenshots and annotations from the live
[lichess editor](https://lichess.org/editor). It is a repository utility,
separate from the installed engine, and does not recognize images.

## Installation

From the repository root:

```bash
source .venv/bin/activate
python -m pip install -e '.[dev,capture]'
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright"
python -m playwright install chromium
```

Playwright is an optional dependency; Chromium is a separate download.
`.venv/` and `.cache/` are ignored by Git. Export the browser path again in new
terminals before running captures or browser tests. Linux may also need the
system libraries listed in the [Playwright installation guide](https://playwright.dev/python/docs/intro).
The tool uses a fresh browser context, not your personal browser profile.
No lichess account is required.

## Prepare positions

The first reviewed dataset is already stored in the repository. Its fixed
[collection manifest](../../data/manifests/lichess-cburnett-brown-v1.json) is
separate from the editable example below. To repeat collection, pass that
manifest with a fresh `--output-root`; existing dataset folders are protected.
See [tuning data](tuning-data.md) and [evaluation data](evaluation-data.md).

Copy [`tools/capture.example.json`](../../tools/capture.example.json) to a new
JSON file and edit it. Its 10 distinct positions produce 20 images: 16 for
tuning and 4 for evaluation, keeping both orientations in the same partition.
They include openings, constructed middlegame/endgame positions, an empty board
and a corner diagnostic. This broader pilot checks the capture workflow; it is
not enough to train a model or measure general recognition accuracy.

| Field | Meaning |
| --- | --- |
| `profileId` | Must be `lichess-cburnett-brown-v1` |
| `notes` | Optional provenance and asset permission notes |
| `positions` | Nonempty list of the position objects below |
| `positions[].groupId` | Unique lowercase identifier: letters, digits, `_`, `-`; 1–64 characters |
| `positions[].split` | `tuning` or `evaluation`, chosen before capturing |
| `positions[].piecePlacement` | Only the first FEN field, ordered from a8 to h1 |

Do not append turn, castling or other FEN fields. Syntax is checked without
requiring a legal chess position. Both orientations are generated automatically.
Duplicate groups and positions are rejected, including across splits. Keep
future crops and variants in the original group's partition. Related positions
from one game or source should also share a split; assign this yourself because
the tool cannot infer those relationships. Later, separate training and
validation within tuning.

## Validate and capture

Check the manifest and destinations without a browser:

```bash
python -m tools.capture_lichess tools/capture.example.json --validate-only
```

First try a scratch output directory:

```bash
python -m tools.capture_lichess tools/capture.example.json --output-root /tmp/boardsnap-pilot
```

Add `--headed` to watch Chromium (requires a graphical session). After reviewing
the pilot, collect your complete manifest into the repository by omitting
`--output-root`, running from the repository root:

```bash
python -m tools.capture_lichess path/to/positions.json
```

Output directories are `data/tuning/lichess-cburnett-brown-v1/` and
`tests/fixtures/evaluation/lichess-cburnett-brown-v1/`. Each contains a
`manifest.json` with only its own positions, plus files such as:

```text
pos-001-white.png
pos-001-white.json
pos-001-black.png
pos-001-black.json
```

Captures are staged temporarily and published after every browser capture
succeeds. Existing profile directories in either partition are rejected, even
on later runs. There is no overwrite, resume or append mode. Prepare a complete
manifest before collecting a batch; use fresh scratch roots for experiments.
Do not merge separate batches without checking groups and positions across
partitions yourself.

Exit codes: `0` success, `1` capture/dependency failure, `2` invalid arguments,
manifest or existing destination. Progress/errors go to stderr; stdout contains
a brief summary. This is separate from the [recognition JSON CLI](cli.md).

## Profile and verification

The fixed collection profile uses cburnett 2D pieces, a brown board, internal
coordinates, light color scheme, English locale, a 1280 × 1000 viewport and
device scale factor 1. Fresh browser defaults currently supply those pieces
and board; the script checks them and stops if they differ. The board retains
its native page size.

For each orientation the script verifies the editor's FEN and rendered piece
locations, waits for artwork, rejects highlights/drawings and measures the grid.
It takes a viewport PNG with [Playwright screenshots](https://playwright.dev/python/docs/screenshots).
FEN/URL fields and the board resize handle are hidden with CSS visibility.
The grid and surrounding layout remain intact; other editor controls and spare
pieces outside the board remain visible. The tool does not rotate PNGs.

## Annotations

Each JSON sidecar contains `image`, `profileId`, `groupId`, `split`,
`orientation`, `boardBounds`, `imageSize`, `piecePlacement`, `source` and `sha256`.
These are dataset metadata, not additions to the engine's output contract.

- `orientation` is `white-bottom` or `black-bottom`. `piecePlacement` remains
  identical for the same position in both images.
- `boardBounds` contains `x`, `y`, `width`, `height` of the 64-square grid,
  excluding external margins. Origin is the PNG's top-left, x grows rightward
  and y downward. Bounds cover `[x, x + width)` and `[y, y + height)`.
  Fractional coordinates are preserved because browser layout uses subpixels.
  Device scale factor 1 and CSS-scale screenshots make the units PNG pixels.
  Future integer crops should round outward.
- `imageSize` records PNG dimensions; `source` records URL, UTC timestamp,
  browser/Playwright versions, rendering settings and page modifications.
- `sha256` identifies the exact PNG bytes.

Labels come from the manifest and are checked against the DOM. This prepares
data, but is not an independent recognition test. Manually review screenshots,
orientation and bounds, especially evaluation samples. Annotation files must
never be inputs to the image recognizer. Record source and asset permissions
before redistributing captures.

## Tests and limitations

Normal tests do not launch browsers or access the network:

```bash
python -m pytest
```

After installing Chromium, enable offline browser checks explicitly:

```bash
BOARDSNAP_BROWSER_TESTS=1 python -m pytest tests/test_capture_lichess.py -m integration
```

These tests intercept page requests with a local HTML fixture. They check PNG
creation, orientation, annotations and rejection of wrong positions, themes and
overlays. They do not test lichess availability. Use a small live capture run
when changing the adapter.

The tool depends on lichess's current editor DOM, styles and assets. Site
changes or network failures may require maintenance. Captures are sequential
with a short pause between pages; the tool does not bypass access restrictions.
Only this collection profile is supported. Collecting images does not mean the
engine recognizes that style. More resolutions, themes, mobile screenshots,
negative samples and book diagrams remain future work. Keep
[tuning](tuning-data.md) and [evaluation](evaluation-data.md) separate.
