# Tuning data

The first profile, `lichess-cburnett-brown-v1`, contains 16 PNGs and JSON
annotations: eight positions captured in both orientations. Use them for
developing detection, normalization and classification. This is a small initial
set, not a complete model-training corpus. Keep all derivatives in this partition.

The [collection manifest](../manifests/lichess-cburnett-brown-v1.json) fixes the
split assignments. Preserve the [source notices](../THIRD_PARTY_NOTICES.md).
Read the [data guide in English](../../docs/en/tuning-data.md).

A [Spanish version of the data guide](../../docs/es/tuning-data.md) is also available.

Additional committed partitions: blue/cburnett lichess (16 images), current
Chess.com green (14) and the experimental hatched book edition (5). See
[evaluated profiles](../../docs/en/profiles.md) for collection differences,
rebuild commands and results. All templates come from tuning, and shared
positions keep the same partition across themes and book diagrams.
