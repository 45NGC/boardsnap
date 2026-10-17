# Digital regression fixes

**English** | [Español](../es/regression-fixes.md) · [Overview](README.md)

The [six original failures](../../data/reports/digital-regressions-v8.json) pass
with `.cache/neural-styles-v8/best.pt` and the updated detector. The three Staunty
cases that regressed during development also [pass](../../data/reports/digital-staunty-regressions-v8.json).
This is regression evidence, **not final digital acceptance**. The reserved
acceptance source plan has not been captured, trained on or evaluated here.

Subsequent user screenshots exposed two additional failing images, now registered
as [video development cases](video-development.md). The results below describe the
original correction, not compatibility with those newly inspected video conditions.

The full-frame fallback described below is historical. The later
[visible-boundary refinement](video-development.md#step-3-visible-boundary-refinement)
requires interior-line and perimeter evidence before accepting a frame-based
proposal, fixing video 002 while preserving the six original cases.

The [complete regression report](../../data/reports/neural-styles-v8-regression.json)
measures **3456/3456 images correct**, with both verified and detected bounds:
221184/221184 squares, zero new recognition failures, and all detected rectangles
within two pixels of their annotations. These are variants of **12 source
positions**, not 3456 independent positions. All 2484 previous-cohort variants and
972 expansion variants pass, including 324 reserved-combination variants.
The [CLI check](../../data/reports/digital-cli-v8-regression.json) also passes all
six original cases with exact JSON, exit code 0 and empty stderr.

Automated tests: **1373 passed, 36 skipped, 2 expected failures**. Skips are optional
browser tests; expected failures belong to the experimental book-diagram baseline.

## Detection

All four failures were complete 384-pixel Staunty boards cropped to the image
boundary, viewed from Black: wood4/digital-038 and blue/digital-001, 006 and 038.
Repeated piece bases shifted the interior edge fit outside the image, causing
the candidate bounds to be discarded despite a valid alternating grid.

When no fitted grid passes, a nearly square complete image is now considered as
another proposal. It must still pass alternating-cell and sustained grid-boundary
checks. Fitted grids take priority so that small margins do not produce duplicate
boards. All four cases now have **zero boundary error**. Tests retain negative
controls, wrong grid sizes, incomplete boards and multiple-board rejection.

The [separate detection regression](../../data/reports/digital-detection-v2-regression.json)
also retains all 28 reviewed real/synthetic rectangles and rejects their 28
board-removal negatives. This does not establish classification of real screenshots.

## Recognition and training data

The Neo failures confused a White pawn with a Black pawn under a blue arrowhead
and a White king with a White knight under crossed arrows. Both now produce the
exact expected placement. Runtime still loads one small 13-class model; it does
not erase arrows or use position-specific corrections.

Weight adjustments alone did not preserve all styles. The final correction adds
[1144 training-only variants](../../data/reports/arrowhead-training-v1.json):
one blue arrowhead example per class, square color, orientation and seen style
combination (13 × 2 × 2 × 22). Sources come exclusively from the original 14
training groups. Arrows are rendered on full boards before normalization and
cropping. Their direction varies deterministically, with width 0.22 squares and
RGBA `[45, 110, 220, 192]`. No exposed regression image was copied into training.

The extra dataset contributes 6437 affected training squares, for **320783** total.
Source hashes, position/group, placement, view and style must match original
training records. Relabeled reserved images are rejected. Validation and regression
distributions remain unchanged; the two reserved piece/background combinations
stay outside training and validation.

The [training record](../../data/reports/neural-styles-v8-training.json) selects
epoch 12 of 12 using validation only: **3131/3132** complete positions, including
**2484/2484** previous-cohort controls. One validation failure remains. Known
failures informed development between runs; the consulted regression set is not
an independent final test.

| Run | Method | Outcome on exposed cases |
| --- | --- | --- |
| v3 | Supervised fine-tuning of styles-v2 | Both original arrow failures remained |
| v4 | Preserve arrows-v1 training predictions, temperature 2 | King failure remained |
| v5 | Continue v4, teacher temperature 4 | Six original cases passed, but three new Staunty failures |
| v6 | Average v2/v5 parameters, fraction selected on validation | Staunty recovered; original pawn failed |
| v7 | Previous-cohort and expansion-cohort training teachers | Original pawn still failed |
| v8 | Supervised fine-tuning of v7 with balanced blue-arrowhead variants | Six original cases and three Staunty cases pass |

Artifacts record source models, datasets, configuration and code hashes. Tests
check deterministic resume, reject changes to initialization/teachers/masks, and
prevent extra training variants from crossing source partitions. Teachers and
parameter averaging are training tools; inference requires only the v8 weights.

## Use and reproduce

Weights are local and ignored by Git. Earlier models and the v1 preview bundle
remain unchanged. Select the corrected model explicitly:

```bash
export BOARDSNAP_MODEL="$PWD/.cache/neural-styles-v8/best.pt"
boardsnap image.png --orientation white-bottom
```

Model SHA-256: `9546c6cfc34517f631cd58bf3eae0cdb3aa7790765b6f4ad1c0bf307ca4ad704`.
Success still returns only `piecePlacement`; error JSON and exit codes are unchanged.

From the repository root with the existing environment, parent corpus and models:

```bash
python -m tools.build_arrowhead_training --parent .cache/digital-style-squares-v2 --captures .cache/arrowhead-training-captures-v1 --output .cache/arrowhead-training-squares-v1 --report data/reports/arrowhead-training-v1.json
python -m tools.train_neural --dataset .cache/digital-style-squares-v2 --extra-training-dataset .cache/arrowhead-training-squares-v1 --run .cache/neural-styles-v8 --config tools/train-styles-v8.json --marked-cells-only --control-cohort previous --initialize-from .cache/neural-styles-v7/best.pt
python -m tools.check_known_regressions --dataset .cache/digital-style-squares-v2 --model .cache/neural-styles-v8/best.pt --previous-report data/reports/neural-styles-v2-evaluation.json --output data/reports/digital-regressions-v8.json
python -m tools.evaluate_marks --dataset .cache/digital-style-squares-v2 --baseline .cache/neural-arrows-v1/best.pt --candidate .cache/neural-styles-v8/best.pt --baseline-name arrowBaseline --candidate-name styleCandidate --split evaluation --regression --output data/reports/neural-styles-v8-regression.json
python -m pytest
```

These creation commands require new output directories. To resume an interrupted
training run, add `--resume` with identical inputs. Rechecking existing models
does not require regenerating the corpus or retraining. The parent model chain is:

```bash
python -m tools.train_neural --dataset .cache/digital-style-squares-v2 --run .cache/neural-styles-v4 --config tools/train-styles-v4.json --marked-cells-only --control-cohort previous --initialize-from .cache/neural-styles-v2/best.pt --teacher .cache/neural-arrows-v1/best.pt
python -m tools.train_neural --dataset .cache/digital-style-squares-v2 --run .cache/neural-styles-v5 --config tools/train-styles-v5.json --marked-cells-only --control-cohort previous --initialize-from .cache/neural-styles-v4/best.pt --teacher .cache/neural-arrows-v1/best.pt
python -m tools.average_neural --dataset .cache/digital-style-squares-v2 --left .cache/neural-styles-v2/best.pt --right .cache/neural-styles-v5/best.pt --run .cache/neural-styles-v6
python -m tools.train_neural --dataset .cache/digital-style-squares-v2 --run .cache/neural-styles-v7 --config tools/train-styles-v7.json --marked-cells-only --control-cohort previous --initialize-from .cache/neural-styles-v6/best.pt --teacher .cache/neural-arrows-v1/best.pt --expansion-teacher .cache/neural-styles-v2/best.pt
```

The [v1 acceptance policy](digital-release.md) pins the old runtime and model;
it remains historical evidence. Completing step 10 still requires new candidate,
CPU, distribution and frozen-policy checks before the guarded final evaluation.
