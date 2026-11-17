# Targeted photographic collection

**English** | [Español](../es/targeted-photo-collection.md)

**Pilot and expansion received and reviewed:** 24 photos and 16 screenshots are in `training2`.
Read the [intake review](targeted-photo-intake.md) before collecting more images.
The instructions below preserve the original plan; the review records actual
orientations and backgrounds received.

The initial November 5, 2026 check
found the same 191 registered originals (161 development, 30 validation), with
no new paths, missing files or changed hashes under
`.cache/real-use-tests/phone-photos/`. No training or inference was run. The
[pilot plan](../../data/manifests/photo-targeted-pilot-v1.json) contains collection
targets, not received samples or verified labels.

## Required photographs

Start with **18 photographs of six distinct positions**, plus **12 direct
screenshots**: one clean and one marked reference per position. Camera changes
do not count as new positions. This pilot covers six of the fourteen
[catalogue](photo-catalogue.md) combinations, prioritizing measured gaps.

| Folder | Appearance | Background | Requested view | Focus |
| --- | --- | --- | --- | --- |
| `session-01` | `cc-thin-stem`, Chess.com | Reference purple | White bottom | Thin pawns of both colors, knights and empty squares |
| `session-02` | `cc-thin-stem`, Chess.com | `brown` | Black bottom | Advanced pawns on both square colors |
| `session-03` | `cc-shaded`, Chess.com | Reference wood | White bottom | White rooks, knights, black bishops and queens |
| `session-04` | `cc-shaded`, Chess.com | `brown` | Black bottom | Same piece families on a plain background; color distinctions |
| `session-05` | `lc-rounded-king`, Lichess | Reference wood | White bottom | White king, queens, knights and empty squares |
| `session-06` | `lc-rounded-king`, Lichess | `brown` | Black bottom | Both piece colors and different square backgrounds |

These names describe **visual appearances**, not confirmed official selectors.
Open the [local reference page](../../.cache/phone-targeted-v1/index.html) to see
the photographs to complement. Save a settings screenshot showing the selected
piece set and background. If a style cannot be identified, provide that settings
screenshot first rather than collecting a large batch of unverified similar
artwork. The local page links existing validation photographs; it does not copy
them into training or count them as new data.

Choose new positions with enough pieces and empty squares. Across the two
positions per design, aim for both piece colors on light and dark squares,
especially the pieces in the focus column. One position need not contain every
combination. An editor is suitable when it makes recording the position and
changing marks easier.

## Taking each series

1. Show the complete board without animations, in the requested orientation.
   Save a **clean direct screenshot** as `reference-clean.png`. Cropping or
   rectifying a photograph does not create a direct screenshot.
2. Take `photo-01`: approximately frontal, comfortable distance and diffuse light.
3. Keep pieces, background and orientation unchanged. Take `photo-02` with a
   moderate side angle, slightly different distance and modest lighting variation.
   Keep every corner visible and pieces readable. Record the actual changes.
4. Preserve the geometry, distance and lighting of `photo-02`, adding usual marks:
   last move, selection or legal-move dots; a simple arrow is optional. Save
   `reference-marked.png` and take `photo-03`. Piece placement must remain identical.
   Do not make another move merely to obtain a highlight: use analysis/editor
   controls, or record another series if the pieces change.

Distribute marks over empty and occupied, light and dark squares. Record their
squares or arrow endpoints. Do not obscure pieces completely. Pairs 02/03 compare
marks at similar geometry; 01/02 vary several conditions and cannot isolate the
effect of light or angle. Strong glare or deliberate blur is unnecessary.

## File organization

Six local folders have been prepared:

```text
.cache/phone-targeted-v1/incoming/session-01/
  photos/
    photo-01.jpg
    photo-02.jpg
    photo-03.jpg
  references/
    reference-clean.png
    reference-marked.png
    settings.png
  session.json
```

Repeat through `session-06`. Photo names are suggestions; original camera names
are acceptable. Preserve real extensions: JPG and HEIC originals are accepted,
but **renaming `.HEIC` to `.jpg` does not convert the image**. Keep direct
screenshots in their actual format without recompression.

`session.json` separates the request (`requested`) from observations (`observed`),
which remain empty until collection. Fill it in or provide `notes.txt` with the
selected piece/background settings, orientation, game/video identifier or link,
timestamp and related sessions. A label such as `game-A` suffices to connect
related series; a URL is optional. For editor positions, preserve the placement
or reference FEN in the notes. If unavailable, the direct screenshot can be
transcribed and reviewed later. The internal `piecePlacement` field stores only
piece placement, never all six FEN fields.

Corner annotations are not needed from the user now. They will be reviewed with
pieces and photo/reference correspondence when the pilot arrives. These folders
are a collection area, not a training index. Do not run the generic converter
on the whole directory: it would mix reference screenshots with photographs.
The existing importer will be reused with photographic originals separated and
pairing reviewed.

## Review before expansion

- Verify piece/background identity, position, orientation, complete board and
  exact correspondence to the direct screenshot.
- Annotate corners and observed conditions; separate ambiguous or animated samples.
  Model predictions must not become labels.
- Count all thirteen classes by design and square color, focusing on pawns,
  knight/bishop color and empty squares with texture or marks.
- Check duplicates, position families and source overlap against current
  manifests. A game/video and all its variants remain together. A session folder
  **does not establish** an independent source.
- Keep the intake as development pending assignment; do not randomly split
  photographs or squares. If a source or position overlaps existing validation,
  retain that partition and exclude it from new training. Group uncertain
  provenance conservatively.
- Report usable photo counts and missing classes, backgrounds or conditions
  before deciding the next batch. Eighteen photographs do not guarantee coverage.

Retain existing controls: `video-img_5406` introduced a false black knight on h8;
`video-img_5404` introduced false rook/bishop predictions, not knights. Their
styles do not necessarily match this pilot. New empty-square examples probe
the problem without establishing recovery of those cases. `chesscom-img_5396`
and `5399` remain positive crop controls. Later comparisons will separate
automatic geometry from reviewed corners.

The user has supplied the pilot and white-knight expansion. Corner annotation
is next; the review lists the remaining coverage gaps. The
four conventional catalogue designs retain their existing references; their
expansion and uncollected combinations remain pending. Models, previous splits,
acceptance criteria and final evaluation are unchanged.
