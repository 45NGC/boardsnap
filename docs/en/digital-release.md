# Digital acceptance and distribution

**English** | [Español](../es/digital-release.md) · [Overview](README.md)

**Current status: candidate, not an accepted digital release.** The
[readiness report](../../data/reports/digital-readiness-v1.json) blocks final
evaluation because the current model adds two arrow regressions and the detector
misses four cropped boards. The [step 9 measurements](style-expansion.md) remain
regression evidence. They are not renamed or reused as an independent final test.

The acceptance tools, thresholds, new position plan, model bundle and clean
installation checks are implemented. No final acceptance images have been
captured or recognized in this iteration. The position plan remains reserved.
The package retains `0.1.0.dev0`; nothing has been published.

## Frozen scope and thresholds

The [machine-readable policy](../../data/manifests/digital-acceptance-v1.json)
was written before final evaluation. It pins the model SHA-256, runtime source
hashes, catalogue, position plan and thresholds. Changing the candidate or criteria
requires a new policy version; never overwrite an existing frozen policy.

| Platform | Pieces | Backgrounds | Present evidence / limitation |
| --- | --- | --- | --- |
| Lichess | cburnett, Merida, Alpha | brown, blue, green | Evaluated pilot; acceptance pending |
| Lichess | Staunty | brown, blue, wood4 | Evaluated pilot; four crop detection misses on blue/wood4 |
| Chess.com | Neo | green, brown, blue | Evaluated pilot; two arrow regressions on brown/blue |
| Chess.com | Classic, Bases | green, brown, blue | Evaluated pilot; acceptance pending |
| Chess.com | Alpha | green, blue, wood | Evaluated pilot; acceptance pending |
| Native Android/iOS apps, other live interfaces | — | — | Not demonstrated by desktop browser captures |
| Other themes, real native overlays, opaque occlusion | — | — | Outside this acceptance scope |
| Book diagrams | — | — | Outside the digital version |

The 24 pairs target Lichess's editor and Chess.com's analysis page in a desktop
browser. Simple marks and arrows use the existing controlled renderer. Board-only
384-pixel crops and 256-pixel boards with artificial margins are clean layout
probes, not evidence for native mobile apps or all small-board/overlay combinations.

| Gate | Required result |
| --- | --- |
| Exact complete placements, full pipeline | At least 99% overall |
| Each combination, condition, layout, platform and explicit view | At least 98% exact complete placements |
| Each of the 13 classes | Precision and recall both at least 99.5%; at least 100 expected squares |
| Missed boards | At most 0.5% |
| Bounds within two pixels | At least 99.5% of positive images, including failures in the denominator |
| False detections | At most 0.5% on at least 200 negative images |
| Explicit orientation mapping | 100% of canonical mappings; both views also contribute to full-placement gates |
| Warm CPU processing, full pipeline | p95 at most 1000 ms |
| Cold imports, model load and first image | At most 5000 ms in a fresh process |
| Peak CPU process RSS | At most 1024 MiB |
| Preparation prerequisites | No new wrong-image regressions, no unresolved known detection misses, clean installation passes |

Missing classes/strata and nonfinite or unmeasured metrics fail. Improvements in
one condition cannot compensate for a failing condition. Orientation means the
supplied view, not turn information. Automatic coordinate reading remains optional
and **outside acceptance**; its limitations are documented in the style guide.

Timing targets refer to Linux CPU, four Torch threads and one OpenCV thread,
without HTTP. They are not claims about inference on Android/iOS. The 0.5% negative
threshold and the small source-game count are pilot criteria, not statistical
proof of a population-wide error bound.

## Independent reserved data

The [new plan](../../data/manifests/digital-acceptance-positions-v1.json) contains
40 positions from ten new generated legal games, including openings, middlegames,
endgames and promotions. Source games and equivalent placements are checked
against the consulted plan and legacy corpora. Moves are replayed to verify labels;
the 13 classes appear on both square colors. This does not represent human play.

The capture recipe derives 1920 clean images: 40 positions × 24 combinations ×
two views, with standard/compact sizes assigned by group. One position/view per
game and combination receives nine mark/arrow cases and two clean layout probes.
This gives **4560 planned positives** and 240 generated negatives (6×6, 7×7,
9×9, 10×10, incomplete 7×8 grids and interface blocks). Negatives are synthetic;
real non-board screenshots require their own reviewed corpus.

All variants retain their game and position. Their split is `acceptance`, which
the training loader rejects. Capture checks rendered artwork, placement, view,
complete board geometry and PNG/annotation integrity using the existing browser
adapter. Final evaluation uses pixels and explicit view; annotations only score it.

`evaluate_acceptance` first recomputes readiness from checksum-pinned evidence.
It refuses the current candidate **before opening the corpus**. When readiness
passes, an exclusive `acceptance-attempt.json` marks the set as consulted before
inference. Failed/crashed runs cannot silently be rerun as a fresh final test.
Use consulted cases for regression and prepare a new independent acceptance set
after tuning. A corrected candidate can reuse this still-unobserved plan, but must
have a new frozen policy with its actual weights and runtime hashes.

Use `prepare_acceptance --reuse-plan` with new policy/model paths for that case.
Every started evaluation also records source-game and position identities under
`data/reports/acceptance-attempts/`. Retain these reports: renaming or copying a
cache directory does not create an independent set. Plan generation excludes
these consulted sources. Unit tests use temporary histories, not the reserved set.

## Measurements and installation performed

The [CPU report](../../data/reports/digital-candidate-cpu-v1.json) uses 40 validation
images, not final data: p95 **168 ms**, cold **1380 ms**, peak **309 MiB** on an Intel
Core i5-10400. All 40 placements matched. Exact versions and machine details are
recorded; timings vary with hardware and load.

The [clean installation report](../../data/reports/digital-clean-install-v1.json)
records an isolated Python 3.12 environment without system packages, a non-editable
wheel, and execution from `/tmp`. Checks cover both platforms/views, exact JSON,
no-board and empty-image errors, invalid orientation, legacy installed assets and
the module entry point. `pip check` found no broken requirements. This is a Linux
installation check, not a claim about other Python versions or operating systems.

## Local distribution artifacts

The local directory `.cache/releases/digital-preview-v1/` holds the wheel,
dependency wheels and `model/`. The model directory includes weights, metadata,
checksums, license and notices. The [bundle report](../../data/reports/digital-model-bundle-v1.json)
records the manifest checksum separately. Metadata preserves architecture, class
order, preprocessing, input size, training settings and source data hashes.

```bash
python -m tools.model_bundle verify .cache/releases/digital-preview-v1/model --manifest-sha256 CHECKSUM_FROM_BUNDLE_REPORT
```

Verification rejects altered weights, metadata and notices. Distribution is a
local artifact, with no upload or model download service. Copy the entire model
directory alongside the matching wheel. `build --acceptance-report PATH` can
label a future bundle accepted only when its final report passes the frozen
gates and matches the exact model/policy; omission always produces a candidate.

Install the wheel and CPU dependencies, then configure an absolute model path:

```bash
python -m pip install --no-index --find-links .cache/releases/digital-preview-v1/dependencies '.cache/releases/digital-preview-v1/wheels/boardsnap-0.1.0.dev0-py3-none-any.whl[ml]'
export BOARDSNAP_MODEL="$PWD/.cache/releases/digital-preview-v1/model/model.pt"
boardsnap image.png --orientation white-bottom
```

Run installation inside a new environment. Where `ensurepip` is unavailable,
`python3 -m venv --without-pip NEW_ENV` plus an existing pip's
`python -m pip --python NEW_ENV/bin/python install ...` avoids changing system Python.
The downloaded wheel directory here targets Linux x86-64/Python 3.12. Other targets
need matching dependency wheels and their own clean installation check.

The public response remains exactly `{"piecePlacement": "..."}` on success or the
existing structured error. No confidence, alternatives or remaining FEN fields
are added. HTTPS and Flutter remain [documented](flutter-integration.md), without
an HTTP server or client implementation here.

## Commands and next release decision

```bash
python -m tools.digital_acceptance --policy data/manifests/digital-acceptance-v1.json --model .cache/neural-styles-v2/best.pt --regression data/reports/neural-styles-v2-evaluation.json --benchmark data/reports/digital-candidate-cpu-v1.json --installation data/reports/digital-clean-install-v1.json --output data/reports/digital-readiness-v1.json
python -m pytest
```

Readiness currently exits **1** with two failed prerequisites. First fix those
cases using development/validation data and rerun regression, CPU and clean-install
checks. Freeze a new version of the policy for the corrected candidate. Then:

```bash
PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright" python -m tools.acceptance_corpus --policy NEW_POLICY.json --plan data/manifests/digital-acceptance-positions-v1.json --capture-root .cache/final-captures --output .cache/final-corpus
python -m tools.evaluate_acceptance --policy NEW_POLICY.json --plan data/manifests/digital-acceptance-positions-v1.json --model NEW_MODEL.pt --readiness NEW_READINESS.json --corpus .cache/final-corpus --output data/reports/digital-final-acceptance.json
```

The evaluator exits 0 for acceptance, 1 for measured rejection, and 2 for a blocked
or invalid attempt. No final acceptance report has been produced today. Current
readiness, CPU and installation reports must not be presented as that final result.


Verification: the complete suite passed 1333 tests (36 optional browser cases
were skipped and two experimental book cases were expected failures). Running
the browser suite separately passed all 71 cases, including those 36 optional
cases. These use simulated local pages, not a live-platform acceptance corpus.
