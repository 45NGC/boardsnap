# Full CLI comparison of the photographic candidate

**English** | [Español](../es/mixed-sqrt-cli.md)

**The photographic gain survives automatic detection, but the candidate loses two
real digital screenshots. Do not replace phone-v1 globally.** Models compared:
`neural-phone-v1/best.pt` and experimental `neural-mixed-sqrt-v1/last.pt`.
Weights and application configuration remain unchanged.

- [Per-image report, outputs and checks](../../data/reports/mixed-sqrt-cli-v1.json).
- [Annotated-corner experiment](mixed-sqrt-result.md).
- Tool: `python -m tools.compare_mixed_cli`.

## Scope and reuse

Thirty previously consulted validation photos and 36 unique digital screenshots
were compared: thirty annotated real screenshots and six exposed original failures.
The fifteen video-manifest entries duplicate images from the real screenshots;
identical hashes/views are checked, aliases preserved and counted once.

Real screenshots had moved into `.cache/real-use-tests/computer-screenshots/`.
The tool resolves this relocation only when the annotated hash matches and records
both paths, without changing historical manifests or using new unannotated cases.

The existing phone-v1 report `photo-pipeline-validation-v2.json` remained compatible:
model, code, manifest, detection report and image hashes were checked. It was reused.
The candidate CLI ran for every photo, with its result checked against existing
automatic geometry crops. The existing photo comparison tool also classified
annotated crops as controls. The full 3,132-board classification corpus was not rerun.

Each digital image ran through `python -m boardsnap` with both models, explicit
orientation and no expected geometry/position supplied to the CLI. Exact JSON,
exit status 0/1 and empty stderr are checked. Success returns only `piecePlacement`;
errors contain `error` with `code` and `message`. Individual process records in
`.cache/mixed-sqrt-cli-v1/` can be reused by image/model/runtime hashes, orientation
and input mode.

These are consulted development/regression data, including the six exposed failures
from an older evaluation split. **Independent final evaluation was not accessed.**
Results do not establish independent games or support for every visual style.

## Photographic results

| Metric | phone-v1 | Square root |
| --- | ---: | ---: |
| Detected boards | 29/30 | 29/30 |
| Exact photos, automatic detection | 20/30 | **22/30** |
| Exact photos, annotated corners | 19/30 | 20/30 |
| Correct squares among 29 detected photos | 1,824/1,856 | **1,839/1,856** |
| False pieces among detected photos | 3 | **2** |
| Missed pieces among detected photos | 18 | **8** |

The candidate retains all twenty baseline automatic successes and recovers
`chesscom-img_5398` and `video-img_5406`. Category results: Chess.com 5→6/10,
Lichess 8→8/10, video 7→8/10. `video-img_5403` still fails detection for both
models and counts as a failed image in the thirty-photo total.

Remaining incorrect positions: `chesscom-img_5395`, `5397`, `5401`, `5402`,
`lichess-img_5391`, `5392`, `video-img_5404`, plus the detection failure.
Expected and actual placements are preserved in the report.

Automatic false-piece counts (3→2) differ from annotated-corner counts (3→5)
because input crops differ; do not combine those experiments. Detection and
rectification are independent of classifier weights. These results are not a new
detector improvement.

## Digital results

| Metric | phone-v1 | Square root |
| --- | ---: | ---: |
| Detected boards | 36/36 | 36/36 |
| Exact screenshots | **35/36** | 33/36 |
| Correct squares | **2,302/2,304** | 2,299/2,304 |
| False pieces | 2 | 4 |
| Missed pieces | 0 | 0 |
| Six complete original cases | 6/6 | 6/6 |

No whole screenshots are recovered; two are lost:

| Image | Square | Expected | phone-v1 | Candidate |
| --- | --- | --- | --- | --- |
| real-use-6 | b8 | empty | empty | black pawn |
| real-use-12 | d3 | white bishop | white bishop | white queen |
| real-use-4 | e3 | empty | empty | black knight |
| real-use-4 | a5 | empty | black king | black knight |

`real-use-4` already failed; the candidate changes a wrong class and adds an error.
These screenshots are outside the 3,132 classification variants measured during
training, so preserving those predictions did not guarantee preserving this real
batch. No retraining or detector changes were made to address these failures.

## Verification and decision

Six comparison-tool tests pass. All completed real CLI calls satisfy the output
contract. A blank 400×400 negative returns `BOARD_NOT_FOUND` and exit status 1 in
both digital and photographic modes with both models. This is a bounded control,
not an exhaustive detector-negative regression rerun. Model and production code
hashes are preserved. Recorded process times include Python startup/model loading;
**they are not isolated CPU benchmarks**.

Keep phone-v1 as the reference and preserve square-root weights as an **experimental
photographic candidate**. Photo gains do not remove annotated-corner acceptance
failures or real digital regressions. No automatic promotion or final acceptance
is declared.

Before Flutter integration, the next useful step is CPU latency/memory measurement
and an explicit trial configuration selecting mode and model: a stable digital
reference and an experimental photographic candidate. Verify the selected models
and document the configuration; this report does not implement automatic selection
or start another training run.

## Reproduction

```bash
# Only when the candidate report is missing; preserve the earlier phone-v1 report.
python -m tools.evaluate_photo_pipeline --detection-report data/reports/photo-detection-validation-v2.json --model .cache/neural-mixed-sqrt-v1/last.pt --output .cache/neural-mixed-sqrt-v1/photo-cli-validation.json
# Reuse compatible digital process records and saved photographic reports.
python -m tools.compare_mixed_cli
python -m pytest tests/test_compare_mixed_cli.py -q
```
