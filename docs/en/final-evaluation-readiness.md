# Final evaluation: outstanding prerequisites

**English** | [Español](../es/final-evaluation-readiness.md)

**Step 7 is not complete.** The November 3, 2026 review did not run final inference,
consume reserved data or grant acceptance. The `screen-preview-v1` candidate,
models and distribution remain unchanged.

The [reproducible audit](../../data/reports/screen-final-readiness-v1.json) verifies
hashes of the policy, runtime, assets, models, distribution and reused measurements.
It distinguishes installation/performance from quality and independence. This is
not a final evaluator and cannot grant acceptance.

## Missing prerequisites

1. **Photographic quality.** Consulted results are 20/30 (66.7%), below the frozen
   90% target. Source categories are Lichess 8/10, Chess.com 5/10 and video 7/10,
   also below the 85% per-group target. This diagnoses readiness, not final
   acceptance. Renaming the dataset or selecting only successes cannot fix it.
2. **Current digital evidence.** The pinned regression report passed with the same
   model, but its runtime hashes predate photographic integration. This does not
   establish a new regression; evidence tied to the current code is missing.
   The 40 correct benchmark images do not replace regressions or final evaluation.
3. **Reviewed independent corpus.** None was supplied to this audit. All 191 files
   in the usual photo directory already have paths recorded in manifests/reports;
   they are not a newly independent batch. No image pixels were opened for this
   filename inventory.
4. **Matching protocol.** The old digital evaluator does not directly accept the
   current two-model policy schema. Bind the final protocol to the candidate,
   required strata and readiness evidence before executing it.

The photo policy requires at least 120 positives from 20 identified independent
sources and 100 negatives, plus category/class/stratum minimums. These are not
instructions to take random new photos immediately: first establish candidate
readiness and source grouping rather than spend final data on tuning.

## Scope decision

- **Digital first, photos experimental:** refresh digital regressions, prepare a
  digital protocol tied to the candidate and collect/capture its reserved corpus
  for the 24 combinations. Acceptance would apply only to that digital scope;
  photos must remain explicitly experimental.
- **Both modes accepted:** continue addressing photographic failures with
  development data, freeze another candidate if recognition changes, then prepare
  independent corpora for both modes. Do not lower the frozen thresholds to pass
  existing results.

Controlled screenshots can be automated. New screen photographs require actual
camera shots; synthetic variants do not establish photographic coverage. Record
source game/video, expected placement, orientation and reviewed geometry. Keep
variants and related positions in one source group. Visual annotation checks
labels before inference; do not adjust images or labels to candidate predictions.

## Repeat the audit without consuming images

```bash
python -m tools.check_final_readiness --output .cache/final-readiness-recheck.json
python -m pytest tests/test_final_readiness.py -q
```

Exit code **1** explicitly means the audit does not grant acceptance; an exception
indicates invalid or modified evidence. It never invokes classification, opens
final pixels or creates attempt markers. Six tests pass: inadequate quality,
stale evidence, missing categories, mismatched weights, and inability to turn even
perfect consulted results into independent acceptance.

Actual final evaluation must retain complete-position, class, detection,
condition and performance results, including failures. Using results for fixes
converts that set into development/regression data and requires new independent
evidence. Until then, only the [external-testing preview](screen-preview.md) is
available.
