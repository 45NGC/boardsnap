# Local trial configuration and CPU performance

**English** | [Español](../es/local-trial.md)

**The trial configuration is ready and passes performance limits.** Photo
recognition remains experimental; this is neither quality acceptance nor a released
model distribution. No training or independent final evaluation was performed.

- [Configuration and checksums](../../data/manifests/local-trial-v1.json).
- [Complete measurements](../../data/reports/local-trial-cpu-v1.json).
- [Photographic candidate CLI quality](mixed-sqrt-cli.md).
- [Future integration design](flutter-integration.md).

## Explicit models

| Mode | Model | Status |
| --- | --- | --- |
| `digital` | `.cache/neural-tolerance-v1-conservative/best.pt` | Existing digital reference pinned in screen-preview-v1 |
| `photo` | `.cache/neural-mixed-sqrt-v1/last.pt` | Experimental photographic candidate; not promoted |
| Photographic comparison reference | `.cache/neural-phone-v1/best.pt` | Preserved unchanged |

The selected digital model is the previous conservative digital reference, not
phone-v1 used as the control in the recent CLI comparison. This benchmark checks
40 representative validation screenshots; it does not rerun the 36 real screenshot
cases with the conservative model.

`local-trial-v1.json` pins paths and SHA-256 checksums. `tools.try_model` requires
mode and orientation, verifies the model and invokes the normal CLI with an explicit
`--model`. It does not rely on `BOARDSNAP_MODEL`, infer mode or change production
defaults. It forwards the ordinary CLI output. Local configuration errors return
`CONFIGURATION_ERROR` JSON and exit 1 before recognition; this belongs to the trial
tool, not core recognition or the HTTP contract.

Run from the repository root with `.venv` activated:

```bash
python -m tools.try_model "/path/screenshot.png" --input-type digital --orientation white-bottom
python -m tools.try_model "/path/photo.jpg" --input-type photo --orientation black-bottom
```

Direct CLI equivalents, without the additional checksum verification:

```bash
boardsnap "/path/screenshot.png" --input-type digital --model .cache/neural-tolerance-v1-conservative/best.pt --orientation white-bottom
boardsnap "/path/photo.jpg" --input-type photo --model .cache/neural-mixed-sqrt-v1/last.pt --orientation black-bottom
```

Choose the actual board view, not the side to move. Success JSON still contains
only `piecePlacement`. `.cache` weights are local; cloning the repository does not
download them. This configuration is not a distribution bundle with weights,
dependencies or clean-install verification.

## Full pipeline with a resident model

Measured November 16, 2026 on Intel Core i5-10400, Linux x86_64, Python 3.12.3,
PyTorch 2.14.1+cpu, four PyTorch threads and one OpenCV thread. Each mode uses a
fresh process with one model; measurements run sequentially.

| Metric | Digital conservative model | Photographic square-root candidate |
| --- | ---: | ---: |
| Consulted validation images | 40 | 30 |
| Warm median | 448 ms | 1,040 ms |
| Warm p95 | 519 ms | 2,782 ms |
| Cold imports, load and first image | 1,406 ms | 2,041 ms |
| Peak process RSS | 317 MiB | 427 MiB |
| Exact positions | 40/40 | 22/30 |

Failures contribute to timing and the photographic denominator. p95 describes one
pass over different images, not repeated latency variability per image. Peak RSS
includes imports, decoding, buffers and allocator retention; it is not the weight
file size or isolated network memory.

Existing trial limits were preserved: p95 ≤1 s digital/≤5 s photo, cold ≤5/10 s,
RSS ≤1,024 MiB, at least 40/30 samples. **Both modes pass.** These are local
desktop/server limits, not promises for Android, iOS, HTTP or concurrent requests.

## Isolated photographic classifier comparison

The same verified 64-square first photographic validation board from the mixed
plan was used for both models. Each model runs in three fresh processes, each with
20 warmups and 100 measurements. No full corpus or second model is resident.
Timing includes RGB-to-tensor preprocessing and network inference; it excludes
photo decoding, detection and rectification.

| Aggregate metric | phone-v1 | Candidate |
| --- | ---: | ---: |
| Median of trial medians | 1.284 ms | 1.291 ms |
| Median of trial p95 values | 2.015 ms | 2.008 ms |
| Median peak RSS | ≈257 MiB | ≈256 MiB |

Candidate/reference ratios are 1.005 for median latency, 0.996 for p95 and 0.998
for RSS, all below the frozen relative limit of 1.25. Differences are small and do
not establish a robust speedup. Most full photographic pipeline time lies outside
64-square classification; current latency does not require a faster network.

## Verification and reproduction

Five tests pass, covering explicit selection, checksum failure, repository path
containment, mode/orientation and status forwarding, structured configuration
errors and fresh-process median aggregation. Actual launcher smoke tests on a
known photo and screenshot verify expected placement, JSON stdout and empty stderr.
Model and production-code hashes are preserved.

```bash
python -m tools.benchmark_local_trial
python -m pytest tests/test_local_trial.py -q
```

Completed worker measurements are stored in `.cache/local-trial-cpu-v1/`. After an
interruption, identical completed signatures/recipes are reused. Original results
are preserved. Reports record implementation, model, configuration, sample and
source checksums.

## Decision and next step

This configuration can support testing the future Flutter recognition flow with
photographic mode explicitly experimental. Performance passing does not resolve
annotated-corner quality regressions or turn consulted validation into final data.

Next, fix the per-mode integration contract and prepare a minimal separate HTTP
adapter, with tests comparing its JSON to the CLI. Clients would send image,
orientation and `inputType`; the server selects the pinned model. No HTTP server
was implemented in this task.

The latest evidence shows a useful gain (20→22 exact photos with automatic detection),
but does not guarantee another substantial gain within a week or generalization to
new photos. Performance/configuration work does not improve accuracy; another
quality gain requires a specific intervention and an independent check.
