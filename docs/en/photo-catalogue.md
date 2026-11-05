# Initial photographic catalogue

**English** | [Español](../es/photo-catalogue.md)

Step 2 defines **seven target entries and fourteen background combinations**
for improving screen photographs. These are intended targets, not a compatibility
claim or a new evaluation. The structured source is
[photo-catalogue-v1.json](../../data/manifests/photo-catalogue-v1.json), including
references and hashes for the reused reports.

## Selected designs and backgrounds

| Platform | Target design or appearance | Background 1 | Background 2 | Evidence and remaining work |
| --- | --- | --- | --- | --- |
| Lichess | `cburnett` | `brown` | `blue` | Both capture configurations verified; identified photographic pairs pending |
| Lichess | `merida` | `brown` | `blue` | Both capture configurations verified; identified photographic pairs pending |
| Chess.com | `neo` | `green` | `brown` | Both capture configurations verified; identified photographic pairs pending |
| Chess.com | `classic` | `green` | `brown` | Both capture configurations verified; identified photographic pairs pending |
| Chess.com | `cc-thin-stem`: thin-stem pawns | Reference plain purple | `brown` | Identify selector; references `chesscom-img_5401` and `5402` |
| Chess.com | `cc-shaded`: shaded pieces | Reference wood texture | `brown` | Identify selector; references `chesscom-img_5397` and `5398` |
| Lichess | `lc-rounded-king`: rounded king crown | Reference wood texture | `brown` | Identify selector; references `lichess-img_5391` and `5392` |

The first four names come from the [existing capture recipe](../../tools/capture-digital-clean-v1.json).
Each of the eight selected combinations has 200 verified digital captures:
140 training, 30 validation and 30 historical evaluation images. This establishes
capture integrity, **not photographic accuracy**. Current photographs labelled
with visual names such as `cc-classic` or `lc-classic-a` are not mapped to these
themes based on similar names. Current platform defaults are not asserted.

The last three entries are local visual identifiers. The official piece selector
and original background selector remain unresolved: “wood texture” does not
necessarily mean `wood` or `wood4`. Before automating their captures, confirm the
settings and compare all twelve rendered pieces against the references. If an
appearance turns out to match one of the four known designs, merge it while
preserving identifiers and references. Seven entries therefore do not establish
seven different designs.

## Why this group

The four identified designs provide conventional references with working capture
configurations. Repeating two backgrounds per design helps separate piece
appearance from background color. Texture expansion is bounded to the reference
backgrounds of failures we intend to address.

The [error inventory](photo-error-inventory.md) records:

| Appearance | Exact automatic positions | Incorrect squares |
| --- | ---: | ---: |
| `cc-thin-stem` | 0/2 | 18 |
| `cc-shaded` | 0/2 | 5 |
| `lc-rounded-king` | 0/2 | 5 |

These six photographs account for **28/32 automatic square errors** among the
29 detected photographs. They are not 28 independent observations; the count
also excludes the photograph rejected by detection. The aim is to address
observed gaps, without asserting that piece design is their sole cause.

## Deferred coverage

- New photographic batches for Lichess `alpha` and `staunty`, and Chess.com
  `bases` and `alpha`. Existing digital regressions remain in place.
- A third background per design, additional textures and all possible combinations.
- Identification and expansion of the ten other local visual groups listed in
  the manifest. All their photographs remain controls, including failures.
- Native Android/iOS apps, ChessBase and arbitrary video layouts. Taking a photo
  with a phone does not establish compatibility with a native mobile app interface.
- Expansion to crossed arrows, strong glare, severe blur or perspective and
  opaque occlusion. Existing marked and arrow regression cases are retained.
- Book diagrams and physical three-dimensional boards.

A photograph of a video can supply examples of an identified target design;
record its interface and provenance separately. It does not automatically validate
other designs or video layouts. This selection does not revoke existing digital
compatibility either.

## Next collection and checks

1. Identify selectors for the three failing appearances before producing their
   variants. Collection can start with the four known designs.
2. Review **15–20 targeted photographs** before expanding the batch. This is a
   pilot, not a guaranteed accuracy threshold or coverage of all fourteen pairs.
3. Preserve a direct screenshot of the same position, settings, expected placement,
   orientation and game/video provenance for every photograph. The script can
   produce digital references; screen photographs require the phone camera.
4. Include both orientations, complete boards, moderate perspective, clean boards
   and last-move highlights. Cover all thirteen classes on light and dark squares
   per design and record gaps. The first batch need not contain every combination
   of conditions.
5. Group before cropping: the same game, video, position and every background,
   view, screenshot and photographic variant remain in the same partition.
   Existing references retain their groups and splits; consulted validation
   must not be moved into training.
6. Measure results by design and background with reviewed corners and automatic
   detection, while retaining current controls. Compatibility depends on these
   results and acceptance of the next candidate.

This step selects the catalogue and checks consistency against existing reports.
New photographs and their validation remain pending. It does not modify the frozen
`screen-preview-v1` candidate, its models or thresholds, or consult independent
final evaluation data.
