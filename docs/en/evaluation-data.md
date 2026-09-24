# Evaluation images (pending)

**English** | [Spanish](../es/evaluation-data.md) · [Overview](README.md)

Location: [`tests/fixtures/evaluation/`](../../tests/fixtures/evaluation/).

This directory is reserved for images that will not be used to build templates,
train classifiers, or select thresholds. It does not contain images or expected
positions yet.

Each case will have an independently annotated `piecePlacement` and metadata
for its source, permission to use it, style, resolution, orientation, and source
group. Negative cases will have an expected error. Board boundaries will also
be annotated when a board is present, so that detection can be measured.

Partitioning by position and original image will happen before generating
variants. Do not share originals, crops, or transformations with `data/tuning/`.
Annotations will be test data, not inputs to the recognizer.
