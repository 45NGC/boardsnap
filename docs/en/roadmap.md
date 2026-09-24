# Incremental roadmap

**English** | [Spanish](../es/roadmap.md) · [Overview](README.md)

## 0. Project scaffold (this iteration)

An installable `boardsnap` package with a single `__init__.py`, a documented
architecture proposal, pytest configuration, and separate areas for tuning and
evaluation. Modules will be added as each stage is implemented. This iteration
includes no algorithms, recognition functions, templates, models, images,
executable CLI, or simulated recognition tests.

## 1. Testable contract and first data profile

Implement and test serialization of known matrices and the contract's errors.
Define a first profile using our own screenshots of **a single lichess theme**,
explicitly recording the piece set, background, and sizes; its exact identity
will be chosen based on available samples. It will not be declared supported
before it is measured.

Start with PNG images, a complete aligned board, static pieces without overlays,
and a single grid per image. Reserve evaluation images with annotated positions
from the outset. Include all pieces, empty squares, both orientations, and
asymmetric positions. Preserve border coordinates when present.

Partition by original image, position, and family of variants: crops, resized
images, and compressed versions derived from the same sample will remain in
the same partition. No template will be extracted from the evaluation set.

## 2. First complete pipeline and CLI

Implement image reading, grid detection through geometry and regularity,
cropping, size normalization, 64-square segmentation, and a template classifier
for the selected profile. Treat square backgrounds and pieces separately.
Resolve orientation using the coordinates supported by the profile or apply
the documented convention.

Connect the CLI to the same core and check JSON, errors, and exit codes. Each
stage will have isolated tests; the complete flow will be evaluated on held-out
images. This milestone requires reporting observed failures and matching every
position exactly in an acceptance suite fixed before tuning; it does not imply
universal recognition.

## 3. Measured expansion of digital support

Add a specific chess.com profile, followed by new themes, resolutions, and
formats, one at a time. Test compression, interface margins, and different
colors using separate samples. Record what has been measured and what remains
out of scope for each profile. Maintain regression tests for previous profiles
when adding a new one.

## 4. Book diagrams

Start with a specific family of printed symbols, complete diagrams, and clean
scans. Evaluate binarization, lines, and contours for grids without alternating
colors, then moderate skew, noise, and paper backgrounds. Do not extrapolate
results from digital screenshots to typographic symbols in books.

## 5. Learned classification and integration

If templates require too many variants or fail evaluation, compare visual
descriptors with a small classifier and, if justified, a 13-class convolutional
network, with PyTorch as a candidate framework. Separate training, validation,
and final evaluation before tuning models. Version the data and artifacts.

Explicitly choose the chess-scanner integration mechanism once platforms,
latency, and execution constraints are known. Implement it in a separate
adapter, preserving the existing contract and core.

## Initial comparison of approaches

These are design hypotheses to test against the dataset; no accuracy measurements
exist yet. Geometric detection and piece classification are separate tasks and
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
