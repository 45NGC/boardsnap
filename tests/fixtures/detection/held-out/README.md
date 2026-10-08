# Held-out digital detection images

Eight original PNGs: games 004 and 005 from each platform. Each game contributes
two positions; arrows, highlights and circles are intentionally retained.
Rectangles, hashes and provenance are recorded in
[the manifest](../../../../data/manifests/digital-detection-v1.json).

Split assignments and the two-pixel edge-error tolerance were fixed before the
first held-out detector run. Visual review was used to annotate bounds, not to
select detector thresholds. These are four source groups, not eight independent
games. Any crops/resizes/removals retain the parent split.

The images have no verified FEN labels and do not establish classification
accuracy. Do not build piece templates or tune detection from these fixtures.
Preserve [source notices](../../../../data/THIRD_PARTY_NOTICES.md).
