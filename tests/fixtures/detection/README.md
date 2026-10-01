# Detection references

`references.json` fixes integer edge references for the existing screenshots:
left 190, top 158, right 774, bottom 742 (exclusive right/bottom). These bounds
were visually reviewed by Codex against the complete grid. They round the
previously reviewed DOM annotations, not an independent subpixel measurement
or a human labeling study. Original fractional sidecars remain unchanged.

The screenshot layout is shared, so one box applies to every listed sample.
The reference contains explicit sample IDs and split membership. Detector code
never reads this file, sidecars, manifests or screenshot filenames.

Tests derive cropped, resized and relocated images with known coordinate
transforms. For board-free examples they remove the grid from the screenshot,
retaining menus and spare pieces. No derived image is moved between splits;
variants are test inputs, not new independent observations. Synthetic unit
images use separately specified grid sizes and placements with exact bounds.
