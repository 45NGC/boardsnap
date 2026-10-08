# Screenshot source and artwork notices

The `lichess-cburnett-brown-v1` dataset contains captures of the live
[lichess board editor](https://lichess.org/editor), made with Playwright on
2026-09-29. Positions were selected or constructed for BoardSnap. Screenshots
were adopted without pixel changes on 2026-09-30. Capture-time CSS hid the
FEN/URL fields and resize handle; the surrounding editor remains visible.

Upstream attribution and licensing are documented in
[Lila's copying notice](https://github.com/lichess-org/lila/blob/master/COPYING.md)
(consulted 2026-09-30):

| Component | Attribution | Upstream terms |
| --- | --- | --- |
| Lila interface and unexcepted files | Lila authors | AGPL-3.0-or-later |
| Board images | Lila authors and pirouetti | AGPL-3.0-or-later |
| cburnett pieces | Colin M. L. Burnett | GPL-2.0-or-later |

Sources: [Lila](https://github.com/lichess-org/lila),
[board assets](https://github.com/lichess-org/lila/tree/master/public/images/board),
[cburnett SVGs](https://github.com/lichess-org/lila/tree/master/public/piece/cburnett).
The upstream notice also lists font/icon exceptions and limits logo use to
referring to lichess.org. The visible site identity here identifies the source.
These screenshots are not original BoardSnap artwork; the repository license
does not replace the upstream component terms. Preserve this notice with the
dataset and consult the linked upstream notices when redistributing it.

The packaged [coordinate glyph masks](../src/boardsnap/assets/README.md) are
derived from the two empty tuning captures (`pos-004`), not from evaluation
images. They contain only coordinate text silhouettes. Their package asset
records source hashes and preserves this source attribution and font-notice
reference; they are not original BoardSnap artwork.

The same asset directory now includes a 26-crop piece atlas derived only from
the tuning split. These crops include cburnett artwork by Colin M. L. Burnett
(GPL-2.0-or-later) and the brown board background (AGPL-3.0-or-later), with the
upstream terms above preserved. `piece-templates.json` records exact source
hashes and square coordinates; no reserved evaluation image supplied a template.

## Additional profiles collected on 2026-10-07

`lichess-cburnett-blue-v1` uses the live lichess editor with its blue preference,
with the same cburnett artwork and upstream terms described above. Captures were
not recolored from the brown dataset. Its piece atlas and coordinate masks are
derived solely from its tuning partition.

`chesscom-default-green-v1` contains screenshots of the public
[Chess.com analysis board](https://www.chess.com/analysis) and derived square/text
templates. Chess.com is the source of its site interface and chess artwork; these
are not original BoardSnap assets. The captured board asset is
[9rdwe/200.png](https://assets-themes.chess.com/image/9rdwe/200.png); piece assets use
`https://assets-themes.chess.com/image/ejgfv/150/{piece}.png`. Individual source
URLs and capture modifications are recorded in the sidecars. No open-source
license grant for these assets is asserted here. The BoardSnap code license does
not relicense the third-party screenshots or artwork. Consult the source's
[terms](https://www.chess.com/legal/user-agreement) for reuse and distribution.
The empty tuning board is explicitly a calibration DOM modification, not an
unaltered live empty position.

`book-strategy-hatched-v1` contains diagrams 1, 3, 4, 5, 6, 7 and 8 from the
[illustrated Project Gutenberg edition of Chess Strategy](https://www.gutenberg.org/cache/epub/5614/pg5614-images.html),
by Edward Lasker, translated by J. du Mont. The edition credits John Mamoun,
Charles Franks and the Online Distributed Proofreaders. The
[catalog entry](https://www.gutenberg.org/ebooks/5614) identifies the edition as
public domain in the USA; this notice does not assert worldwide public-domain
status. Preserve the source's [license and terms](https://www.gutenberg.org/policy/license.html).
The downloaded JPEG pixels were decoded to RGB and stored as PNG without
redrawing, recoloring or geometric correction. Sidecars record original URLs
and hashes. The book atlas contains crops only from tuning diagrams 1, 4, 5, 6
and 8. Reserved diagrams 3 and 7 supplied no templates.

## Detection-only corpus: digital-detection-v1

`data/detection/development/` and `tests/fixtures/detection/held-out/` add 28
original PNGs for rectangle tests. The detection manifest records their hashes,
original local paths, source groups and conditions. Twenty images were supplied
by the project owner as real-use Lichess/Chess.com screenshots; exact game URLs,
FEN/PGN, capture dates and named appearance settings were not supplied. Their
pixels are preserved, including visible interface fragments and annotations.
Eight more images come from the configurable automated pilot: Lichess
green/Merida and purple/Alpha, Chess.com blue/Classic and brown/Bases. Their
capture URLs, asset URLs and page modifications are preserved in the manifest.

In addition to the earlier Lichess notices, the upstream
[copying notice](https://github.com/lichess-org/lila/blob/master/COPYING.md)
identifies Merida by Armando Hernandez Marroquin under GPL-2.0-or-later, and Alpha
by Eric Bentzen with personal, noncommercial-use terms. Alpha is listed as a
non-free exception; neither this repository's license nor inclusion in a test
fixture grants broader artwork rights. Board and interface notices above still
apply. The Chess.com images retain the same third-party status described above;
no open-source license grant is asserted for Classic/Bases or user screenshots.

These images are detection references, not newly licensed BoardSnap artwork.
They supply no piece-training templates or verified position labels. Preserve
these notices when using the corpus and review upstream terms for redistribution.
