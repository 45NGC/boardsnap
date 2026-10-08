# Digital style and condition inventory

**English** | [Español](../es/style-inventory.md) · [Overview](README.md)

The [first clean classifier corpus](first-clean-corpus.md) contains 3600 verified
captures: six piece sets on three backgrounds each, both orientations and two
viewport sizes. Its 80 positions retain the frozen training/validation/evaluation
split. The separate 36-image style check is excluded. Model training remains pending.

Inventory v1, reviewed **2026-10-07**. This is the finite expansion backlog for
Lichess and Chess.com. Book diagrams are deferred. Adding a row records work to
do; it does not add a recognition profile or establish support.

The three existing digital combinations are **evaluated pilots**. None is
promoted here to broad release compatibility: each has four reserved screenshots
of just two independent positions, shared across the three profiles.

## Three independent dimensions

| Dimension | Record separately | Recognition responsibility |
| --- | --- | --- |
| Board background | Platform, local style ID, upstream name, artwork version/hash, flat colors or texture | Detection and background handling |
| Piece design | Platform, local style ID, upstream name, artwork version/hash, twelve visible symbols | Thirteen-class classification, including empty |
| Interface layout | Screen/page, client, version, viewport, pixel ratio, UI light/dark mode, coordinates, board bounds | Finding the board among UI elements and reading orientation clues |

A page's background outside the grid belongs to the **interface**, not the board
background. A site's named “theme” may bundle all three dimensions. Identical
display names on different platforms do not establish identical artwork.

The unit of compatibility is an explicit **board + pieces + layout/client +
conditions** combination. Evaluating one component does not establish support for
its Cartesian product with the other components. The tables below organize data
collection; their E entries refer only to C01–C03.

Existing `Profile` objects in `src/boardsnap/profiles.py` still bundle runtime
settings. This milestone separates the inventory and future annotation fields;
it does not expose arbitrary combinations through the Python API or CLI.
`--profile` and the output contract remain unchanged.

## Status and promotion rules

| Code | Status | Evidence required |
| --- | --- | --- |
| P | Pending capture | Named target; no annotated corpus covering this exact scope. Confirm availability/artwork before collection. |
| D | In development | Versioned, annotated samples and fixed source-group partitions exist; implementation or validation is unfinished. |
| E | Evaluated | Frozen implementation tested on reserved data, with a linked report including failures and full-position results. Evaluation may fail. |
| C | Compatible | E plus the predeclared release acceptance criteria have passed for the explicitly listed combinations, clients and conditions. |

No table currently claims C. “Pending” for Android/iOS means there is no BoardSnap
capture evidence; it does **not** assert that a theme is available in that app.
A capture script, a rendered example or a passing unit test alone does not make
a style E or C. Development of the capture tooling alone does not make a row D.

Before promoting an evaluated combination to C, record an acceptance plan with
the number of **independent positions**, image sizes, conditions, client versions,
exact-position target, board-bound tolerance and negative-image target. Freeze
these choices before final evaluation. Passing the existing four-image pilots is
not sufficient. Report detection failures in the full-pipeline denominator,
accuracy by class/background, exact `piecePlacement` matches and processing time.
Keep a separate result per condition so clean boards cannot hide failures with
arrows. Compatibility describes the measured scope, not guaranteed perfection.

## Source snapshot and bounded scope

- Lichess: the public [2D board registry](https://github.com/lichess-org/lila/blob/master/modules/pref/src/main/Theme.scala)
  and [2D piece registry](https://github.com/lichess-org/lila/blob/master/modules/pref/src/main/PieceSet.scala)
  were consulted on the review date. The snapshot below includes 25 board names
  and 41 visible piece designs; `disguised` is excluded below. These upstream
  branches can change; this table changes only through an explicit inventory update.
- Chess.com: [board examples](https://www.chess.com/article/view/what-your-chess-board-theme-says-about-you)
  and [piece examples](https://www.chess.com/article/view/what-your-chess-piece-style-says-about-you)
  published in 2022 provide names for a **selected initial backlog**, not a complete
  current catalogue. The public settings link redirected to login during review;
  current selection/availability must be verified when capturing. The existing
  capture annotations establish artwork IDs `9rdwe` and `ejgfv`, not a verified
  mapping from that piece asset to the selector label “Neo”.
- Chess.com's [customization guide](https://support.chess.com/en/articles/8594320-how-do-i-change-my-background-board-and-pieces)
  distinguishes web/mobile settings and temporary special themes. Mobile clients
  need independent screenshots; even shared source artwork does not verify their
  layout, scaling or coordinate rendering.

G1 is the first collection group: flat backgrounds and conventional 2D pieces.
G2 is the later group: textures, more distinctive drawings and remaining designs
whose appearance needs inspection. These are **planning priorities**, not measured
difficulty or an assertion that every G2 background is textured.

This version has **88 component rows**: 25 Lichess backgrounds, 41 Lichess piece
sets, 11 Chess.com backgrounds and 11 Chess.com piece entries (including the pinned
default whose alias remains to be confirmed). It is not 88 supported profiles.
If Neo is confirmed to be the pinned default, merge the alias with evidence
instead of treating it as new coverage. Additional Chess.com selector entries
require a new inventory revision; “every current or future theme” is not the
completion criterion for v1.

## Board backgrounds

The Web column concerns the limited desktop capture layouts C01–C03 only.
Mobile browser status is separate in the layout table.

### Lichess

| Upstream board name | Group | Web | Android app | iOS app |
| --- | --- | --- | --- | --- |
| `brown` | G1 | E (C01) | P | P |
| `wood` | G2 | P | P | P |
| `wood2` | G2 | P | P | P |
| `wood3` | G2 | P | P | P |
| `wood4` | G2 | P | P | P |
| `maple` | G2 | P | P | P |
| `maple2` | G2 | P | P | P |
| `horsey` | G2 | P | P | P |
| `leather` | G2 | P | P | P |
| `blue` | G1 | E (C02) | P | P |
| `blue2` | G2 | P | P | P |
| `blue3` | G2 | P | P | P |
| `canvas` | G2 | P | P | P |
| `blue-marble` | G2 | P | P | P |
| `ic` | G2 | P | P | P |
| `green` | G1 | P | P | P |
| `marble` | G2 | P | P | P |
| `green-plastic` | G2 | P | P | P |
| `olive` | G2 | P | P | P |
| `grey` | G2 | P | P | P |
| `metal` | G2 | P | P | P |
| `newspaper` | G2 | P | P | P |
| `purple` | G1 | P | P | P |
| `purple-diag` | G2 | P | P | P |
| `pink` | G2 | P | P | P |

### Chess.com

Names below are catalogue candidates except the pinned captured Green asset.
An artwork change under the same name needs a new version and evaluation.

| Board name / pinned asset | Group | Web | Android app | iOS app |
| --- | --- | --- | --- | --- |
| Green (`9rdwe`) | G1 | E (C03) | P | P |
| Brown | G1 | P | P | P |
| Blue | G1 | P | P | P |
| Dark Wood | G2 | P | P | P |
| Walnut | G2 | P | P | P |
| Icy Sea | G2 | P | P | P |
| Tournament | G2 | P | P | P |
| Bubblegum | G2 | P | P | P |
| Marble | G2 | P | P | P |
| Glass | G2 | P | P | P |
| Lolz | G2 | P | P | P |

## Piece designs

All classes must be sampled on both light and dark squares. Names such as Alpha
or Wood on two platforms are separate targets until artwork equivalence is
verified, and equivalence alone does not transfer full-pipeline compatibility.

### Lichess

| Upstream piece name | Group | Web | Android app | iOS app |
| --- | --- | --- | --- | --- |
| `cburnett` | G1 | E (C01, C02) | P | P |
| `merida` | G1 | P | P | P |
| `alpha` | G1 | P | P | P |
| `pirouetti` | G2 | P | P | P |
| `chessnut` | G2 | P | P | P |
| `chess7` | G2 | P | P | P |
| `reillycraig` | G2 | P | P | P |
| `companion` | G2 | P | P | P |
| `riohacha` | G2 | P | P | P |
| `kosal` | G2 | P | P | P |
| `leipzig` | G2 | P | P | P |
| `fantasy` | G2 | P | P | P |
| `spatial` | G2 | P | P | P |
| `celtic` | G2 | P | P | P |
| `california` | G2 | P | P | P |
| `caliente` | G2 | P | P | P |
| `pixel` | G2 | P | P | P |
| `firi` | G2 | P | P | P |
| `rhosgfx` | G2 | P | P | P |
| `maestro` | G2 | P | P | P |
| `fresca` | G2 | P | P | P |
| `cardinal` | G2 | P | P | P |
| `gioco` | G2 | P | P | P |
| `tatiana` | G2 | P | P | P |
| `staunty` | G2 | P | P | P |
| `cooke` | G2 | P | P | P |
| `monarchy` | G2 | P | P | P |
| `papercut` | G2 | P | P | P |
| `minimal-warmth` | G2 | P | P | P |
| `governor` | G2 | P | P | P |
| `dubrovny` | G2 | P | P | P |
| `shahi-ivory-brown` | G2 | P | P | P |
| `icpieces` | G2 | P | P | P |
| `mpchess` | G2 | P | P | P |
| `kiwen-suwi` | G2 | P | P | P |
| `totoy` | G2 | P | P | P |
| `horsey` | G2 | P | P | P |
| `anarcandy` | G2 | P | P | P |
| `xkcd` | G2 | P | P | P |
| `shapes` | G2 | P | P | P |
| `letter` | G2 | P | P | P |

### Chess.com

| Piece name / pinned asset | Group | Web | Android app | iOS app |
| --- | --- | --- | --- | --- |
| Captured default (`ejgfv`) | G1 | E (C03) | P | P |
| Neo | G1 | P | P | P |
| Classic | G1 | P | P | P |
| Bases | G1 | P | P | P |
| Alpha | G1 | P | P | P |
| Icy Sea | G1 | P | P | P |
| Wood | G2 | P | P | P |
| Neo-Wood | G2 | P | P | P |
| Glass | G2 | P | P | P |
| Game Room | G2 | P | P | P |
| Marble | G2 | P | P | P |

## Interface and client targets

Stable layout IDs below are inventory identifiers, not implemented CLI options.
The unqualified word “web” must not include all browsers, screen sizes or pages.

| Layout ID | Platform / client / screen | State | Evidence or remaining work |
| --- | --- | --- | --- |
| LC01 | Lichess, desktop Chromium, editor | E | C01, C02; 1280 × 1000 viewport, pixel ratio 1, 584 px grid; capture tool hides FEN/URL inputs and resize handle |
| LC02 | Lichess, desktop browser, analysis/study | P | Capture both screen variants separately with sidebar and evaluation panel |
| LC03 | Lichess, desktop browser, game | P | Capture clocks, player panels and move list |
| LC04 | Lichess, mobile browser | P | Android Chrome and iOS Safari; portrait and landscape captured separately |
| LC05 | Lichess, native Android app | P | Record app/version, device and OS; game and analysis screens |
| LC06 | Lichess, native iOS app | P | Record app/version, device and OS; game and analysis screens |
| CC01 | Chess.com, desktop Chromium, analysis | E | Recognition combination C03; 1280 × 1000 viewport, 704 px grid; capture hides arrows, highlights, evaluation bar and inputs |
| CC02 | Chess.com, desktop browser, game | P | Capture clocks, player panels and move list |
| CC03 | Chess.com, desktop browser, review/puzzles | P | Capture both screen variants separately, including review annotations |
| CC04 | Chess.com, mobile browser | P | Android Chrome and iOS Safari; portrait and landscape captured separately |
| CC05 | Chess.com, native Android app | P | Record app/version, device and OS; game and analysis screens |
| CC06 | Chess.com, native iOS app | P | Record app/version, device and OS; game and analysis screens |

LC/CC identify layouts; C01–C03 below identify evaluated recognition combinations.
The current browser is Chromium 153.0.8010.12 in the committed annotations.
For each desktop layout, Firefox and Safari verification remains P. Emulating a
mobile viewport in Chromium is development data, not native Android/iOS evidence.
A plain crop of a desktop board is not mobile evidence either.

## Existing evaluated combinations

Only these three combinations have digital recognition evidence today.
“Clean” means static pieces, complete aligned grid, no arrows/highlights and no
obstruction. Both views are present; the profile is selected explicitly.

| ID | Board | Pieces | Layout | Runtime profile | State | Reserved result |
| --- | --- | --- | --- | --- | --- | --- |
| C01 | Lichess brown | cburnett | LC01 | `lichess-cburnett-brown-v1` | E | 4/4 positions, 256/256 squares |
| C02 | Lichess blue | cburnett | LC01 | `lichess-cburnett-blue-v1` | E | 4/4 positions, 256/256 squares |
| C03 | Chess.com Green `9rdwe` | captured `ejgfv` | CC01 | `chesscom-default-green-v1` | E | 4/4 positions, 256/256 squares |

Evidence: [brown report](../../data/reports/lichess-cburnett-brown-v1-classification-evaluation.json),
[blue report](../../data/reports/lichess-cburnett-blue-v1-classification-evaluation.json),
[Chess.com report](../../data/reports/chesscom-default-green-v1-classification-evaluation.json)
and the corresponding [profile limitations](profiles.md).
All three reuse the same two held-out position groups. The empty Chess.com tuning
board was produced by explicitly removing DOM pieces; its provenance does not
demonstrate a native empty-board UI.

## Conditions to evaluate independently

States refer to the **digital combinations above**, not every inventoried style.
“D” below means bounded regression cases already exist; broader captured evidence
is still missing. No new condition is marked compatible by this document.

| ID | Condition | State | Required coverage / existing evidence |
| --- | --- | --- | --- |
| K01 | Clean, complete, aligned PNG | E | Existing C01–C03 reports, original sizes only |
| K02 | White/Black at bottom, explicit orientation | D | Asymmetric-position regression on all three profiles; extend across new styles/layouts |
| K03 | Coordinates present / absent / contradictory | D | Existing automatic/explicit precedence tests, including edited tuning images; capture natural examples |
| K04 | Board-only crop / translated board / extra UI margins | D | Existing synthetic geometry regressions; independent captures needed |
| K05 | Size, browser zoom, device pixel ratio | D | 75%/125% tuning resizes exist; collect native 256/384/512/768 px grids and pixel ratios 1/2/3 where feasible |
| K06 | JPEG / recompressed shared image | P | RGB decoding is implemented, but no representative end-to-end compression evaluation; start with quality 95/80/60 |
| K07 | Light/dark UI and surrounding panels | P | Test detection against similar UI colors, both UI modes and layout variants |
| K08 | Last-move highlighted squares | P | Origin/destination, light/dark squares, occupied and empty |
| K09 | Selected square and legal-move markers | P | Dots/rings, occupied capture targets, both piece colors |
| K10 | Check and premove highlights | P | Different colors/opacity, highlighted king and other occupied squares |
| K11 | User-drawn arrows and circles | P | Different colors, thicknesses, crossings, empty squares and pieces |
| K12 | Engine arrows and move-quality badges | P | Single/multiple arrows, labels touching pieces and grid borders |
| K13 | Combined overlays | P | Explicit cases: last-move + arrow; selection + move markers; check + arrow; review badge + engine arrow |
| K14 | Negative and ambiguous images | D | Blank/striped/board-free and multiple-grid regressions exist; add real UI without a board, lookalike tables, partial boards |

Capture values in K05/K06 are planned test points, not supported ranges.
Test overlays on full screenshots **before** square extraction and keep clean
and annotated variants of the same position in the same partition. A test of
an arrow across empty squares is not evidence for an arrow obscuring a piece.
Where a symbol is fully hidden or visually indistinguishable, the image may not
contain enough information for exact recovery; never repair it by inventing
legality, side to move or extra FEN fields.

## Ordered work batches

The [80-position plan](position-plan.md) now fixes source-group partitions and
label coverage for the first batch below. Its images still need to be captured;
inventory recognition states are unchanged.

1. **Expand evidence for C01–C03.** Gather independent positions covering all
   thirteen classes on both backgrounds, both views and clean geometry; establish
   the release acceptance plan before opening new held-out images.
2. **G1 backgrounds with fixed pieces.** Lichess green and purple with cburnett;
   Chess.com Brown and Blue with the verified default artwork. Fix the existing
   desktop layout and clean PNG condition while varying the background.
3. **G1 pieces with a fixed background.** Lichess merida then alpha on brown;
   Chess.com verify the Neo alias, then Classic, Bases, Alpha and Icy Sea on Green.
   Capture diagnostic positions and real independent positions for each.
4. **G1 combinations and clients.** Test cross-combinations before declaring them.
   Extend to game/analysis layouts, mobile browser, native Android, then native
   iOS. Record a separate result for every claimed combination/client.
5. **Conditions K05–K13.** First sizes/compression/UI modes, then highlighted
   squares, move markers/check/premove, arrows/circles, review overlays and the
   four named mixed cases. Freeze exact coverage instead of “any overlay”.
6. **G2.** Work through the remaining named backgrounds and piece sets in table
   order, validating appearance and availability first. Start with one reference
   partner for each component, then evaluate the exact combinations to release.

One-component experiments keep collection manageable. They do not prove that
every pair works. A group is complete only when the release manifest enumerates
its supported combinations and every claimed cell passes its acceptance plan.
Entries that cannot be obtained or interpreted must be explicitly removed/deferred
with a reason in a new revision, rather than silently counted as supported.

## Annotation and maintenance checklist

For each new collection, record these fields separately in its versioned manifest
(the following are **proposed metadata**, not fields accepted by today's tools):

- `platform`, `boardStyleId`, `pieceStyleId`, `layoutId` and pinned artwork hashes.
- Client type (`desktop-web`, `mobile-web`, `android-app`, `ios-app`), browser/app
  version, OS, viewport/image dimensions, pixel ratio and UI mode.
- Condition IDs plus exact overlay colors/opacity/geometry, scaling and compression.
- Source URL/date, image hash, source group, partition, expected `piecePlacement`,
  image orientation and independently checked board bounds.
- Capture availability/source, source attribution, report path, tested code/assets
  revision, failure count and date of each state transition.

Keep every position and its crops, views, overlays, themes and compression
variants together across partitions. Learned models will additionally need a
validation split, separate from final evaluation. New external artwork must be
documented in [source notices](../../data/THIRD_PARTY_NOTICES.md).

To update a state, edit this document and its Spanish counterpart together, link
the evidence, preserve prior regression reports, and retain the stable identifiers.
No HTTP/Flutter integration, new theme recognition, PyTorch dependency or expanded
capture implementation is introduced by this inventory.

## Excluded from inventory v1

Physical 3D boards, perspective/3D rendering modes, animations during piece
movement, hidden/blindfold pieces (including Lichess `disguised`), transient event
themes, arbitrary user CSS/custom uploaded board artwork and book diagrams.
Unknown future catalogue entries require an explicit scope revision. This boundary
does not remove the existing experimental book profile; that work is simply deferred.
