# Screen photograph corpus

**English** | [Español](../es/phone-photo-corpus.md)

## Status — 22 October 2026

The **90 photographs are enough to start the geometry pilot**. They are not yet
a training-ready dataset or evidence of photographic recognition support. This
review ran no recognition or training; models and production input are unchanged.

| Source according to directory | Photos | Enlarged reviews | Transcribed placements |
| --- | ---: | ---: | ---: |
| Chess.com | 30 | 6 | 6 |
| Lichess | 30 | 6 | 6 |
| Videos | 30 | 6 | 5 |
| Total | 90 | 18 | 17 |

All 90 were inspected in contact sheets, with 18 enlarged reviews. The **other
72 have pending labels**, not predictions. `IMG_5205.HEIC` shows a black queen
mid-animation, with multiple silhouettes between squares. It remains ambiguous
without an expected placement. To replace it, pause the video and wait for the
move animation to finish before photographing.

All HEICs decode, with no exact file duplicates. EXIF identifies an **iPhone 8**
for all 90. No direct reference screenshots, FENs or PGNs were supplied.
Originals are preserved unchanged.

## Files and commands

- Originals: `.cache/real-use-tests/phone-photos/`.
- Copies and contact sheets: `.cache/phone-photos-v1/`.
- Open `.cache/phone-photos-v1/index.html` in a browser to map each original
  filename to its full-size PNG.
- [Inventory and annotations](../../data/manifests/phone-photos-v1.json).
- [Integrity and coverage report](../../data/reports/phone-photos-intake-v1.json).

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

| Directory | Files reviewed in detail |
| --- | --- |
| `chesscom-photos` | `IMG_5228`, `IMG_5234`, `IMG_5238`, `IMG_5246`, `IMG_5248`, `IMG_5257` |
| `lichess-photos` | `IMG_5258`, `IMG_5264`, `IMG_5267`, `IMG_5276`, `IMG_5283`, `IMG_5289` |
| `video-photos` | `IMG_5195`, `IMG_5197`, `IMG_5205` (ambiguous), `IMG_5214`, `IMG_5220`, `IMG_5223` |

The 17 placements cover 1088 squares and all 13 classes on both canonical square
colors. This does not establish readability or model accuracy. There are only
two black queens on light squares and three white kings on light squares in
this subset: it is not balanced. Several photos belong to related sequences,
so these are not independent example counts.

Four-corner annotations remain pending (`boardCorners: null`). Annotate them
on full-size PNGs for rectification studies instead of substituting approximate
rectangles. Rendering a board from a FEN could help review pieces, but would
not supply an original screenshot.

## Groups and partitions

**90 development, 0 training, 0 validation and 0 final evaluation.**
This is a safe provisional state, not a completed training split.

Related game sequences and a shared video context are visible. Provenance has
not been systematically recorded. Different positions or directories cannot be
assumed independent. The batch shares `phone-photos-unresolved-origin-v1`;
the auditor rejects moving isolated records to other partitions. Trainers must
not consume this intake format.

Before training, identify games/videos, join variants, check overlap with
previous corpora and freeze a new partition version. The initial position in
`IMG_5197` is already-known content. No reserved final evaluation data was
consulted for this inventory.

If provenance cannot be recovered, this batch can remain development material.
Validation will need new identified game series separated from collection
onward. Independent final evaluation will be collected later, after freezing
the candidate and criteria.

## What to add

Do not reach 200 merely by repeating these conditions. Perspective, rotation,
different distances, openings, middlegames, endgames, both orientations,
highlights and some arrows are already represented. Screen interference
patterns (*moire*) and color bands are visible. Brown backgrounds, few designs
and a similar monitor environment predominate; exact theme names are unconfirmed.

After the pilot, prioritize **20–30 further photos**, if expansion is needed,
from several new, identified games or videos:

1. Other backgrounds and piece sets, without changing every factor at once.
2. Other angles, distances and lighting; another monitor or phone if available.
3. Variants of a position with a clear frontal photograph and a direct computer
   screenshot when possible. Retain links and timestamps; placement can be
   transcribed later. Pause animations and retain the complete board.
4. Some photographs without boards or with clipped boards, explicitly labeled
   negative controls and separate from full-placement images.

These quantities target gaps rather than guarantee accuracy. Closing phase 5
still requires the other 72 labels, recovering or replacing references where
ambiguous, and separating verified sources. The pilot already supports corner
annotation and rectification studies without training on doubtful labels.

## Checks

```bash
python -m pytest tests/test_phone_photos.py tests/test_image_input.py tests/test_real_positions.py -q
```

63 tests passed, including the HEIC test enabled by `photos`. They cover
original preservation, EXIF orientation, conversion, hashes, overwrite
prevention, pending labels and unreviewed partition blocking. HEIC skips
without the extra. The manifest test needs no local images; the auditor checks
all 90 originals and PNGs. These are data checks, not photographic recognition
measurements.
