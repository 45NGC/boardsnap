# Evaluation data

The first profile, `lichess-cburnett-brown-v1`, contains four PNGs and JSON
annotations: `pos-003` and `pos-010`, each in both orientations. Reserve these
images for evaluation; do not use them to select templates, thresholds or models.
Their pilot use checked capture correctness only, before recognition development.
Two positions are an initial regression set, not a representative benchmark.

The [collection manifest](../../../data/manifests/lichess-cburnett-brown-v1.json)
fixes the splits. Preserve the [source notices](../../../data/THIRD_PARTY_NOTICES.md).
Read the [evaluation guide in English](../../../docs/en/evaluation-data.md).

A [Spanish version of the evaluation guide](../../../docs/es/evaluation-data.md)
is also available.

Additional reserved partitions: blue/cburnett (4 images), Chess.com green (4)
and the hatched book edition (2). Digital themes share the same two positions;
these are not independent positions just because their artwork differs.
The book baseline currently fails both complete positions (126/128 squares).
Those failures remain explicit in the reports and strict `xfail` tests.
See [evaluated profiles](../../../docs/en/profiles.md).
