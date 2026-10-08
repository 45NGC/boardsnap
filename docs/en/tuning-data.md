# Tuning samples

**English** | [Spanish](../es/tuning-data.md) · [Overview](README.md)

This guide records the original brown-profile implementation. See [evaluated profiles](profiles.md) for subsequent digital styles, the experimental book profile and current coverage.

Location: [`data/tuning/`](../../data/tuning/).

The new [position plan](position-plan.md) defines separate `training`, `validation`
and `evaluation` groups before capture. It does not rename or redistribute this
legacy tuning corpus, and no new images have been collected from that plan yet.

Use the [capture utility](capture-data.md) to collect the first lichess profile
from a manifest with positions assigned to partitions in advance.

The first dataset is `lichess-cburnett-brown-v1`: 16 PNGs and JSON annotations
covering eight positions in both orientations. The reviewed pilot captures
were adopted unchanged on 2026-09-30. They are available for templates,
preprocessing and initial classification experiments; they are not a complete
training corpus. No model or recognition accuracy is available yet.

The [collection manifest](../../data/manifests/lichess-cburnett-brown-v1.json)
fixes the positions and splits independently of the editable tool example.
Images are 1280 × 1000 with a 584 × 584 board, cburnett pieces, brown squares,
internal coordinates and editor context. Each JSON records the original capture
time, source, canonical placement, orientation, bounds and image hash. See the
[source notices](../../data/THIRD_PARTY_NOTICES.md) for artwork attribution.

All 20 dataset screenshots were visually checked against positions and
orientations. The grid extent was visually checked; fractional DOM-derived
bounds were preserved, not independently measured to subpixel precision.
The dataset integrity tests check files and partition consistency, not detection.
Regenerate into a fresh output root using the collection manifest; do not
overwrite the committed fixtures when the live site changes.

For each sample added, record its identifier, source, permission to use it,
visual profile, resolution, known position, orientation, and source group. All
its crops, augmentations, and transformations will belong to the same partition.
For learned models, validation will also be separated from training.

Do not copy images from `tests/fixtures/evaluation/` here while retaining them
as evaluation data. A sample used for tuning is no longer an independent
evaluation sample.
