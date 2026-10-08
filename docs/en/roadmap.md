# Incremental roadmap

**English** | [Spanish](../es/roadmap.md) · [Overview](README.md)

Current digital-roadmap milestone completed: explicit orientation input in the
Python pipeline and CLI (`white-bottom`, `black-bottom`, default `auto`). Tests
cover both views, missing/opposite labels, backward compatibility and invalid
values; the JSON contract is unchanged. See [orientation](orientation.md).
Further themes and overlays remain subsequent work; the book experiment is deferred.

The next planning milestone is also complete: the bilingual [digital style and
condition inventory](style-inventory.md) separates backgrounds, pieces and layouts,
defines four evidence-based states and tracks browsers and native mobile apps
independently. Its ordered work batches are the current expansion backlog.

Position planning is now implemented: [80 placements in 20 source groups](position-plan.md),
fixed training/validation/evaluation assignments (56/12/12), reproducible legal
source sequences, legacy isolation and class/background coverage checks. Eight
underrepresented combinations are documented.

[Configurable capture](configurable-capture.md) is implemented for clean Lichess
and Chess.com web boards: independent backgrounds/pieces, both views, viewport
and pixel density, verified PNG labels and atomic batches. A local 16-image
training pilot covers four combinations. Reviewed real-use import is available
for planned positions. Twenty real-use images have since been supplied and
adopted as detection-only fixtures, without FEN/classification labels. Next expand the
clean corpus, develop recognition for the new styles, and add automated marks.
Recognition compatibility and native mobile coverage are unchanged.

Digital detection now combines palette proposals, RGB boundaries, regular grid
spacing and robust cell alternation. The [detection guide](detection.md) records
28 reviewed images, grouped development/evaluation partitions, independent
rectangle metrics and negative tests. All 8 held-out originals have exact integer
bounds; no piece-classification improvement is claimed. Next broaden real-theme
and texture coverage and improve classification/normalization for markings.

## 0. Project scaffold (completed)

An installable `boardsnap` package with a single `__init__.py`, a documented
architecture proposal, pytest configuration, and separate areas for tuning and
evaluation. Modules will be added as each stage is implemented. This iteration
includes no algorithms, recognition functions, templates, models, images,
executable CLI, or simulated recognition tests.

## 1. Testable contract and first data profile

Matrix serialization and internal validation are implemented and covered by
53 passing unit test cases. Image loading now supports PNG/JPEG with RGB
normalization and the three input error codes, covered by 31 unit cases.
Template asset failures now use `PROCESSING_FAILED`.
The first profile is now `lichess-cburnett-brown-v1`: 20 annotated PNGs with
cburnett pieces, a brown board, 1280 × 1000 screenshots and a 584 × 584 grid.
There are eight tuning positions and two reserved evaluation positions, each
in both orientations. The [collection manifest](../../data/manifests/lichess-cburnett-brown-v1.json)
fixes this initial set. Collection does not establish recognition support.
First-profile [board detection](detection.md) is implemented and tested on
cropped, resized, translated and board-free cases, with reserved-image results
reported separately. Original captures still share one layout; independent
captures and broader negative examples remain necessary before generalization
claims. [Normalization and 64-square segmentation](normalization.md) are now
implemented, retaining the complete source for orientation. [Orientation](orientation.md)
now reads the profile's internal coordinates and applies the documented fallback.
The [template classifier and Python pipeline](classification.md) are implemented
with a measured initial baseline. The [JSON CLI](cli.md) is also implemented.
The subsequent [profile expansion](profiles.md) and [Flutter transport design](flutter-integration.md) are now documented.

Start with PNG images, a complete aligned board, static pieces without overlays,
and a single grid per image. Reserve evaluation images with annotated positions
from the outset. Include all pieces, empty squares, both orientations, and
asymmetric positions. Preserve border coordinates when present.

Partition by original image, position, and family of variants: crops, resized
images, and compressed versions derived from the same sample will remain in
the same partition. No template will be extracted from the evaluation set.

## 2. First complete pipeline and CLI (implemented for the initial profile)

The Python pipeline connects image input, detection, normalization, 64-square
segmentation, template classification, orientation and piece placement output.
The [CLI](cli.md) invokes this same core and provides JSON, structured errors,
exit codes and separate diagnostics. Both console and module entry points are
tested on tuning and reserved images, in addition to isolated stage tests.
The [measured baseline](classification.md) reports the limited initial acceptance
results; this milestone does not imply universal recognition.

## 3. Measured digital expansion (initial profiles implemented)

Blue/cburnett lichess and the captured Chess.com default green style now have
explicit profiles, tuning-only templates, capture tooling and regression tests.
Each recognizes 4/4 reserved images (two positions in both views). See the
[profile guide](profiles.md) for limits; these small, shared-position pilots do
not establish support for arbitrary themes, resolutions or platforms.

Next collect independently selected positions, additional browser layouts and
compression cases, and keep all existing regressions. Add one evaluated style
at a time rather than claiming every combination is covered.

## 4. Book diagrams (experimental baseline implemented)

The fixed illustrated *Chess Strategy* edition has five tuning diagrams and two
reserved diagrams. A frame/brightness detector and 80 tuning crops achieve
126/128 reserved squares, but **0/2 exact positions**. Full-position acceptance
therefore remains open, with both failures recorded as strict expected failures.

Next gather more examples of that symbol family and improve robustness on a
separate development set. If the current held-out failures inform tuning, retire
them into development and obtain new independent acceptance diagrams. Other
books, fonts, full pages and perspective correction remain outside measured scope.

## 5. Learned classification and integration

The [frozen template baseline](classification.md) can be compared with a small
13-class PyTorch model on the current profile without first covering every theme.
Separate whole source groups into training, validation and final evaluation before
tuning models, check class/background coverage and add independent samples as needed.
Keep all crop/orientation/augmentation relatives together. Version data and artifacts;
the current tiny corpus cannot establish a robust neural-model advantage.

The requested Android, iOS and web targets lead to the [documented HTTPS
proposal](flutter-integration.md). Implement the backend adapter and Flutter
client in a later task; this iteration supplies the design only and retains the core contract.

## Initial comparison of approaches

The alternatives below remain hypotheses; [template baseline measurements](classification.md)
now exist for the initial corpus only. Geometric detection and classification are separate tasks and
may use different techniques.

| Approach | Expected accuracy and limits | Complexity | Maintenance |
| --- | --- | --- | --- |
| Templates on normalized squares | A useful starting point for bounded symbol sets and scales; sensitive to new drawings, highlights, and crops. | Low; each example can be inspected. | Grows with themes, backgrounds, and variants. |
| Classical vision: lines, contours, thresholds, and descriptors | Useful for locating grids and separating foreground from background; shape rules may confuse similar pieces. | Medium; preprocessing needs tuning for each image family. | Rules may become fragile as styles expand. |
| Descriptors + a small supervised classifier | May handle variations covered by the data; depends on labels and the evaluated domain. | Medium; adds training and validation. | Requires reproducible data and artifacts. |
| A 13-class convolutional network | Potential for greater visual diversity with enough examples; does not guarantee generalization to unseen styles. | High compared with the template baseline. | Adds labeling, training, distribution, and regression monitoring costs. |

OpenCV's template matching provides a technical reference for the first
experiment ([official documentation](https://docs.opencv.org/4.x/de/da9/tutorial_template_matching.html)).
Contours and their hierarchy are another candidate tool for diagrams
([OpenCV](https://docs.opencv.org/4.x/d9/d8b/tutorial_py_contours_hierarchy.html)).
A multiclass SVM could be considered for the small classifier
([scikit-learn](https://scikit-learn.org/stable/modules/svm.html)); mentioning
these options does not mean adding them as dependencies now.

## Measuring progress

Record correct board detection, correct orientation, accuracy per square class,
and exact `piecePlacement` matches per image and style. Square-level accuracy
will not replace exact full-position matches; detection failures will also
count in end-to-end evaluation. Measure processing time and the cost of
maintaining each profile as well.

These metrics will be development reports, never fields in the app response.
Held-out evaluation data will not be used to select templates, thresholds, or
hyperparameters. If a sample is used for tuning after a failure is analyzed, it
will leave the evaluation set and a new held-out sample will be prepared.
