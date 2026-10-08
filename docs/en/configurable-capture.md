# Configurable captures

[Español](../es/configurable-capture.md)

Run these repository utilities from the repository root. They collect labeled
images; they do not add recognition profiles or train a model. Legacy capture
commands remain available for the original two-partition datasets.

## Clean platform screenshots

Install the optional browser dependency once:

```bash
python -m pip install -e '.[dev,capture]'
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright"
python -m playwright install chromium
python -m tools.capture_batch capture tools/capture-clean.example.json --output-root .cache/configurable-captures --validate-only
python -m tools.capture_batch capture tools/capture-clean.example.json --output-root .cache/configurable-captures
```

The example requests **16 images**: two training positions, four configurations
(Lichess green/Merida and purple/Alpha; Chess.com blue/Classic and brown/Bases),
each in both orientations. Both positions share a source group: this is a
tool-verification pilot, not an independent accuracy benchmark. No evaluation
positions are used to debug capture. Outputs in `.cache/` are ignored by Git.
The [pilot verification record](../../data/reports/configurable-capture-pilot-v1.json)
records the 16 local PNG hashes, configuration and provenance without committing
the screenshots. An additional two-image size check uses a 1024 × 900 viewport
and pixel density 2 (2048 × 1800 PNGs), in `g1-size-pilot-v1`.

Copy the recipe and assign a new `batchId` to expand it. It has exactly:
`schemaVersion: 1`, `batchId`, `positionIds`, and `configurations`.
Each configuration specifies:

| Field | Meaning |
| --- | --- |
| `id` | Unique lowercase configuration identifier |
| `platform` | `lichess` or `chesscom` |
| `boardTheme`, `pieceSet` | Independent style names, lowercase with hyphens |
| `orientations` | One or both of `white-bottom`, `black-bottom` |
| `viewport` | Browser CSS-pixel `width` and `height`, integers 320–2560 |
| `deviceScaleFactor` | 1, 2 or 3; saved pixels per CSS pixel |
| `conditions` | Currently exactly `["clean"]` |

Viewport controls responsive board size; it does not prescribe a board width.
Small viewports can fail if the complete board is not visible. Layouts remain
desktop web: a narrow viewport does not prove native mobile compatibility.
Style availability is checked live; an accepted name does not imply recognition
support. Unavailable styles fail instead of falling back silently.
`--validate-only` checks recipe/partition structure without checking remote style
availability. `--headed` displays Chromium. Internet access is required for capture.

The output layout is:

```text
<output-root>/digital-positions-v1/<batchId>/
    batch.json
    <training|validation|evaluation>/<configurationId>/
        <positionId>-<orientation>.png
        <positionId>-<orientation>.json
```

Each sidecar records canonical `piecePlacement`, inherited position/group/split,
orientation, configuration, image dimensions and SHA-256, bounds in **saved PNG
pixels**, source URL, browser version, UTC timestamp, artwork URLs and checks.
Bounds may be fractional; right/bottom are exclusive (`x + width`, `y + height`).
The batch records the recipe and a hash of the frozen position manifest. A different plan hash
under an existing dataset ID is rejected.
Never split individual themes, orientations or square crops independently.

Publication is atomic: a failed capture leaves no partial batch. Existing batches
are never overwritten; use a new batch ID. A per-dataset lock prevents concurrent
publication. Exit codes are 0 for success, 2 for invalid input/verification errors,
and 1 for other browser failures. Progress goes to stderr; stdout is a status
message, not the recognition CLI's JSON contract.

## What is actually verified

Before **and** after taking the screenshot, the adapter checks rendered piece
roles/colors and their square geometry against the expected placement, orientation,
computed board/piece artwork URLs, loaded assets, visibility, board coverage,
and absence of visible markings. It rejects moving pieces and changes during
capture. The PNG is decoded and its dimensions/bounds checked before saving.
A style selector's label alone is insufficient.

Lichess uses its native anonymous appearance controls and asset manifest.
Chess.com reads the public theme catalogue opened by its Board settings panel,
accepts only unlocked web assets and top-down pieces, then applies those assets
to the **local board renderer**. Anonymous preference saves can fail while the
selector displays the requested name. This approach avoids account preference
writes and verifies the artwork actually rendered.

These are modified automated pages: resize/answer fields are hidden on Lichess;
onboarding and consent dialogs are dismissed and arrows/highlights/answer inputs
are hidden on Chess.com. All modifications are recorded. They are not untouched
real-use captures. Browser integrations depend on live DOM/asset APIs and may
need maintenance when the platforms change. Mark generation is deferred;
automated requests for arrows or highlights explicitly fail.

## Import real-use screenshots

Use original PNG screenshots taken during actual analysis/play, independently of
the automated editor. Review the position, orientation, complete board bounds,
style, layout and observed marks manually; keep related positions from a game in
one source group. No real-use images are fabricated or supplied by this command.

`import-real` currently accepts only positions already in the frozen plan. For
an unrelated real game, the position-plan schema must first be extended to
represent real-game provenance and freeze its group/split assignment. The current
validator supports generated sequences only; `--manifest` does not bypass that
constraint. Do not relabel a different board as an existing position to make it fit.

Create a JSON file with `schemaVersion: 1`, a new `batchId` and a `samples` list.
Every sample contains:

- `id`, `positionId`, `image` (path relative to this JSON), `sha256` of original bytes.
- `orientation`, `reviewed: true`, `reviewedPlacement` (canonical first FEN field).
- `boardBounds: {"x": ..., "y": ..., "width": ..., "height": ...}` in original PNG pixels.
- `configuration`: `platform`, `boardTheme`, `pieceSet`, `layoutId`, `conditions`.
  Conditions are `["clean"]` or observed `arrows`, `highlights`, `badges`; never
  combine clean with marks.
- `source`: `url`, `capturedAt`, `client`, `clientVersion`, `sourceGroupId`,
  `reviewedBy`, `reviewedAt`. Use UTC ISO timestamps and a stable game/session ID.
  Clients: `desktop-web`, `mobile-web`, `android-app`, `ios-app`.

```bash
sha256sum screenshots/original.png
python -m tools.capture_batch import-real review.json --output-root data/datasets --validate-only
python -m tools.capture_batch import-real review.json --output-root data/datasets
```

Review is a human assertion, not automated visual proof. Hashes ensure reviewed
bytes have not changed. Imported PNGs are copied unchanged, under
`<split>/real-use/`; provenance explicitly says human review, no DOM evidence.
The importer rejects conflicting labels for identical bytes and source groups
crossing partitions, including earlier batches **in the same output root**.
Use one authoritative root: separate roots cannot enforce global isolation.
Importing marked images does not make the recognizer support marks.

Keep source/asset attribution with any corpus promoted into version control;
see [third-party notices](../../data/THIRD_PARTY_NOTICES.md). The pilot stays
local until reviewed for inclusion; existing recognition fixtures are unchanged.

## Tests

```bash
python -m pytest tests/test_capture_batch.py tests/test_capture_sites.py
BOARDSNAP_BROWSER_TESTS=1 python -m pytest tests/test_capture_batch.py tests/test_capture_sites.py
python -m pytest
```

Browser tests use local invented DOM/artwork fixtures with intercepted requests,
including both orientations, two pixel densities, wrong artwork/pieces, clipping,
covering dialogs, markings and changes during capture. Catalogue tests reject
locked, incomplete, non-web and 3D styles. Import tests check review, original
bytes, partition inheritance, atomic failure and cross-batch game isolation.
These tests measure collection integrity, not recognition accuracy.
