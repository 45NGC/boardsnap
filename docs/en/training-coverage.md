# Existing training coverage inventory

**English** | [Español](../es/training-coverage.md)

Reviewed November 14, 2026. **Existing data are sufficient to prepare the next
mixed training dataset; more photos are not required yet.** Keep `neural-phone-v1`
as the recommended model. This inventory performs no training and demonstrates
no recognition improvement.

- [Counts, examples and input hashes](../../data/reports/training-coverage-v1.json).
- [Local training gallery](../../.cache/training-coverage-v1/index.html).
- [Old photo background review](../../data/manifests/phone-training-backgrounds-v1.json).
- [Regression diagnosis](targeted-photo-regressions.md).

## Available sources without counting their ancestors again

| Source under `.cache` | Training boards | Positions | Stored squares | Existing selector squares |
| --- | ---: | ---: | ---: | ---: |
| `digital-style-squares-v2` | 14,616 | 56 | 935,424 | 314,346 |
| `arrowhead-training-squares-v1` | 1,144 | 56 | 73,216 | 6,437 |
| `phone-targeted-training-v1` | 184 | 161 | 11,776 | 11,776 |

The main digital source already includes previous digital corpora. Its variants
share 56 positions and 14 groups, as does the supplementary arrow source; they
are not thousands of independent situations. There are 22 digital piece/background
combinations. Photos comprise 160 old images (153 placements) and 24 new images
(eight placements). Old photos keep their unresolved conservative source group;
new photos keep their eight groups.

The final column calculates existing `training_indices`: complete clean boards,
and selected marked cells with existing safety halos. It does not apply a new
sampling policy or mutate data. All 15,944 training archive checksums were verified.
No duplicate archive hashes were found across the inventoried rows, but individual
squares can still repeat identical pixels across variants.

## Reusable arrows and simple marks

Main digital corpus, measured per canonical square:

| Cell condition | Empty | Occupied |
| --- | ---: | ---: |
| Arrow touched | 26,466 | 9,607 |
| Arrow tip | 4,388 | 1,772 |
| Arrow start | 4,463 | 1,697 |
| Arrow crossing | 918 | 314 |
| Arrow and another mark | 1,478 | 986 |
| Circle | 1,729 | 6,895 |
| Last move | 1,816 | 3,112 |
| Selection | 179 | 1,053 |
| Move dots | 1,029 | 6,363 |

Categories overlap and must not be added. Arrow coverage uses geometric masks;
crossings require overlapping pixels, not simply two arrows on one board. Tip/start
mean endpoint cells. These are controlled digital overlays, not proof of coverage
of all native platform marks.

Tips, starts, circles, selections and combinations cover all 13 classes on both
square colors. Crossings lack white rooks on either color, white kings on light
and black queens on light. Check highlights cover kings only, appropriately;
missing classes do not automatically justify incoherent synthetic examples.

All 11,088 marked boards in the main source have matching training clean controls;
there are 3,528 clean boards. The additional 1,144 arrow variants contain 88 tips on
empty cells and 1,056 on occupied cells, covering all 13 classes on both colors.
Their clean controls are in the main source, matched by source-image checksum.
This material can protect real pieces under marks as well as suppress false pieces.

## Photos: wood and thin pieces

Visual review of all 160 old training boards identifies visible wood grain in
`lichess-photo-40` through `lichess-photo-44`. Wood grain is distinguished from
screen moire. The other 155 are labeled “no visible wood grain”; this does not mean
clean, texture-free, or free of photographic artifacts.

Including six new wood photos gives **11 photos, seven positions, 704 squares**:
**404 empty (209 light, 195 dark)** and 300 occupied. Missing pairs are white queen
on dark, white king on light and black knight on light. The three recorded groups
do not prove three identified games: one is the unresolved old-source bucket.

New photographs:

| Observed appearance | Photos / positions | Empty squares | Occupied squares |
| --- | ---: | ---: | ---: |
| Thin-stem pawns (`cc-thin-stem`) | 12 / 4 | 444 | 324 |
| Shaded pieces (`cc-shaded`) | 6 / 2 | 210 | 174 |
| Rounded crown (`lc-rounded-king`) | 6 / 2 | 213 | 171 |

Thin-stem examples include all 13 classes but lack white kings on light squares.
The other two appearances have additional class/color gaps listed in the report.
These are visual labels, not newly confirmed official themes. The previous piece
style audit remains valid; old piece themes were not all identified again.

**Photo marks are only annotated per image.** The 404 empty wood cells cannot be
called 404 unmarked cells, and images tagged as containing arrows cannot give an
exact number of empty cells with arrowheads. Some old photos lack detailed condition
annotations. Unknown conditions remain unknown, not “clean.” Traceable examples
in the gallery show their labels and source positions.

## Decision and next step

1. Reuse digital clean controls, simple marks, tips, starts, crossings and occupied
   cells instead of repeating a photo-only fine-tune that lost overlay tolerance.
2. Retain old photos and all 24 targeted additions, giving controlled representation
   to wood and thin pieces without blindly multiplying their few positions.
3. Prepare mixed sampling by source and condition. Even with the existing selector,
   320,783 digital cells versus 11,776 photo cells would dominate a naive concatenation.
4. Before assembly, check groups, placement families and duplicate identities across
   sources and against existing validation. This inventory is not that leakage audit
   and does not authorize moving validation failures into training.
5. Freeze the recipe and acceptance criteria before one new candidate. Request more
   data only if validation demonstrates a relevant remaining coverage gap.

All models, original labels and partitions remain unchanged. No inference or
validation/final image reads occurred. The shared digital index is filtered by
split before inspecting reserved annotations. Five focused tests cover partition
exclusion, index integrity, mark geometry, unknown conditions and counting.

```bash
python -m tools.inventory_training_coverage --gallery .cache/training-coverage-v1
python -m pytest tests/test_training_coverage_inventory.py -q
```

The [mixed training preparation](mixed-training.md) fixes 50% digital / 50% photographic sampling, checks overlap against existing validation and exports reproducible crops without training a model.
