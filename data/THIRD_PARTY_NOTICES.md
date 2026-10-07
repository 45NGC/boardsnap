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
