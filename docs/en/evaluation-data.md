# Evaluation images

**English** | [Spanish](../es/evaluation-data.md) · [Overview](README.md)

Location: [`tests/fixtures/evaluation/`](../../tests/fixtures/evaluation/).

The first profile contains four annotated PNGs: `pos-003` (pawn ending) and
`pos-010` (constructed middlegame), each in both orientations. They were assigned
to evaluation before capture and have only been used to check the capture tool,
not to tune recognition. Reserve them from template building, classifier training
and threshold selection. This two-position set does not establish general accuracy.

The [collection manifest](../../data/manifests/lichess-cburnett-brown-v1.json)
records the split and visual review. Labels were checked against the screenshots;
bounds originate in the browser DOM and were visually checked for grid extent,
not independently measured to subpixel precision. The images retain their original
capture metadata and hashes. Attribution is in the
[source notices](../../data/THIRD_PARTY_NOTICES.md).

Each case will have an independently annotated `piecePlacement` and metadata
for its source, permission to use it, style, resolution, orientation, and source
group. Negative cases will have an expected error. Board boundaries will also
be annotated when a board is present, so that detection can be measured.

Partitioning by position and original image happened before generating variants.
Do not share originals, crops, or transformations with `data/tuning/`. Annotations
are expected test data, never inputs to the recognizer. Negative images without
a board and variation in board size/location still need to be collected.
