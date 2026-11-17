# Review of the training2 pilot

**English** | [Español](../es/targeted-photo-intake.md)

On November 12, 2026, **24 photographs and 16 direct screenshots** were received
and reviewed across eight positions. The initial pilot had 18 photos and 12
screenshots; series 7 and 8 add six photos and four references targeting the
missing white knights. All 24 photos are usable for further
preparation: the complete grid is visible, pieces and orientation match their
references, and they add perspective, moire and marks. **This batch does not
need to be retaken.** This review does not measure model accuracy.

- [Paired inventory and transcriptions](../../data/manifests/phone-targeted-intake-v1.json).
- [Coverage and gap report](../../data/reports/phone-targeted-intake-v1.json).
- [Local photo/reference gallery](../../.cache/phone-targeted-v1/review/index.html).
- Originals: `.cache/real-use-tests/training2/position1/` through `position8/`.

## Received material

| Series | Observed appearance | Background | Orientation | Frontal / oblique / marked photo |
| --- | --- | --- | --- | --- |
| 1 | `cc-thin-stem` | Plain purple | Black bottom | `IMG_5470` / `5471` / `5472` |
| 2 | `cc-thin-stem` | Plain brown | Black bottom | `IMG_5473` / `5474` / `5475` |
| 3 | `cc-shaded` | Plain brown | Black bottom | `IMG_5476` / `5477` / `5478` |
| 4 | `cc-shaded` | Wood | White bottom | `IMG_5479` / `5480` / `5481` |
| 5 | `lc-rounded-king` | Wood | White bottom | `IMG_5482` / `5483` / `5485` |
| 6 | `lc-rounded-king` | Plain brown | Black bottom | `IMG_5486` / `5487` / `5488` |
| 7 | `cc-thin-stem` | Plain purple | White bottom | `IMG_5490` / `5491` / `5492` |
| 8 | `cc-thin-stem` | Plain brown | White bottom | `IMG_5493` / `5494` / `5495` |

The gap from 5483 to 5485 is not a missing sample: that series contains three
photos. All photographs are iPhone 8 HEIC originals, 3024×4032 after file
orientation is applied. Originals were preserved; lossless RGB sRGB PNGs and
review JPEGs were generated using the existing converter. Original and derived
PNG hashes are recorded.

The first PNG screenshot in each folder corresponds to its first two photos;
the second corresponds to the marked photo. Eight placements were transcribed
visually from screenshots and compared with the photos, without model-generated
labels. The manifest stores visual rows, orientation and canonical
`piecePlacement`. Review was performed by the assistant; `userVerified` remains
`false`.

## Differences from the plan

- Series 1 and 2 both have black at the bottom. New series 7 and 8 supply
  white-bottom views for that design on both backgrounds.
- Series 3 and 4 swap the planned backgrounds and change views. Actual
  combinations are recorded without renaming or moving originals.
- The sixteen baseline photos retain **last-move highlights**. Series 6 also
  includes check. They are not labelled completely clean.
- All eight additional photos have arrows; several contain dense combinations or
  crossings. Lichess also provides circles. These are useful cases, but controlled
  comparisons with simpler marks are still missing.
- Series 1 and 8 change tilt direction between the oblique and marked photo. A change
  in recognition cannot be attributed solely to marks.
- Moire and perspective/color changes are visible. No lighting or distance
  measurements are available to quantify those factors.
- Visible appearances match selected references; official selectors remain
  unresolved because settings screenshots were not supplied. Similar artwork
  is not used to invent official theme names.
- Series 7 has overlapping vertical arrows on the f-file. Origin/destination
  pairings that cannot be resolved confidently remain pending in the manifest;
  the screenshot is the mark reference. This does not affect transcribed piece
  placement.

## Coverage and targeted expansion

Counts use **512 squares from eight distinct positions**, once per position.
Photographic variants and screenshots do not multiply that diversity.

| Appearance | Classes present | Main gap |
| --- | ---: | --- |
| Thin-stem pawns | 13/13 | White king missing on light squares |
| Shaded pieces | 13/13 | Queens/kings missing on some square colors |
| Rounded king | 13/13 | Rooks/queens/kings missing on some square colors |

All thirteen classes occur across the batch. Missing combinations per design
are listed below; uppercase denotes white pieces and lowercase black pieces:

| Appearance | Missing class and square color |
| --- | --- |
| `cc-thin-stem` | `K`: light |
| `cc-shaded` | `Q`, `K`, `q`: light; `k`: dark |
| `lc-rounded-king` | `R`, `K`, `q`: light; `Q`, `k`: dark |

`N` = knight, `B` = bishop, `R` = rook, `Q` = queen, `K` = king. Both pawn
colors and empty squares occur on light and dark squares in every group.
Presence does not establish sufficient quantity or recognition accuracy.

The expansion **fills the white-knight data gap**: positions 7 and 8 each contain
a white knight on c3 (dark) and f3 (light). These provide two examples per square
color, counted by position, across both backgrounds. They also fill the earlier
bishop and queen gaps for this appearance. All thirteen classes now occur in
every appearance; recognition accuracy still requires measurement.

No additional collection is needed to complete this expansion. Geometry for all
24 photos was reviewed on November 13, 2026 (see below). Future expansion can address the table's gaps,
genuinely unmarked baselines and simple-mark pairs at similar framing. The report
retains a summary of the first six positions to show what the new samples add;
their existing image and session records were preserved.

## Provenance and preparation status

Six distinct Chess.com games were read from the photographs:
`186750194058`, `186559752718`, `187062563830`, `187014017568`,
`186984581962` and `186840071668`.
The user confirmed that Lichess series 5 and 6 come from different games; their
identifiers are not visible. Each game has its own group, keeping every photo
and reference together.

No duplicate original files or position-family overlap was found against the
191 previously registered photographs. The six Chess.com identifiers do not
match known identifiers in that batch either. This check is limited to previous
photographic manifests: incomplete provenance and other corpora still require
review before training assignment. It does not establish independent final
evaluation data.

The **paired intake and geometry reviews are complete**. On November 13, 2026,
the four corners of every photo were annotated and all 24 rectified boards were
visually checked against the original photograph, direct reference and label
diagram. The existing detector supplied proposals; each was inspected before
approval. No manual corner adjustment was needed. This is assistant visual
review, not an independent detector benchmark or subpixel ground truth.

Corners use full-resolution, EXIF-normalized RGB image coordinates, in
**top-left, top-right, bottom-right, bottom-left** order. They describe the
photographed view independently of chess orientation. All eight rows and columns
remain visible and aligned; no clipped pieces or misplaced labels were observed.
Moire, arrows, highlights and color variation remain in the pixels.

## Prepared squares

- [Geometry and labeled-square gallery](../../.cache/phone-targeted-squares-v1/index.html).
- [Export report](../../data/reports/phone-targeted-squares-v1.json).
- Local arrays: `.cache/phone-targeted-squares-v1/development/*.npz`.
- Local index: `.cache/phone-targeted-squares-v1/verified.jsonl`.

There are **1,536 RGB crops of 64×64 pixels**, 64 from each of 24 photos,
covering all 13 classes. Each board is rectified to 512×512 with OpenCV linear
interpolation. Cells follow a8..h1; black-bottom views reorder whole cells without
rotating piece glyphs. The 16 screenshots remain references and are not silently
added as training boards. Eight positions and eight source groups remain intact.
No balancing or random square-level split is applied.

The export records photo/reference hashes, corners, labels, orientation, source,
group, conditions and array checksums. A visual-review fingerprint invalidates
approval when geometry, pairing, labels or grouping change. Changed source bytes,
missing reviews and inconsistent session membership prevent publication. The
export is atomic and refuses to overwrite an existing destination.

Reproduce into a new output directory (local source images are required):

```bash
python -m tools.build_targeted_photo_squares --output .cache/phone-targeted-squares-rebuild
```

Run the preparation checks:

```bash
python -m pytest tests/test_targeted_photo_squares.py tests/test_phone_squares.py tests/test_phone_geometry.py -q
```

The crops are ready for training-data assembly and remain **development** with
`readyForTraining: false`: this export does not itself assign training membership.
The overlap check below is now complete, with residual provenance uncertainty.
Existing partitions and models are unchanged. No training or final evaluation
was run; this task does not establish recognition accuracy or new compatibility.

## Overlap check against existing validation — November 13, 2026

[Detailed reproducible report](../../data/reports/phone-targeted-overlap-v1.json).
The 24 photos and 16 paired references were compared with the **30 existing
validation photographs**. Original bytes, normalized files and decoded RGB
pixels were checked. All eight placements were compared canonically and through
the existing conservative family check (rotations, reflections and color swaps).
Known source IDs were compared with platform identity retained.

| Check | Result |
| --- | --- |
| Duplicate originals, normalized files or pixels vs photo validation | 0 |
| Equal positions or position families vs photo validation | 0 |
| Shared known game/video IDs vs photo validation | 0 |
| Position-family matches vs 12 generated digital validation positions | 0 |
| Position-family or known-source matches vs 161 previous development photos | 0 |

The nearest photo-validation placements differ on **16–31 squares**, depending
on the new position. This is a rough similarity check, not proof of unrelated
games or a legal-move distance. The development comparison uses existing
annotations; only the targeted and photo-validation image bytes were rechecked.

Six new Chess.com game IDs differ from the five known validation game IDs
(10 photos). New Lichess series 5/6 have no game IDs, and **20 validation photos**
have no verified game/video IDs. Their provenance cannot be fully compared.
The user's confirmation establishes that series 5 and 6 are different from each
other; it does not establish separation from every older source.

**Decision:** no observed conflict requires removing a photo. Keep each new
source group intact when assembling the next training plan, record the remaining
provenance uncertainty, and leave validation outside training. Shared piece
styles/backgrounds are desirable here; the prohibited overlap is the same
example, its variants or related source material across the split. This reused
validation supports development, not an independent release acceptance claim.
No model was run and no reserved final evaluation was accessed.

Reproduce the check (requires local images):

```bash
python -m tools.audit_targeted_photo_overlap
python -m pytest tests/test_targeted_photo_overlap.py -q
```

## Subsequent training

The reviewed crops were subsequently assigned to training in a separate frozen plan.
See the [completed training and comparison](targeted-photo-training.md). The
original intake/export stays development data; its reviews and hashes are preserved.
