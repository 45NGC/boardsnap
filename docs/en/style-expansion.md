# Multi-style recognition and the second style group

**English** | [Español](../es/style-expansion.md) · [Overview](README.md)

Step 9 separates model configuration from individual recognition requests. The
application supplies an image and its view; no piece-set or board-theme selection
is needed for the neural path. The engine still returns only `piecePlacement` or
a structured error. No HTTP server or Flutter client is added.

## Configure once, recognize by image and orientation

Install the existing optional ML extra, then configure an absolute model path:

```bash
python -m pip install -e '.[dev,ml]'
export BOARDSNAP_MODEL="$PWD/.cache/neural-styles-v2/best.pt"
boardsnap image.png --orientation black-bottom
```

The equivalent Python request is:

```python
from boardsnap.pipeline import recognize_image
result = recognize_image("image.png", orientation="black-bottom")
```

For a one-off model comparison, pass `--model PATH` or `model=PATH` explicitly.
The argument overrides `BOARDSNAP_MODEL`. A long-lived application can construct
`NeuralClassifier(PATH)` once and reuse its `recognize_image` method, avoiding a
weight reload per request. Model paths are configuration, not user image metadata.
There are no downloads or repository-relative automatic model searches.

An explicit `--profile` selects the existing templates for diagnostics or legacy
compatibility and ignores `BOARDSNAP_MODEL`. Passing both `--profile` and `--model`
is a usage error. With no configured model and no explicit profile, the original
brown/cburnett template default remains for existing installations. An empty,
missing or incompatible configured model **fails**; it never silently falls back
to a different classifier. PyTorch remains optional for template-only use.

Explicit orientation bypasses coordinate reading. Neural `auto` tries the known
Lichess/Chess.com coordinate layouts using local background contrast rather than
a user-selected color profile. Missing, unfamiliar or contradictory clues retain
the White-at-the-bottom convention. This is not universal OCR, especially on
textures or tiny text; explicit view is the intended application workflow.
Digital detection uses the existing structural detector with its internal palette
proposal optimization. No runtime theme lookup or annotation is used.

The optional reader got **604/648** new validation views correct with verified
bounds ([orientation report](../../data/reports/digital-styles-v2-orientation-validation.json)).
It is therefore not advertised as reliable across every new condition. Model
comparisons use explicit orientation, including on the 44 images where `auto`
would choose the wrong view; that parameter is part of the intended request.

## Fixed expansion and generalization holdouts

The [capture recipe](../../tools/capture-digital-styles-v2.json) and
[policy](../../data/manifests/digital-styles-v2.json) fix this bounded group:

| Platform | Pieces | Development backgrounds | Reserved combination |
| --- | --- | --- | --- |
| Lichess | Staunty | brown, wood4 | blue + Staunty |
| Chess.com | Alpha | green, wood | blue + Alpha |

Both piece sets are new to the previous six-set corpus. Each appears on two
backgrounds in training/validation, including a wood texture. Blue is already
present with other piece designs; the two new blue/piece pairs are never included
in training **or validation**. Only their original evaluation positions are
captured. No existing images are retroactively called unseen.

The collector produces 860 clean PNG/JSON pairs: all 80 planned positions on
development combinations, both views, plus a compact representative per source
group. Reserved pairs contribute 60 images from the 12 evaluation positions.
DOM geometry, position, orientation and rendered artwork are checked before and
after capture. Existing batches are audited before resuming.

A deterministic source subset receives the five simple-mark and four arrow
scenarios from steps 7–8, drawn on the full board before segmentation. Additional
384-pixel board-only crops and 256-pixel boards with controlled margins probe
size and layout sensitivity. These are labeled transformations, **not evidence
for a native mobile app or a different live game screen**. Every variant inherits
its position, game group and split. The loader rejects reserved pairs in either
development partition even if someone regenerates the index hash.

The controlled layout probes are clean images. Their success does not establish
every combination of small size, texture and overlay; the exact record conditions
and stratified results define the measured coverage.

The previous corpus is retained with `cohort: previous`; the new images carry
`cohort: expansion`. Independent fields record platform, pieces, background,
combination, layout and client. Evaluation reports qualify piece/background names by platform
so, for example, the two platforms' Alpha designs are not conflated.

The [corpus report](../../data/reports/digital-styles-v2.json) records 860 captured
images and 3784 controlled variants, added to 16560 previous images: **21204
boards** in total (14616 training, 3132 validation, 3456 evaluation). The 324
reserved-combination variants all remain in evaluation. Source groups and
positions still number 20 and 80; these image counts are not independent games.

## Training, regression and compatibility

The [fixed training settings](../../tools/train-styles-v2.json) run 40 epochs from
scratch on CPU. Validation selects first by complete correct boards in the entire
previous cohort, including arrows, then by overall board accuracy, macro recall
and loss. Training-only affected-cell selection and class weighting are retained;
validation and evaluation keep all 64 cells. The held-out combinations are not
used for model selection. There is no overlay removal or legality-based repair.

The run completed all 40 epochs and selected **epoch 39** using validation alone:
3131/3132 exact boards, including **2484/2484** previous-cohort controls and
647/648 new-style boards. The selected weights remain in
`.cache/neural-styles-v2/best.pt`; previous models remain available. Dataset,
index, training code and weight hashes pin the run. The merged 21204 records were
also checked against the frozen position plan, including equivalent positions
and image hashes across partitions.

The comparison scores verified-bound classification and detection-based processing
separately, with complete-image and per-class results. Breakdowns cover platform,
piece set, background, exact combination, layout, size, view, overlay and cohort;
reserved combinations have their own group. A failure stays in the denominator.
The new report must be read alongside the previous-corpus regression, not just its
aggregate average. Measured pilot evidence is not broad release compatibility.

### Recorded evaluation and known regressions

The [completed comparison](../../data/reports/neural-styles-v2-evaluation.json)
contains model hashes, training history, per-class metrics, detection failures and
all breakdowns. The weights were frozen before this run and were not adjusted
after its results. Both models saw the same 3456 images, derived from **12 source
positions in three groups**, with explicit orientation.

| Cohort | Previous model: verified / detected | New model: verified / detected |
| --- | --- | --- |
| Previous styles | 2484/2484 · 2484/2484 | 2482/2484 · 2482/2484 |
| New styles, all backgrounds | 324/972 · 324/972 | 972/972 · 968/972 |
| Reserved pairs, subset of new styles | 162/324 · 162/324 | 324/324 · 321/324 |
| Total | 2808/3456 · 2808/3456 | 3454/3456 · 3450/3456 |

The new model classified **221182/221184 squares** correctly with verified bounds.
Its two errors are regressions on previous Chess.com Neo arrow variants:
`digital-037`, white-bottom, blue, `arrow-piece`; and `digital-038`, black-bottom,
brown, `arrow-crossed`. The previous model got both correct. Clean and simple-mark
classification retained full accuracy on this corpus. The report's aggregate
`cleanPerformanceMaintained` flag does **not** mean that every previous condition
is free of regressions.

Detection found **3452/3456** boards within two pixels of their references. All
four misses are 384-pixel board-only Staunty crops viewed from Black: wood4
`digital-038`, and blue `digital-001`, `digital-006`, `digital-038`. They return
`BOARD_NOT_FOUND`; they are included as failures rather than omitted from accuracy.
The classifier got their pieces correct when given verified bounds. Both models
use the same detector, so these failures are distinct from model regressions.

The measured combination table below summarizes the 24 exact pairs. Multiple
names in one row mean every listed piece/background combination was tested.
These are **evaluated pilot results**, not a release-wide compatibility guarantee.

| Platform | Pieces | Backgrounds | Verified exact boards | Detected exact boards |
| --- | --- | --- | ---: | ---: |
| Lichess | cburnett, Merida, Alpha | brown, blue, green | 1242/1242 | 1242/1242 |
| Chess.com | Classic, Bases | brown, blue, green | 828/828 | 828/828 |
| Chess.com | Neo | green | 138/138 | 138/138 |
| Chess.com | Neo | brown | 137/138 | 137/138 |
| Chess.com | Neo | blue | 137/138 | 137/138 |
| Lichess | Staunty | brown | 162/162 | 162/162 |
| Lichess | Staunty | wood4 | 162/162 | 161/162 |
| Lichess | Staunty | blue (reserved) | 162/162 | 159/162 |
| Chess.com | Alpha | green | 162/162 | 162/162 |
| Chess.com | Alpha | wood | 162/162 | 162/162 |
| Chess.com | Alpha | blue (reserved) | 162/162 | 162/162 |

The new weights are an opt-in **candidate with known regressions**, not an
unconditional replacement for `.cache/neural-arrows-v1/best.pt`. Address the two
arrow regressions and four detection misses with development examples before
acceptance; these exposed cases are now regression evidence, not fresh blind tests.
The 34-image runtime smoke check also passed through `NeuralClassifier`, and the
configured Python API and CLI produced the exact `piecePlacement`-only contract.

The positions reused from earlier milestones are regression data. Step 10 still
requires fixed acceptance thresholds and a fresh independent acceptance corpus.
Real game screenshots need reviewed placements; native Android/iOS, untested live
interfaces, arbitrary themes and fully obscured pieces remain outside the claim.
Book diagrams are outside this digital expansion.

## Reproduce

The following paths contain local artifacts after the run; use new destinations
for a fresh build. Model/capture data stay in ignored `.cache/`.

```bash
PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright" python -m tools.collect_styles --output-root .cache/digital-style-captures-v2 --report .cache/digital-style-captures-v2-report.json
python -m tools.build_style_dataset --capture-root .cache/digital-style-captures-v2 --derived .cache/digital-style-derived-v2 --new-squares .cache/digital-style-addition-v2 --parent .cache/digital-arrow-squares-v1 --output .cache/digital-style-squares-v2 --report data/reports/digital-styles-v2.json
python -m tools.train_neural --dataset .cache/digital-style-squares-v2 --run .cache/neural-styles-v2 --config tools/train-styles-v2.json --marked-cells-only --control-cohort previous
python -m tools.evaluate_marks --dataset .cache/digital-style-squares-v2 --baseline .cache/neural-arrows-v1/best.pt --candidate .cache/neural-styles-v2/best.pt --baseline-name arrowBaseline --candidate-name styleCandidate --split evaluation --output data/reports/neural-styles-v2-evaluation.json
python -m pytest tests/test_multistyle_runtime.py tests/test_style_expansion.py
```

`collect_styles --audit-only` verifies an existing collection. Development
measurements use `--split validation`; model choices must be frozen before the
reserved comparison. Distribution and clean installation are part of step 10.

Step 10 now provides the [digital acceptance protocol](digital-release.md), a
verified local distribution and a reserved new plan. The [subsequent fixes](regression-fixes.md)
address the six known cases with a new candidate. These step 9 measurements remain
historical regression evidence; final acceptance still requires the new policy/checks.
