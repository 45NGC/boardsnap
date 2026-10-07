# Evaluated recognition profiles

[Spanish](../es/profiles.md) · [Overview](README.md)

A profile specifies board appearance, piece templates and coordinate layout.
Selection is **explicit**, not automatic style recognition. Existing calls and
`boardsnap image.png` still select `lichess-cburnett-brown-v1`. A wrong piece style
on a supported background can produce wrong pieces; templates are not an
unknown-style detector. Output remains only `piecePlacement` or a structured error.

## Coverage and measured results

The [style inventory](style-inventory.md) separates board backgrounds, piece
designs and layouts. Existing digital profiles have status **evaluated** there;
their pilot results do not establish broader release compatibility or mobile
support. Pending inventory entries are not accepted as runtime profile IDs.

Results below are from **reserved source positions**, with all algorithms and
assets fixed on tuning data first. Reports include failures and every class,
background and full-position result; metrics never appear in the app response.

| Profile ID | Scope | Tuning images | Reserved images | Correct reserved squares | Exact reserved positions |
| --- | --- | ---: | ---: | ---: | ---: |
| `lichess-cburnett-brown-v1` | Existing brown board, cburnett | 16 | 4 | 256/256 | 4/4 |
| `lichess-cburnett-blue-v1` | Flat blue board, cburnett | 16 | 4 | 256/256 | 4/4 |
| `chesscom-default-green-v1` | Captured default green board and pieces, 2026-10-07 | 14 | 4 | 256/256 | 4/4 |
| `book-strategy-hatched-v1` | **Experimental**: the illustrated Gutenberg edition of *Chess Strategy* | 5 | 2 | 126/128 | **0/2** |

Digital reserved data contain the **same two positions** in both views across
all three themes. These are regression pilots, not twelve independent positions
or evidence of universal accuracy. The book pilot has two different reserved
diagrams. There are 65 images total: 51 tuning and 14 evaluation. Variants of a
position stay in the same partition across profiles, including the starting
position shared by the book and digital corpora.

Reports: [blue](../../data/reports/lichess-cburnett-blue-v1-classification-evaluation.json),
[Chess.com](../../data/reports/chesscom-default-green-v1-classification-evaluation.json),
[book](../../data/reports/book-strategy-hatched-v1-classification-evaluation.json).
Corresponding `-tuning.json` reports record 16/16, 14/14 and 5/5 complete positions.

The book experiment **has not met full-position acceptance**. Each reserved
image contains one classification error. Both failures remain visible as strict
`xfail` acceptance tests, alongside tests that preserve the measured baseline.
No thresholds/templates were adjusted after inspecting these reserved results.
Improving this profile needs new development examples and fresh independent
acceptance diagrams if these failures are used for tuning. Do not present the
126/128 square score as reliable recognition of complete book positions.

## Geometry, orientation and limitations

- Digital profiles: complete, axis-aligned boards, uniform backgrounds, no arrows,
  highlights or covered pieces. Original blue grids are 584 px; Chess.com grids are
  704 px. Tuning regression also checks translated board crops at 75% and 125%.
  The geometric minimum remains 128 px; readable coordinates require at least
  256 px and sufficient text resolution. These limits are not accuracy guarantees.
- Blue needs a tighter color tolerance than brown: otherwise nearby gray UI
  surfaces merge into the light squares and enlarge the detected bounds.
- Lichess reads files at the lower-left and ranks at the upper-right of edge
  squares. Chess.com reads lower-right files and upper-left ranks. Each uses
  its own glyph masks, extracted only from empty tuning calibration images.
  Blue includes 90 masks from the original images and readable 75%/125% resizes;
  brown and Chess.com each use 32 masks.
- The print profile uses an outer dark frame and verifies alternating brightness
  of square rims. It suppresses fine hatch with a small blur and compares up to
  four tuning examples per class/background, allowing small alignment offsets.
  Its 80 templates cover all 13 classes on both backgrounds. It requires the
  retained frame, a near-square diagram at least 256 px wide and this edition's
  symbols. Scanned full pages, perspective correction, arbitrary books and other
  fonts are not established capabilities.
- In `orientation="auto"`, print diagrams have no coordinates and assume White
  at the bottom. Digital images with absent/unreadable/conflicting coordinates
  use the same convention. Explicit `white-bottom` or `black-bottom` bypasses
  coordinate reading in every profile and takes priority over image clues. Piece arrangements are never used to guess orientation.

A profile flag changes internal processing only. It adds no confidence, alternative
positions, legality correction, game state or extra FEN fields. Book failures
still return the recognized position when processing succeeds, allowing the app
editor to correct it; the experimental status is documented, not injected into JSON.

## Commands

```bash
boardsnap image.png --profile lichess-cburnett-blue-v1
boardsnap image.png --profile chesscom-default-green-v1
# Experimental, not accepted for reliable whole-position recognition:
boardsnap diagram.png --profile book-strategy-hatched-v1

python -m tools.preview_detection data/tuning/chesscom-default-green-v1 \
  --profile chesscom-default-green-v1 --recognition \
  --output-dir .cache/chesscom-preview

python -m tools.evaluate_classification --profile chesscom-default-green-v1 \
  --split evaluation --output .cache/chesscom-report.json
python -m pytest tests/test_profiles.py
```

Python callers use `recognize_image(path, profile="...", orientation="auto")`.
The pipeline also accepts explicit `white-bottom`/`black-bottom`; see [orientation](orientation.md). Detection, orientation
and classification accept the `profile` keyword; the input orientation override belongs to the pipeline. Unknown CLI profiles are usage errors
(exit 2, diagnostics on stderr); unknown Python profiles raise `ValueError`.
The preview tool defaults to the original brown folder, so adding new datasets
does not accidentally process every theme with the brown profile.

## Collection and rebuild

Live digital captures are reproducible through the optional Playwright tool:

```bash
python -m pip install -e '.[dev,capture]'
python -m playwright install chromium
python -m tools.capture_profiles lichess-cburnett-blue-v1 --output-root .cache/new-blue
python -m tools.capture_profiles chesscom-default-green-v1 --output-root .cache/new-chesscom
```

Use the same `PLAYWRIGHT_BROWSERS_PATH` at installation and capture if maintaining
browsers in `.cache/ms-playwright`. A batch is staged and published only after all
samples pass DOM geometry/piece checks. Existing destinations are refused.
Lichess blue is selected through the site's preferences. Chess.com source artwork
IDs `9rdwe` (board) and `ejgfv` (pieces) are pinned and recorded; a future default
change must be evaluated as a new profile. The name does not promise support for
all designs called “green” or any future default.

Chess.com rejects the original illegal corner diagnostic (`pos-005`), so it is
omitted. The empty tuning calibration (`pos-004`) explicitly removes piece DOM
nodes because analysis substitutes the starting position for an empty FEN.
That modification is recorded; it is not an untouched live empty-board sample.
Other captures verify the actual rendered pieces against requested positions.
No held-out image is generated from tuning crops or recolored from another image.

Book sources are **actual downloaded JPEG diagrams**, decoded to RGB and saved
losslessly as PNG; they were not redrawn with the recognition templates. Sidecars
record original URLs/hashes, manually transcribed positions and visually reviewed
approximate interior bounds. Tuning diagrams: 1, 4, 5, 6, 8. Reserved: 3, 7.
Diagram 2 contains arrows and is outside this pilot. See the
[book manifest](../../data/manifests/book-strategy-hatched-v1.json) and
[source notices](../../data/THIRD_PARTY_NOTICES.md).

Rebuild shipped assets only from their committed tuning partitions:

```bash
python -m tools.build_piece_templates --profile lichess-cburnett-blue-v1
python -m tools.build_coordinate_templates --profile lichess-cburnett-blue-v1
python -m tools.build_piece_templates --profile chesscom-default-green-v1
python -m tools.build_coordinate_templates --profile chesscom-default-green-v1
python -m tools.build_piece_templates --profile book-strategy-hatched-v1
```

The book builder uses no coordinate asset. Assets include source hashes and crop
mappings; recognition reads only installed package assets and input pixels.
Keep third-party artwork notices with both screenshots and derived templates.

For a new profile: acquire distinct annotated source positions, fix partitions,
cover all classes/backgrounds and orientation cases, build from tuning only,
freeze the implementation, evaluate full positions and negatives, then retain
all previous profiles' regression tests. A PyTorch comparison remains a separate
experiment with training, validation and final evaluation groups.
