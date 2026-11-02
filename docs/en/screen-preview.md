# Frozen screen-recognition preview

**English** | [Español](../es/screen-preview.md)

`screen-preview-v1`, package **0.1.0.dev1**, is a portable Linux CPU preview for
external testing. It is **not final acceptance**. The digital and photo models
remain separate and unchanged. No independent final images were captured or read.

## Frozen candidate and catalogue

The [policy](../../data/manifests/screen-preview-v1.json) pins every runtime Python
file, installed asset, package configuration, both weight checksums and their
metadata: architecture, class order, input size, preprocessing, training settings
and data versions. The archive also inventories source, wheels, dependencies,
notices, documentation and measurement reports. Changes require a new candidate;
older policies and release artifacts remain historical records.

| Mode | Target catalogue | Status |
| --- | --- | --- |
| Digital Lichess | cburnett, Merida, Alpha on brown/blue/green; Staunty on brown/blue/wood4 | 12 measured combinations, independent acceptance pending |
| Digital Chess.com | Neo, Classic, Bases on green/brown/blue; Alpha on green/blue/wood | 12 measured combinations, independent acceptance pending |
| Photographs | Complete screen boards from Lichess, Chess.com and videos, moderate perspective, explicit view | Experimental; no official photographic theme declared compatible |

Digital layout/condition coverage is the fixed catalogue in the policy: desktop
editor/analysis captures, clean board crops and artificial margins, controlled
last-move/selection/check/circle/dot marks and four arrow conditions. This does not
establish arbitrary video layouts, real overlays or native Android/iOS app support.

The finite photographic inventory remains the 13 **observed visual groups** in
[the classifier diagnosis](phone-classifier-analysis.md): `cc-classic`, `cc-flat`,
`cc-shaded`, `cc-thin-stem`, `lc-classic-a`, `lc-classic-b`, `lc-rounded-king`,
`video-chessbase`, `video-classic-a`, `video-classic-b`, `video-flat-brown`,
`video-flat-green`, `video-flat-vibes`. These are not official themes. Current
photographic evidence is one iPhone 8 and 30 consulted photos; useful results on a
few photos do not establish compatibility across devices or all these groups.
Books, physical 3D pieces, heavily occluded pieces and unmeasured themes are excluded.

## Acceptance fixed before independent data

Installation readiness is distinct from recognition quality. The preview can be
copied and tested now; photographic quality still blocks a general photo release.

| Gate | Digital | Photographic target |
| --- | ---: | ---: |
| Complete positions correct, including missed boards as failures | ≥99% | ≥90% |
| Complete positions in each declared stratum | ≥98% | ≥85% |
| Precision and recall of each of 13 classes | ≥99.5% | ≥98% |
| Missed boards | ≤0.5% | ≤5% |
| False detections | ≤0.5%, ≥200 negatives | ≤1%, ≥100 negatives |
| Explicit orientation mapping | 100% | 100% |
| Geometry agreement among all positive inputs | ≥99.5% within 2 pixels | ≥95% within existing photo geometry policy |
| Warm full-pipeline p95 | ≤1 s | ≤5 s |
| Cold import/load/first image | ≤5 s | ≤10 s |
| Peak process RSS | ≤1024 MiB | ≤1024 MiB |

Digital sample/stratum requirements are retained from the previous digital policy,
including at least 4,560 positive images. The photographic target requires at least
120 positives from 20 identified independent source groups, 30 per source category,
10 per declared stratum and 50 expected squares per class. All requirements apply
simultaneously; some catalogues therefore require more than 120 images. Strata
include source, observed piece design, background, perspective, resolution,
overlay and orientation. Missing evidence fails, and aggregate scores cannot hide
a failing stratum. Photo geometry uses IoU ≥.95, corner error ≤1% of board side
and maximum grid displacement ≤8% of a cell.

Photo thresholds are first-version utility targets, **not lowered to pass 20/30**.
These sample sizes do not prove population-wide error bounds. Freeze grouping and
review annotations before inference; positions, game/video relatives and variants
stay together. This preparation does not start final evaluation. The photographic
final corpus and its evaluation procedure must be prepared separately. Consulted
batches remain development/regression data; using final results to tune consumes
their independence. The existing digital evaluator targets its own policy/schema;
do not pass this two-model preview policy to it as if it were compatible.

## Measurements and installation

Fresh **non-editable wheel installation**, no system site packages, CPython 3.12.3,
Linux x86-64, Intel Core i5-10400, Torch 2.14.1+cpu, four Torch threads and one OpenCV
thread. Runs were sequential after the regression suite completed.

| Validation benchmark | Digital | Photo |
| --- | ---: | ---: |
| Different images, including failures | 40 | 30 |
| Exact complete positions | 40/40 | 20/30 |
| Warm p95 | 546 ms | 2,839 ms |
| Cold import/load/first image | 1,499 ms | 2,130 ms |
| Peak RSS | 437 MiB | 549 MiB |

Warm measurements reuse one resident model and include decoding, detection,
normalization/rectification, classification and output construction. Cold time
includes Python-library imports, loading and the first image; it is not a p95 of
many independent process starts. Process RSS includes imported libraries. These
are CPU-specific observations, not phone, server-concurrency or HTTP measurements.
The 40-image digital benchmark is a timing sample, not a new quality evaluation.

The clean environment passes `pip check`, nine digital installation checks and
11 photo checks: both views, both entry points, exact JSON, structured image/model
errors, missing board and invalid arguments. Commands run from `/tmp` without the
checkout on `PYTHONPATH`. Digital installed files are checked byte-for-byte against
the wheel. Photo references come only from previously consulted validation.

The general suite passed 1,665 tests; 80 optional browser/model or unavailable
fixture tests were skipped, and 161 evaluation-marked tests were excluded. Release
tooling checks are recorded separately (33 passed, including 16 new tests).
The skipped tests are not counted as passes. No model was trained or replaced.

## Portable artifact

Local archive: **`.cache/releases/screen-preview-v1.tar.gz`**. The expanded directory
has the matching wheel, a dependency wheelhouse, `requirements.lock` with exact
versions/hashes, two model bundles, source snapshot, policies, reports, notices,
`INSTALL.md` and a standard-library verifier. Raw photos and private datasets are
not distributed. Nothing is uploaded automatically; `.cache` stays out of Git.

The [distribution report](../../data/reports/screen-preview-v1.json) records the
archive and release-manifest SHA-256 values independently. Check the archive hash
before extraction. Copy it to another **Linux x86-64 / Python 3.12** machine; the
bundled wheels require glibc 2.28 or newer. Other targets need matching dependency
wheels and their own installation/CPU checks. CPU PyTorch is included; no GPU,
network access, editable checkout or training corpus is needed for inference.

From the extracted `screen-preview-v1` directory:

```bash
python3.12 verify_preview.py . --sha256 MANIFEST_SHA256_FROM_DISTRIBUTION_REPORT
python3.12 -m venv /tmp/boardsnap-preview-env
/tmp/boardsnap-preview-env/bin/python -m pip install --no-index --find-links dependencies --require-hashes -r requirements.lock
/tmp/boardsnap-preview-env/bin/python -m pip check
/tmp/boardsnap-preview-env/bin/boardsnap /path/image.png --model "$PWD/models/digital/model.pt" --orientation white-bottom
/tmp/boardsnap-preview-env/bin/boardsnap /path/photo.jpg --input-type photo --model "$PWD/models/photo/model.pt" --orientation black-bottom
```

Create the environment **outside** the extracted directory so integrity verification
continues to reject unlisted files. If this Linux installation lacks `ensurepip`,
create it with `--without-pip`, then use an existing pip's `--python ENV/bin/python`
option with the same offline install arguments. The package accepts PNG/JPEG;
convert HEIC first. Choose the model and input type explicitly. Successful JSON
still contains only `piecePlacement`; errors and exit codes are unchanged.

## Remaining work

Photo v1 still misses `video-img_5403`, predicts a false knight on h8 in `5406`,
and has style/moire errors documented in the [quality review](photo-recovery.md).
The digital benchmark passing does not establish a new independent acceptance
result. Final recognition acceptance, publication, model hosting and Flutter/HTTPS
remain pending. The existing [Flutter contract](flutter-integration.md) is unchanged.
