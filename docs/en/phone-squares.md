# Photographic square dataset

**English** | [Español](../es/phone-squares.md)

The [reviewed phone corpus](phone-photo-corpus.md) now has a square export:
**160 boards × 64 cells = 10,240 RGB crops**. The ambiguous capture animation
`lichess-photo-8` is excluded. No model has been trained or changed.

**Update 2026-10-30:** the [training dataset](phone-training-data.md) reuses these
160 archives and adds 30 newly exported validation boards. The development-only
export documented below remains preserved as the original reference.

## Files and commands

Open `.cache/phone-squares-v1/index.html` to inspect all crops with their algebraic
square and piece label. The pixels are shown unchanged; labels sit outside each
crop. Each board has a compressed `.npz` in `development/`, containing:

- `images`: 64 RGB crops of 64×64 pixels, `uint8`, shape `(64, 64, 64, 3)`.
- `class_ids`: 64 labels in the project's existing 13-class order.

They are grouped archives rather than 10,240 separate image files. This matches
the array representation used by the existing classifier tools.
`verified.jsonl` links every cell to its source photo, placement, orientation,
source group, original and normalized-image hashes, reviewed corners and review
provenance. It also records canonical and photographed cell coordinates.
`dataset.json` describes preprocessing, coverage and hashes.
The versioned summary is [phone-squares-v1.json](../../data/reports/phone-squares-v1.json).

Build a new version from the reviewed annotations:

```bash
python -m tools.build_phone_squares --output .cache/phone-squares-v2 --report data/reports/phone-squares-v2.json
```

Existing output directories are never overwritten. The tool audits inputs,
verifies saved arrays and publishes the directory only after the complete build.
A missing/stale review or altered source file prevents publication.

## Geometry and labels

Each full RGB PNG is rectified from its four reviewed grid corners to 512×512
with OpenCV linear interpolation. It is then divided into exactly eight rows
and eight columns. The output order is a8 through h1. For black-bottom photos,
only the cell order is reversed on both axes; the piece pixels inside each cell
are not rotated. Highlights, arrows, moiré and coordinate glyphs are retained.

These are **crops using reference geometry**, for classifier development.
They do not measure automatic photo detection or the complete recognition path.
No balancing, augmentation, inference or prediction-based labeling is applied.
Light/dark counts describe canonical square parity, not observed RGB colors.
The borderline corner in `lichess-photo-22` remains documented in its geometry
review and is carried through into the crop index.

## Partition status

| Assignment | Boards | Squares |
| --- | ---: | ---: |
| Development | 160 | 10,240 |
| Training | 0 | 0 |
| Validation | 0 | 0 |
| Final evaluation | 0 | 0 |

**This table describes the preserved development-only export.** The new
[training export](phone-training-data.md) contains 160 training and 30 validation
boards without modifying this original export.
`partition-plan.json` records the current conservative source group, all sample
IDs (including the excluded photo), visible game-ID clues and the requirements
for a separate validation set. The six visible Chess.com game IDs do not prove
that these games are unrelated to the unidentified photos or older corpora.
Different folders, styles, positions or shooting dates are not split boundaries.

The original 161 photos therefore retain `phone-photos-unresolved-origin-v1` and
`development`. Identical positions and all views remain together. Existing
training loaders reject the `development` split; `readyForTraining` is false.
Do not change the split strings manually to bypass this safeguard.

To establish validation:

1. Collect new series from identifiable games/videos; record their URLs, game
   IDs or local source labels (such as `game-01`) and keep that identity for every
   photograph and variant. Local labels must refer to actual source groups.
2. Assign entire games/videos to validation before cropping or model selection.
3. Review source overlap and identical/equivalent positions against development
   and earlier corpora; related samples must remain together. Do not inspect the
   reserved final evaluation to tune this decision.
4. Review placements, orientations and corners, then freeze a versioned partition
   manifest. Cover the intended platforms, styles and photographic conditions.
5. Export that approved partition for the training tools, preserving validation
   frequencies. Only training may later be balanced or augmented.

The current unresolved batch can remain development/training material after an
explicit partition migration; it cannot also supply independent validation by
randomly withholding individual photos or squares. Final evaluation will be a
later, separate collection.

## New validation intake (2026-10-29)

Thirty new photographs have been supplied for validation: 10 Lichess
(`IMG_5383`–`IMG_5392`), 10 Chess.com (`IMG_5393`–`IMG_5402`) and 10 video photos
(`IMG_5403`–`IMG_5413`, excluding `IMG_5408`). They are kept separate from the
original development manifest and square export.

- Gallery and full-size JPEG review copies: `.cache/phone-validation-v1/index.html`.
- Intake manifest: [phone-validation-v1.json](../../data/manifests/phone-validation-v1.json).
- Intake checks: [phone-validation-intake-v1.json](../../data/reports/phone-validation-intake-v1.json).

Original HEICs are retained, alongside normalized full-size RGB PNG copies.
The user confirms deliberately selecting games/videos different from the previous
batch, while allowing for accidental repeated positions. This is recorded as
user-reported provenance, not independently verified source identities. All 30
photos share the conservative `phone-validation-batch-v1` group; it does not
imply one shared game or 30 independent sources. Keep the entire batch out of
training. After visual annotation and overlap review, all 30 records now have
`split: validation`. The original 161-photo development manifest is unchanged.

All **30 placements and 120 grid corners** have been visually reviewed in the
original and rectified photographs: 22 white-bottom, 8 black-bottom. The diagram
beside each rectified board is generated from the transcription, not a prediction.
Corners use full-size, EXIF-normalized RGB pixel coordinates in image
top-left/top-right/bottom-right/bottom-left order. They exclude the interface and
outer coordinate margins. Rectification retains the photographed orientation;
piece placement is canonical a8 through h1. Review is by the assistant, not an
independent human annotation pass.

The 30 distinct placements provide **1,920 labeled squares**, covering all 13
classes on both square parities. There are no identical or equivalent position
families (including rotations, reflections and color swaps) against the 160
legible development positions, and no overlap among known Chess.com game IDs.
This check does not establish independence for unidentified games or positions
not represented in the old batch. The five Chess.com game IDs visible in browser
addresses, Lichess player-pair clues and related video titles are recorded.
`IMG_5404` targets only the digital diagram, and `IMG_5406` targets the large main
board rather than the recommendation thumbnails.

Coverage is uneven: there is only one black queen on a light square and two
black kings on dark squares. These observations are useful for a pilot, but
cannot support precise performance claims for those combinations.

Open `.cache/phone-validation-v1/geometry/index.html` for the comparison gallery.
The [annotation report](../../data/reports/phone-validation-annotations-v1.json)
records coverage, source-file verification and the overlap audit. Recheck the
annotations and regenerate the gallery with:

```bash
python -m tools.review_phone_validation --output .cache/phone-validation-v1/geometry --report data/reports/phone-validation-annotations-v1.json
```

The subsequent [training export](phone-training-data.md) provides validation
arrays and loader-compatible indexes. The annotation manifest remains pinned
at its pre-export state; readiness flags in the new dataset describe current
availability. No model inference, training or reserved final evaluation has been
run. These annotations do not measure automatic photo detection.

## Checks

```bash
python -m pytest tests/test_phone_validation.py tests/test_phone_squares.py tests/test_phone_geometry.py tests/test_phone_photos.py -q
```

Tests cover 64-cell identity, black-bottom ordering without pixel rotation,
source preservation, ambiguous exclusions, stale reviews, safe publication,
overwrite refusal and rejection of unapproved validation/training assignments.
