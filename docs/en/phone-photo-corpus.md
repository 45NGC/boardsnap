# Screen photograph corpus

**English** | [Español](../es/phone-photo-corpus.md)

## Status — 28 October 2026

The **161 photographs are enough to start the geometry pilot**. They are not yet
a training-ready dataset or evidence of photographic recognition support. This
review ran no recognition or training; models and production input are unchanged.

| Source according to directory | Photos | Enlarged reviews | Transcribed placements |
| --- | ---: | ---: | ---: |
| Chess.com | 55 | 55 | 55 |
| Lichess | 53 | 53 | 52 |
| Videos | 53 | 53 | 53 |
| Total | 161 | 161 | 160 |

Enlarged review is complete for all active photos: **160 have transcribed
placements and one is ambiguous**. There are 89 white-bottom views (including
the ambiguous image) and 72 black-bottom views, identified using visible
board edge coordinates.

- `IMG_5205.HEIC`: deleted by the user and removed from active samples.
  A removal record retains its hash and reason; its derived copy is not
  reused as an active sample.
- `lichess-photo-8.HEIC`: a black king and white rook overlap on f7 during a capture
  animation. Orientation is recorded, but `piecePlacement: null`.
  It remains ambiguous and excluded from complete-placement examples.
  To replace it, pause playback and wait for the animation to finish.

The 161 originals and their PNGs retain their recorded hashes. There are no
exact file duplicates. EXIF identifies an **iPhone 8** in every photo. No
direct reference screenshots, FENs or PGNs were supplied. Remaining originals
are unchanged.

The 27 October addition contains **72 photos** (25 Chess.com, 23 Lichess,
24 video), all visually transcribed and exported to JPEG/PNG. The earlier
89 records and their image bytes are preserved. No model predictions were
used as labels.

## Files and commands

- Originals: `.cache/real-use-tests/phone-photos/`.
- Copies and contact sheets: `.cache/phone-photos-v1/`.
- JPEG review copies: `.cache/phone-photos-v1/jpg/`, organized into
  `chesscom`, `lichess` and `video`, using readable names with a `.jpg` extension.
- Open `.cache/phone-photos-v1/index.html` in a browser to map each original
  filename to its full-size copy, status, orientation and placement.
- [Inventory and annotations](../../data/manifests/phone-photos-v1.json).
- [Integrity and coverage report](../../data/reports/phone-photos-intake-v1.json).

Originals are named `chesscom-photo-1.HEIC` through `chesscom-photo-55.HEIC`,
`lichess-photo-1.HEIC` through `lichess-photo-53.HEIC` and `video-photo-1.HEIC`
through `video-photo-53.HEIC`, in their respective directories. Numbering follows
the previous camera filename order. The manifest retains `previousOriginalPath`
and stable sample IDs; the local mapping is stored at
`.cache/real-use-tests/phone-photos/rename-map.json`. PNG review copies retain
their internal names and the review page displays the new original names. Append
new photos starting at 56, 54 and 54 respectively; do not renumber existing ones.

On 24 October, all 89 photos were exported to full-size sRGB JPEG at quality 95
without chroma subsampling. The additional 72 received the same conversion on
27 October. The review page links to all 161 JPEGs.
`jpg/export.json` records the mapping and hashes. These are compressed convenience
copies: original HEICs and annotation-linked PNGs remain unchanged. They are not
additional samples and do not change the formats of other project corpora.

Images remain ignored by Git. The manifest and report are versionable; neither
contains GPS or wholesale EXIF dumps. Conversion uses the optional `photos`
extra, separate from engine dependencies:

```bash
python -m pip install -e '.[photos]'
```

This batch is already prepared. Check it without repeating conversion:

```bash
python -m tools.prepare_phone_photos audit --manifest data/manifests/phone-photos-v1.json --report data/reports/phone-photos-intake-v1.json
```

To prepare a batch from scratch, use new destinations. The tool refuses to
overwrite existing review work or write inside the originals directory:

```bash
python -m tools.prepare_phone_photos prepare --source .cache/real-use-tests/phone-photos --output .cache/phone-photos-v1 --manifest data/manifests/phone-photos-v1.json
```

Copies preserve full size, apply file orientation and convert embedded ICC
colors to RGB sRGB. Untagged inputs record the sRGB assumption. They are not
cropped, rectified or sharpened. Derived PNGs **are not direct reference
screenshots**. Original/copy hashes, dimensions and conversion metadata are
recorded. Production still accepts PNG/JPEG: installing this extra does not add
HEIC or perspective correction to the engine.

## Pilot labels

These are **assistant visual transcriptions**, without BoardSnap predictions,
with `userVerified: false`. They contain only a8-to-h1 piece placement, with
orientation and annotation provenance recorded separately. Turn, castling and
en-passant fields are not invented. Internal annotations do not change the
output JSON contract.

The 23 October review added 71 transcriptions and one ambiguous case to the
previous 17 transcriptions. New labels include `visualRows`: rows top to bottom
and columns left to right **as seen in the photograph**, with uppercase for
white pieces. This is not canonical FEN in a black-bottom view. The auditor
checks that reversing both axes in that case produces `piecePlacement`.
All 72 labels added on 27 October also include these visual rows.
Orientation describes the view, not whose turn it is.

The 160 placements contain **10240 squares**, covering all 13 classes on both
canonical square colors. There are **153 distinct placements**, which does not
mean 153 independent games. Seven equal-placement pairs are recorded:

- `video-photo-9` / `video-photo-10`.
- `video-photo-14` / `video-photo-15`.
- `video-photo-16` / `video-photo-18`.
- `video-photo-26` / `video-photo-27`.
- `chesscom-photo-26` / `lichess-photo-1`, across Chess.com and Lichess.
- `lichess-photo-31` / `lichess-photo-39`, blue versus green background.
- `video-photo-37` / `video-photo-40`, without versus with arrows.

Coverage remains unbalanced: only 19 white kings and 23 black queens
on light squares. Counts include related positions and variants; they are not
accuracy metrics or independent sample counts. Eight-rank format, orientation
conversion and file integrity were checked. Assistant visual review does not
replace an independent second label review before training.

## Transcription and corner review

On 28 October, all **161 rectified photographs** were compared visually with
diagrams rendered from their existing transcriptions. All 160 placements and
their orientations matched the visible pieces; none needed correction.
`lichess-photo-8` remains ambiguous and excluded from classification. This is a
second assistant visual pass, **not independent human verification**;
`userVerified` remains `false`.

All **161 photographs have four annotated corners** in `boardCorners`. These
are `[x, y]` grid-boundary coordinates in the full RGB PNG after EXIF orientation
normalization. The origin is the image top-left; x increases rightward and y
downward. Order is **top-left, top-right, bottom-right, bottom-left**, regardless
of chess orientation. Clocks and interface margins are excluded. Do not apply
EXIF orientation again.

Contour proposals were refined against interior grid lines, then rectified
crops and eight-row/eight-column alignment were reviewed visually.
`video-photo-45` required manual correction of a proposal that included left
and bottom margins, followed by another visual check. In `lichess-photo-22`,
the top-right corner touches the image boundary: a line-fit extrapolation of
about two full-image pixels was constrained to that boundary. Minimal clipping
of that corner cannot be excluded; its annotation records this limitation and
it should not be treated as an example with an entirely unobstructed border.

`geometryReview` binds corners to the PNG hash and records method, date and
reviewer. `label.rectifiedReview` snapshots the reviewed placement, orientation
and corners. The auditor rejects invalid/crossed coordinates and reviews that
no longer match the image, geometry or label. These are dataset references,
**not photographic detector outputs**, and do not demonstrate CLI recognition.

Open `.cache/phone-photos-v1/geometry/index.html` to compare the outlined photo,
rectified board and transcription diagram. The existing intake page at
`.cache/phone-photos-v1/index.html` also links each comparison. Regenerate them:

```bash
python -m tools.review_phone_geometry
```

The tool verifies hashes and produces 512×512 review crops with linear
interpolation, retaining the photographed square order. It does not rotate
piece glyphs or modify originals. Rectified PNGs and `geometry/export.json`
are local review artifacts, not a partitioned training-square dataset.
No model was trained or modified.

The [crops from all 160 valid photos](phone-squares.md) are prepared: 10,240 traced squares, all in development. Separate validation by source remains pending.

## Groups and partitions

**161 development, 0 training, 0 validation and 0 final evaluation.**
This is a safe provisional state, not a completed training split.

Related game sequences and a shared video context are visible. Provenance has
not been systematically recorded. Different positions or directories cannot be
assumed independent. The batch shares `phone-photos-unresolved-origin-v1`;
the auditor rejects moving isolated records to other partitions. Trainers must
not consume this intake format.

Before training, identify games/videos, join variants, check overlap with
previous corpora and freeze a new partition version. The initial position in
`video-photo-4` is already-known content. No reserved final evaluation data was
consulted for this inventory.

If provenance cannot be recovered, this batch can remain development material.
Validation will need new identified game series separated from collection
onward. Independent final evaluation will be collected later, after freezing
the candidate and criteria.

Some source evidence is now recorded: six game IDs are visible in browser
addresses in the new Chess.com photos; players and video titles provide partial
clues elsewhere. These are visual observations, not verified downloads or proof
of independence from the old corpus. The user cannot recover further source
information, so the conservative development grouping is retained.

In `video-photo-37`–`45` and `48`–`53`, labels describe the **large central
board**; secondary boards appear in the video or recommendations. This is
recorded in `source.targetBoard` and `multiple-visible-boards`. Corner annotations
select that target. These are not evidence that the current single-board
CLI supports multiple boards automatically.

## What to add

**No more photos are needed before the geometry pilot.** The new batch adds
blue and green backgrounds, wood textures, several different piece silhouettes,
both orientations, arrows, check highlights and legal-move dots. Exact official
theme names remain unconfirmed. It still uses the same iPhone 8 and broadly
similar monitor environment; moire and color bands are visible.

With labels and corners reviewed, next prepare rectification and square export
under a safe partition policy. If later measurements show gaps, add targeted examples from identified game/video series, other
angles, lighting, screens or cameras, and separate negative controls (no board
or clipped board). Keep a direct screenshot where possible; transcribing a
position does not recover missing pixels or provenance.

The ambiguous image is already excluded from classification. Closing phase 5
still requires safe source partitions and the data format consumed by training. If source identities
cannot be recovered, keep this corpus in development and collect new identified
series for validation. The total photo count alone does not guarantee accuracy.

## Checks

```bash
python -m pytest tests/test_phone_geometry.py tests/test_phone_photos.py tests/test_image_input.py tests/test_real_positions.py -q
```

87 tests passed, including the HEIC test enabled by `photos`. They cover
original preservation, EXIF orientation, conversion, hashes, overwrite
prevention, ambiguous labels, visual-row/orientation consistency and unreviewed
partition blocking. They also check corner order and validity, stale reviews,
and all 64 square identities through synthetic perspective rectification. HEIC skips
without the extra. The manifest test needs no local images; the auditor checks
all 161 originals and PNGs. These are data checks, not photographic recognition
measurements.
