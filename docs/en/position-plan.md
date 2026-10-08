# Position plan and fixed dataset partitions

**English** | [Español](../es/position-plan.md) · [Overview](README.md)

The [digital-positions-v1 manifest](../../data/manifests/digital-positions-v1.json)
contains **80 distinct canonical placements from 20 source sequences**, partitioned
before screenshots or square crops. The [coverage report](../../data/reports/digital-positions-v1-coverage.json)
measures label coverage, not recognition accuracy. No new screenshots, templates,
trained models or runtime profiles are introduced in this milestone.

## What is in the batch

| Partition | Source groups | Distinct positions | Purpose |
| --- | ---: | ---: | --- |
| `training` | 14 | 56 | Learn model parameters; build templates and develop preprocessing |
| `validation` | 3 | 12 | Select thresholds, hyperparameters and compare models |
| `evaluation` | 3 | 12 | Final measurement after implementation and choices are frozen |
| Total | 20 | 80 | Initial collection plan, not a precision guarantee |

Each sequence contributes four different snapshots: one opening, one middlegame,
one sparse endgame and one immediately after a promotion. Categories may overlap
with density tags. Every partition contains all twelve piece/color classes and
empty squares on both logical square colors, and promotions by both White and Black.

| Category | Training | Validation | Evaluation | Selection rule |
| --- | ---: | ---: | ---: | --- |
| Opening | 14 | 3 | 3 | After 12 plies, at least 28 occupied squares |
| Middlegame | 14 | 3 | 3 | At least 32 plies, 12–26 occupied squares |
| Endgame | 14 | 3 | 3 | 3–10 occupied squares; selected separately from the promotion snapshot |
| Promotion | 14 | 3 | 3 | Immediately after a legal promotion, including underpromotions in the batch |
| Dense | 14 | 3 | 4 | At least 28 occupied squares |
| Sparse | 18 | 4 | 4 | At most 10 occupied squares |

Phase names are sampling heuristics, not expert annotations of game strategy.
The extra dense/sparse counts overlap other rows; do not add all category counts
to estimate corpus size. Square colors mean chessboard parity: a8 is light and
a1 is dark. Actual image themes and overlays remain to be captured.

## Reproducible sources and limitations

These are **synthetic legal move sequences**, generated from the standard start,
not downloaded human games and not invented recognition results. A seeded
weighted choice among legal moves favors captures and pawn advances to obtain
endgames and promotions. It does not play strong or representative chess.
Sequences stop once the four required snapshots are available; they are not
necessarily completed games.

Each source stores its seed, standard-start marker and UCI moves. Each position
stores its source group and ply number. The optional replay check reconstructs
every move, checks legality and compares the selected board with the stored
`piecePlacement`. Chess rules are used only by dataset tooling, never to correct
the recognizer's output. Full FEN state is not added to image labels or app output.

There are **20 groups, not 80 independent games**. Validation and evaluation each
contain only three groups. More themes and two orientations create more images,
not more independent positions or groups. This first batch is useful for capture
and model experiments, but needs independent real-world captures and more source
groups before broad compatibility claims.

The generator uses [python-chess legal moves and board representation](https://python-chess.readthedocs.io/en/latest/core.html)
through the pinned optional dependency `chess==1.11.2`. It adds no dependency to
the recognition core and does not introduce PyTorch. The committed UCI records
are the primary source evidence even if a future Python random implementation
changes reproduction behavior.

## How the split is fixed

1. Generate eligible sequences with seeds beginning at `20261007`; reject
   incomplete sequences, repeated/transformed snapshots and overlap with the
   existing corpus. Keep the first twenty eligible sources.
2. Stratify whole groups using partition seed `1729`. Select the first shuffled
   14/3/3 allocation having at least **two square occurrences of each class on each
   background in each partition**, plus promotions by both colors. This uses
   ground-truth labels only, before images and recognition experiments.
3. Commit the resulting group assignments. Never shuffle images or square crops
   into their own partitions. Reproduction checks compare the complete manifest.
4. Freeze the plan before capture. The preparation command refuses to overwrite
   an existing file; use a new output path to check reproduction. A changed plan
   requires a new dataset version and a reviewed migration, not silent replacement.

Every group has its split in exactly one place, `groups[].split`. A position has
`positionId`, `groupId`, `ply`, `piecePlacement` and `categories`; it cannot
override the group's split. All themes, apps, orientations, arrows, highlights,
resizes, compression variants and square crops inherit this identity.

Future import of human games needs a stable canonical game/source identifier,
deduplication across downloads and the same group rule. Closely related positions
from a game must not be split between training and evaluation. The current schema
validates generated sequences only; it does not pretend to be a PGN importer.

## Preserve the previous corpus

The four existing profile manifests (including the book experiment) are pinned
by path and SHA-256 in `legacyExclusions`. Their current files, images and splits
remain unchanged. The new plan excludes all their placements, rotations,
reflections and color-swapped equivalents. This is deliberately conservative.

Existing `tuning` data remain development data. If reused for learned models,
use them only as additional training data; do not relabel them as independent
validation or final evaluation. Existing `evaluation` fixtures remain regression
holdouts and must not be copied into training. The new `evaluation` groups are
separate from those small, repeatedly checked pilot positions. Update the
exclusion policy explicitly if another corpus is introduced.

## Coverage and remaining gaps

The report contains occurrence counts, distinct position counts and distinct
source-group counts for every class/background in every partition. Repeating the
same piece in four related snapshots is not four independent sources. Its manifest
SHA-256 makes the report traceable to the exact frozen plan.

Eight combinations are flagged because they have fewer than five square
occurrences or fewer than three source groups:

| Partition | Class / square color | Squares | Positions | Groups |
| --- | --- | ---: | ---: | ---: |
| Validation | White queen / dark | 2 | 2 | 2 |
| Validation | White king / light | 3 | 3 | 2 |
| Validation | Black queen / light | 2 | 2 | 1 |
| Evaluation | White queen / dark | 2 | 2 | 2 |
| Evaluation | White king / light | 4 | 4 | 2 |
| Evaluation | Black queen / light | 3 | 3 | 2 |
| Evaluation | Black queen / dark | 4 | 4 | 2 |
| Evaluation | Black king / dark | 3 | 3 | 2 |

Training has all 26 class/background combinations with at least five occurrences
and three source groups. That is a coverage check, not a sufficient sample-size
claim. Neither two nor five is an accuracy threshold. Prioritize new independent
groups for the sparse combinations when extending the plan.

Do not move existing groups across partitions to fix gaps after development has
started. If a final-evaluation failure is used to guide tuning, retire that whole
source group into development and obtain fresh, independent evaluation sources
in a new version. Never retain its other themes/views in evaluation.

## Commands

From the repository root, after installing the normal development dependencies:

```bash
# Structural checks, legacy isolation and coverage; standard library only.
python -m tools.position_dataset

# Additional optional dependency, only for generation and legal replay.
python -m pip install -e '.[dev,dataset]'
python -m tools.position_dataset --replay

# Reproduce into a NEW path; compare against the committed frozen plan.
python -m tools.prepare_positions .cache/positions-reproduced.json
cmp data/manifests/digital-positions-v1.json .cache/positions-reproduced.json

# Save a local report without replacing the committed evidence.
python -m tools.position_dataset --replay > .cache/positions-coverage.json
python -m pytest tests/test_position_dataset.py
```

The validation tool emits JSON to stdout and errors to stderr (exit 2). The JSON
is a **dataset report**, separate from BoardSnap's single-`piecePlacement` runtime
response. Without `.[dataset]`, structural tests still run; only the legal
replay/reproduction test is skipped. The test suite checks leaks, bad labels,
parity, missing classes, variant identity, frozen report and reproducibility.

## Next: capture from this plan

The old capture tools accept `tuning/evaluation` profile manifests. They do **not**
yet accept this profile-independent three-partition schema. Do not flatten
validation into tuning or feed the new manifest to the old capture command.

The next capture adapter should validate the complete plan once, then call:

```python
from tools.position_dataset import variant_identity, validate_variants

identity = variant_identity(manifest, "digital-001")
annotation = {
    **identity,
    "orientation": "black-bottom",
    "boardStyleId": "lichess-brown",
    "pieceStyleId": "lichess-cburnett",
    "layoutId": "LC01",
    "conditions": ["K01"],
}
validate_variants(manifest, [annotation])
```

This example assembles annotation metadata; it neither renders nor recognizes an
image. Add image path/hash, capture provenance and independently checked bounds
at capture time. Keep the dataset ID in output paths to separate the new batch
from legacy fixtures; a proposed layout is
`data/datasets/digital-positions-v1/<split>/<profile>/<position>-<variant>.png`.

Start with the three existing clean desktop combinations from the
[style inventory](style-inventory.md). Capture both orientations, check rendered
pieces and bounds, preserve source notices, and verify every saved annotation
against the manifest before producing any square crops. Training and template
builders must read only training; model selection reads validation; final
evaluation is reserved until all choices are frozen.

