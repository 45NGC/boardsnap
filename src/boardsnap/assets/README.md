# Coordinate glyph templates

`coordinate-glyphs.json` contains 32 binary coordinate glyph masks: two examples
of each of `abcdefgh12345678`, extracted only from the empty tuning boards
`data/tuning/lichess-cburnett-brown-v1/pos-004-{white,black}.png`.
No piece drawings, evaluation pixels or full screenshots are included.
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
