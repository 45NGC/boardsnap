# First clean classification corpus

**English** | [Español](../es/first-clean-corpus.md) · [Overview](README.md)

Steps 6.1 and 6.2 define and collect the first clean corpus for a learned square
classifier. Capture integrity is checked independently of recognition accuracy.
No model, dependency or runtime recognition profile is added by collecting data.

The completed local collection contains **3600 verified PNG/JSON pairs** in 720
batches. The [integrity report](../../data/reports/digital-clean-corpus-v1.json)
records all images and their inherited partitions. This report measures capture
integrity only; no model was trained or evaluated.

## Selected combinations

Each piece set is captured on **all three** listed backgrounds. Background and
piece design remain independent parameters.

| Platform | Piece set (`pieceSet`) | Backgrounds (`boardTheme`) | Role |
| --- | --- | --- | --- |
| Lichess | `cburnett` | `brown`, `blue`, `green` | Retain brown/blue recognition baselines and add another background |
| Lichess | `merida` | `brown`, `blue`, `green` | Extend the verified green/Merida capture |
| Lichess | `alpha` | `brown`, `blue`, `green` | Reuse the purple/Alpha pilot's design on shared backgrounds |
| Chess.com | `neo` | `green`, `brown`, `blue` | Retain the default-green baseline and add other backgrounds |
| Chess.com | `classic` | `green`, `brown`, `blue` | Extend the verified blue/Classic capture |
| Chess.com | `bases` | `green`, `brown`, `blue` | Extend the verified brown/Bases capture |

This gives **six platform-specific piece sets and 18 combinations**. Neo was
identified in the public catalogue by the same `ejgfv` artwork URLs used by the
default-green profile. Each capture verifies actual rendered assets. Capturing
new styles does not promote them to evaluated/compatible recognition profiles.

Backgrounds still affect contrast and appearance. Sharing several backgrounds
across piece designs reduces the opportunity to associate a background with a
particular piece set. These combinations are an initial scope, not the entire
platform catalogue. Textures, marks, arrows and native mobile apps remain later work.

## Positions, sizes and partitions

The [base recipe](../../tools/capture-digital-clean-v1.json) uses all 80 positions
in the frozen [position plan](position-plan.md), all 18 combinations, both views
and a 1280 × 1000 CSS-pixel viewport. Pixel density is 1.

The [collector](../../tools/collect_clean_corpus.py) expands it deterministically:

- `standard`: all 80 positions at 1280 × 1000; **2880 PNGs**.
- `compact`: one position per source group at 1024 × 900; **720 PNGs**.
  Sort groups by ID, then choose position `group_index % 4` from each group's
  four manifest positions. The same 20 positions are used for every style.
- Both sizes use `white-bottom` and `black-bottom`, with `conditions: ["clean"]`.
  The board resizes with the page; its measured bounds are saved for every image.

| Partition | Distinct positions | Standard PNGs | Compact PNGs | Total PNGs |
| --- | ---: | ---: | ---: | ---: |
| Training | 56 | 2016 | 504 | 2520 |
| Validation | 12 | 432 | 108 | 540 |
| Evaluation | 12 | 432 | 108 | 540 |
| Total | 80 | 2880 | 720 | 3600 |

There are still **20 independent source groups**, split 14/3/3. Every variant
inherits its position/group/partition from the frozen manifest. No repartitioning
happens during capture or later square extraction. More screenshots do not mean
more independent positions, and many empty-square crops will be similar.

All combinations occur in every partition. This tests unseen **positions**, not
unseen design/background combinations. Later combination-holdout experiments must
be defined without moving positions between partitions. Final-evaluation labels
may be checked for capture integrity; do not use recognition results on them to
choose the classifier, preprocessing or training parameters.

## Capture and resume

Run from the repository root with the capture extra and Chromium installed (see
[installation and adapters](configurable-capture.md)):

```bash
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/ms-playwright"
# Optional local recipe validation: no browser or downloads
python -m tools.capture_batch capture tools/capture-digital-clean-v1.json --output-root .cache/digital-clean-corpus --validate-only
# Capture, or resume by running this exact command again
python -m tools.collect_clean_corpus --output-root .cache/digital-clean-corpus --report data/reports/digital-clean-corpus-v1.json
# Recheck all local PNG/JSON pairs without opening a browser
python -m tools.collect_clean_corpus --output-root .cache/digital-clean-corpus --report data/reports/digital-clean-corpus-v1.json --audit-only
```

The separate [36-image style check](../../tools/capture-digital-clean-style-check-v1.json)
uses only training position `digital-009`. Its completed local run is under
`.cache/digital-clean-checks/`. It is excluded from the model corpus; it is a tool
check, not 36 additional independent positions.

The collector creates **720 atomic batches**, one per style/size/source group.
Each contains eight standard images or two compact images. The output is:

```text
.cache/digital-clean-corpus/digital-positions-v1/
  clean-<platform>-<background>-<pieces>-<standard|compact>-sequence-NNN/
    batch.json
    <training|validation|evaluation>/<configurationId>/
      digital-NNN-<white-bottom|black-bottom>.png
      digital-NNN-<white-bottom|black-bottom>.json
```

It reuses one page for a fixed style/viewport. Lichess positions change through
the native editor FEN field and flip control; Chess.com uses its board's
`game.load` and flip control. Every image still passes the same before/after DOM
checks. Page reuse and modifications are recorded in provenance; these are
modified automated pages, not untouched real-play screenshots.

Before saving, the adapter verifies actual piece roles/colors/squares,
orientation, computed artwork URLs against the selected style, loaded assets,
complete visible board geometry, absence of marks and stability across the
screenshot. The PNG is decoded and its bounds/dimensions checked. An unavailable
style or a failed position update aborts the group instead of substituting data.

A failed group is discarded and retried with a fresh browser context, up to
three attempts. Earlier completed groups remain. On resume, existing batches
are audited, never silently overwritten: manifest/recipe, expected variants,
partition, recorded rendered rows/orientation, PNG hash, sidecar equality,
dimensions and bounds must all agree. Missing, extra or altered files fail the
run. Use a dedicated output root; unrelated batches are not accepted.

An interrupted process may leave `.capture.lock` and `.capture-*` temporary
folders. Only after confirming no collector is running, remove those temporary
entries, preserving completed `clean-*` batches, and rerun. Do not edit annotations
to bypass a failed check. Corrupt completed batches require investigation and
explicit removal of the affected batch before recapturing.

The completion report is written **only after every expected batch passes**.
It indexes all PNG paths/hashes, identities, configuration IDs, dimensions and
bounds; full provenance/configuration stays in each local sidecar and batch.
The collector returns 0 on success and 1 on failure. Its progress/status text is
separate from the recognition CLI's JSON contract.

Screenshots remain in Git-ignored `.cache/`; committing recipes/code/report does
not back them up. Preserve the verified corpus elsewhere before clearing that
cache, or regenerate it and produce a new report. Sites may change, so recapture
is not guaranteed to reproduce identical PNG bytes.

## Manual captures and next step

**No manual captures are required for this clean batch.** The supplied 20 real-use
screenshots all contain last-move highlights and remain separate detection data.
Before classification use, their placements/provenance need review and the
real-game import schema needs extending. Their reserved evaluation groups must
stay reserved. Actual games, other layouts and native apps will need additional
examples later.

[Square preparation](square-dataset.md) now preserves partitions and audits
class/background/style coverage, with separate verified/detected-bound inputs.
Next train and compare a small model against the existing templates. Data
preparation alone does not establish recognition quality.

Preserve [artwork attribution and terms](../../data/THIRD_PARTY_NOTICES.md).
Alpha has personal/noncommercial-use terms; this experimental collection does
not establish distribution rights for artwork or a future model.
