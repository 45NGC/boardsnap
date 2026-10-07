# Recognition templates

## Piece templates

`piece-templates.png` holds 26 RGB crops, with one example of each of the thirteen
classes on each background. Its columns are light/dark and its rows are empty,
P, N, B, R, Q, K, p, n, b, r, q, k. `piece-templates.json` records class labels,
source paths and image/annotation hashes, square indices, atlas mapping/hash
and tuning coverage. All examples come from the fixed tuning split; none comes
from evaluation. Runtime classification uses pixels and these installed assets,
not source filenames or annotations.

The crops derive from the lichess screenshots described in
`data/THIRD_PARTY_NOTICES.md` in the BoardSnap repository. The cburnett piece
artwork is by Colin M. L. Burnett, GPL-2.0-or-later; board artwork is attributed
to Lila authors and pirouetti, AGPL-3.0-or-later. These are not original BoardSnap
drawings. Preserve the source attribution and upstream terms when redistributing.
Upstream sources/notices: https://github.com/lichess-org/lila/blob/master/COPYING.md
and https://github.com/lichess-org/lila/tree/master/public/piece/cburnett.

Rebuild with `.venv/bin/python -m tools.build_piece_templates` from the repository
root. Selection is deterministic: first class/background example in filename
and image row/column order. No classifier parameters or templates are chosen
using reserved images. PNG encoding may vary across Pillow versions; the same
environment produces byte-identical assets.

## Coordinate glyph templates

`coordinate-glyphs.json` contains 32 binary coordinate glyph masks: two examples
of each of `abcdefgh12345678`, extracted only from the empty tuning boards
`data/tuning/lichess-cburnett-brown-v1/pos-004-{white,black}.png`.
This coordinate asset contains no piece drawings, evaluation pixels or full screenshots.
The asset records input paths, SHA-256 hashes and reviewed integer grid bounds.

The glyphs depict lichess interface coordinate text, not BoardSnap artwork.
Source: the live lichess editor, captured 2026-09-29. The source screenshots'
attribution and upstream terms are recorded in `data/THIRD_PARTY_NOTICES.md` in
the BoardSnap repository. Lila authors' interface is covered by AGPL-3.0-or-later
with exceptions described in https://github.com/lichess-org/lila/blob/master/COPYING.md,
including its font notices. Preserve this provenance when redistributing assets.

Rebuild from the repository root with:

```bash
.venv/bin/python -m tools.build_coordinate_templates
```

The tool fixes source orientations from their known capture views and extracts
bottom file/right rank labels using the same pixel preprocessing as the reader.
At runtime the engine reads this installed asset using `importlib.resources`;
it does not access the repository dataset or infer orientation from filenames.
The two examples account for different backgrounds and subpixel rendering.
Templates and recognition gates were fixed on tuning data before evaluation.

## Additional profile assets

Profile-named `*-pieces.json/png` and `*-coordinates.json` files belong to the
explicit profiles in `boardsnap.profiles`. Digital atlases retain format version
1 and 26 crops. The experimental print atlas uses format version 2: 80 crops,
up to four examples of each class/background, with explicit atlas coordinates.
It uses no coordinate asset; orientation follows White-at-the-bottom convention.
Blue glyph masks also include readable 75% and 125% resizes of the empty tuning
board, to cover coordinate rasterization changes. No evaluation glyph is included.

Rebuild using `python -m tools.build_piece_templates --profile PROFILE_ID` and,
for digital profiles, `python -m tools.build_coordinate_templates --profile PROFILE_ID`.
The book builder is also available as `python -m tools.build_book_templates`.
The same environment produces deterministic assets. Source files are not runtime
inputs and the engine never looks up positions or annotations from the corpus.

Preserve the packaged [third-party notices](THIRD_PARTY_NOTICES.md). Blue uses
lichess/cburnett assets; Chess.com owns the source interface/artwork; book crops
come from the illustrated Gutenberg edition of Edward Lasker's *Chess Strategy*,
translated by J. du Mont. The BoardSnap code license does not relicense these
third-party assets. The book profile is experimental: its frozen reserved report
contains 126/128 correct squares but zero of two exact positions.
