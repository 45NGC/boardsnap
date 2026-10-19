# Classifier tolerance to crop errors

[Español](../es/classifier-tolerance.md)

This development step measures the classifier independently of detection. The
reviewed rectangle is the control; changing it deliberately tests what happens
when a detector is slightly wrong. It does not change the production detector,
normalization, orientation, JSON contract or default model selection. v8 remains
available unchanged. Chess.com videos 009/010 are deferred known limitations,
not targets of this experiment.

## Fixed measurement

`tools.evaluate_tolerance` uses all 3132 validation images (12 source positions)
of `digital-style-squares-v2`, keeping clean images, simple marks and arrows
separate. For each source it measures these 14 cases:

- The reviewed rectangle with normal production preprocessing.
- Horizontal and vertical translations of -1, +1, -2 and +2 input-image pixels.
- Inward and outward changes of two pixels on every edge.
- Asymmetric edge changes of `(1, -2, 2, -1)` pixels, in left/top/right/bottom order.
- Whole-board resizing to 85% with bilinear or 115% with bicubic resampling,
  followed by the usual whole-board LANCZOS normalization and square extraction.

These are image-pixel offsets: the same error is proportionally larger on a
smaller board. Variants are generated before splitting into squares; Black's
view reverses cell order without rotating the pieces. An out-of-image crop is
reported as inapplicable, never padded or silently clipped. The `applicable` and per-case metrics exclude inapplicable crops. The `all`
confusion matrix also records them in its last column as processing errors;
report their count separately when interpreting classifier accuracy.

The report includes each scenario's confusion matrix, class precision/recall,
exact boards, overlay cases, and working controls lost under perturbation.
When comparing two models it also lists paired losses and gains, so equal totals
cannot conceal a regression on previously working images. Source data, model and
code hashes make the comparison auditable. These are validation measurements,
not an independent final evaluation.

## Training and selection

`tools.train_tolerance` starts from v8 and retains its original training examples,
including the previously audited arrowhead additions. It chooses approximately a quarter
of training source paths by hash and adds one whole-board perturbation per selected
source, with all 64 labels. Scenario selection is deterministic and independent
of the expected pieces or model mistakes. Only transformations that stay within
the screenshot are applicable. Each added board records its source hash, position,
group, split, orientation, transformation and resulting bounds.

Original validation arrays and frequencies are unchanged. A separate, fixed
challenge block adds one applicable transformation per validation board for model
selection. Neither validation block enters training; evaluation arrays remain
unopened during training and selection. Existing split/group checks also protect the reserved combinations.
The prepared arrays are disk-backed to limit RAM pressure, and cached arrays are
hashed before reuse.

The configuration freezes the seed, eight epochs and optimizer settings. Training
uses class weights from training labels only. Distillation from v8 applies only
to original training examples, while the new crops use their verified labels.
Epoch selection prioritizes exact original validation boards, then all validation
boards, macro recall and loss. Epoch checkpoints support `--resume` with the same
inputs/configuration. A completed training run alone is not grounds to switch models.

A second selection compares fixed parameter averages of v8 and the trained
model (trained fractions 0, 0.0625, 0.125, 0.25, 0.5, 0.75 and 1). It rejects any fraction that
loses an originally correct validation board or reduces the original correct-square
total. Among the remaining fractions it applies the same validation ranking. The
result is one ordinary network, with no ensemble or additional inference cost.
The unmodified v8 endpoint remains a fallback if none improves tolerance.

The criterion for recommending a candidate is no loss of previously correct
unperturbed validation boards, improved exact-board tolerance, no aggregate
board/square regression within each overlay case, and preservation of the working
development and consulted regression cases. The independent final set is reserved
for the later acceptance step.

## Validation selection

The [frozen selection](../../data/reports/neural-tolerance-candidate.json) chooses
`.cache/neural-tolerance-v1-conservative/best.pt`: 87.5% v8 parameters plus 12.5%
of epoch 7 of the first training run. All 3131 originally correct validation
boards remain correct; the fixed challenge block improves from 2855 to 2906
exact boards out of 3132. These are selection results, not final acceptance.

The unrestricted trained model lost an original correct board and was rejected.
A second run with a lower learning rate and stronger distillation was also
completed, using the same data. Its best eligible average reached 2897 challenge
boards and was not chosen. The reports retain the
[first training](../../data/reports/neural-tolerance-v1-training.json),
[coarse selection](../../data/reports/neural-tolerance-v1-selection.json),
[conservative selection](../../data/reports/neural-tolerance-v1-conservative-selection.json),
[second training](../../data/reports/neural-tolerance-v2-training.json) and
[second selection](../../data/reports/neural-tolerance-v2-selection.json).
All choices used validation before running the consulted regressions.

## Completed verification

The [analysis of the 11 losses](tolerance-regressions.md) identifies a local
white-bishop/queen confusion and recommends retaining this candidate after rejecting
a mixture closer to v8 that sacrificed 400 newly correct boards.

The [full validation comparison](../../data/reports/neural-tolerance-validation.json)
passes the documented development gate. Counts below are exact whole boards;
perturbed variants are correlated views of the same 12 positions, not independent
new positions.

| Measurement | v8 | Selected candidate |
| --- | ---: | ---: |
| Original validation rectangles | 3131 / 3132 | 3131 / 3132 |
| All applicable perturbed variants | 36955 / 40236 (91.85%) | 37618 / 40236 (93.49%) |
| Horizontal shift +2 px | 2366 / 3084 | 2513 / 3084 |
| Horizontal shift -2 px | 2529 / 3084 | 2647 / 3084 |
| Asymmetric edges | 2381 / 3084 | 2561 / 3084 |
| Inset 2 px | 2696 / 3132 | 2790 / 3132 |
| Outset 2 px | 2747 / 3084 | 2796 / 3084 |
| Resampling, each of the two variants | 3131 / 3132 | 3131 / 3132 |

There are 480 inapplicable crop attempts, excluded from the applicable totals.
The candidate makes 1506 fewer square errors on perturbed inputs. It gains 674
exact perturbed boards but loses 11 that v8 got right: a net gain of 663, **not a
universal improvement**. No originally correct unperturbed board is lost; each
clean/mark/arrow category improves in aggregate. Per-class precision/recall,
confusion matrices, all scenarios and the individual paired losses are retained
in the comparison report.

After freezing the candidate, the [consulted corpus regression](../../data/reports/neural-tolerance-regression.json)
preserves 3456/3456 boards and 221184/221184 squares for both models with verified
bounds. This isolates classification; it does not claim a new detection/full-pipeline
run over all 3456 images. The detector and production preprocessing are unchanged.
The [six original failures](../../data/reports/digital-regressions-tolerance.json)
pass both bounds and complete-position checks through the real pipeline. The
[15 development images](../../data/reports/video-development-v2-tolerance.json)
retain 13/15 in detection, classification with reviewed bounds and full-pipeline
recognition; only deferred videos 009/010 fail. The CLI on video 002 also returns
the exact expected JSON, exit code 0 and no stderr output.

The completed full test run recorded 1582 passed, 36 skipped and 8 expected
failures. After adding the optional verified-bounds regression mode, the targeted
suite recorded 107 passed. The [closeout record](../../data/reports/neural-tolerance-summary.json)
links the evidence and hashes. Step 4 is complete within this measured scope;
the next step still repeats the full pipeline corpus and freezes the release
candidate. Independent final acceptance has not been run.

## Commands

From the repository root with the `ml` extra installed and the existing local
capture/square datasets available:

```bash
python -m tools.evaluate_tolerance --dataset .cache/digital-style-squares-v2 --model .cache/neural-styles-v8/best.pt --output .cache/tolerance-baseline.json
python -m tools.train_tolerance --dataset .cache/digital-style-squares-v2 --extra-training-dataset .cache/arrowhead-training-squares-v1 --cache .cache/tolerance-data-v1 --baseline .cache/neural-styles-v8/best.pt --run .cache/neural-tolerance-v1
python -m tools.select_tolerance --cache .cache/tolerance-data-v1 --baseline .cache/neural-styles-v8/best.pt --trained .cache/neural-tolerance-v1/best.pt --run .cache/neural-tolerance-v1-conservative
python -m tools.evaluate_tolerance --dataset .cache/digital-style-squares-v2 --model .cache/neural-styles-v8/best.pt --model .cache/neural-tolerance-v1-conservative/best.pt --output .cache/tolerance-comparison.json
python -m tools.evaluate_marks --dataset .cache/digital-style-squares-v2 --baseline .cache/neural-styles-v8/best.pt --candidate .cache/neural-tolerance-v1-conservative/best.pt --baseline-name v8 --candidate-name toleranceCandidate --split evaluation --regression --verified-only --output .cache/tolerance-regression.json
python -m tools.recheck_digital_regressions --model .cache/neural-tolerance-v1-conservative/best.pt --output .cache/tolerance-six-regressions.json
python -m pytest tests/test_bounds_tolerance.py tests/test_training_augmentation.py tests/test_neural.py
```

The commands that create a training/selection run require fresh output
directories; use another name when reproducing an existing run. Add `--resume`
to the training command to continue an interrupted epoch run with its original
configuration. The second experiment uses `--config tools/train-tolerance-v2.json`
and separate `neural-tolerance-v2` / `neural-tolerance-v2-selected` directories.
A paired tolerance comparison exits 1 when its validation gate fails.

The selected candidate can be tested without changing the v8 reference:

```bash
boardsnap .cache/real-use-tests/chesscom-video-002.png --model .cache/neural-tolerance-v1-conservative/best.pt --orientation black-bottom
```

Keep v8 and the candidate in different directories. Weights, prepared arrays and
screenshots stay in ignored `.cache`; reproducible tools and measured reports
belong in the repository. This experiment does not declare video-wide or mobile
application compatibility, and it cannot restore a piece whose identifying
information is absent from the image.
