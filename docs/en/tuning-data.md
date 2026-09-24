# Tuning samples (pending)

**English** | [Spanish](../es/tuning-data.md) · [Overview](README.md)

Location: [`data/tuning/`](../../data/tuning/).

This directory is reserved for images used to create templates, tune
preprocessing, and, in the future, train or validate classifiers. It does not
contain samples or artifacts yet.

For each sample added, record its identifier, source, permission to use it,
visual profile, resolution, known position, orientation, and source group. All
its crops, augmentations, and transformations will belong to the same partition.
For learned models, validation will also be separated from training.

Do not copy images from `tests/fixtures/evaluation/` here while retaining them
as evaluation data. A sample used for tuning is no longer an independent
evaluation sample.
