# First photographic classifier

**English** | [Español](../es/phone-training.md)

The first photographic fine-tuning run is complete. Its experimental weights are
`.cache/neural-phone-v1/best.pt`. They **do not replace** the digital candidate at
`.cache/neural-tolerance-v1-conservative/best.pt`; v8 is also unchanged.
The subsequent [photographic detector](photo-detection.md) implements automatic
four-corner localization separately; its integration with recognition is pending.
The subsequent [classifier diagnosis](phone-classifier-analysis.md) completes
the class, appearance and condition breakdown using these same saved predictions.

## Data and selection

The existing [reviewed dataset](phone-training-data.md) supplies 160 training
photos (10,240 squares) and 30 validation photos (1,920 squares). No photographs
were recropped, repartitioned or added. Final evaluation was not accessed.
Source separation remains user-confirmed, with the documented provenance limits.
The position-family check found no overlap between photographic training and
digital validation, or photographic validation and digital training, in the
digital-style-squares-v2 corpus. This does not prove unknown source independence.

The run starts from the tolerance candidate and uses the existing deterministic
CPU trainer with a fresh AdamW optimizer. The [configuration](../../tools/train-phone-v1.json)
fixes seed 20261030, 20 epochs, batch size 256, learning rate 0.0001, weight decay
0.0001 and four threads. Inverse-frequency loss weights use training labels only.
There is no augmentation or digital replay in this initial photo-only pilot.

Selection prioritizes validation exact boards, then macro recall and loss.
**Epoch 1 was selected**; subsequent epochs did not improve validation. `best.pt`
contains that selected state; `last.pt` is a resumable checkpoint, not the model
to use for inference. More epochs alone are not supported by these results.

## Measured results

Both models receive identical crops from reviewed boundaries. These are
classification measurements, **not full-image photographic detection results**.

| Validation corpus | Digital reference | Photo v1 |
| --- | ---: | ---: |
| Photographs: exact boards | 18/30 | 19/30 |
| Photographs: correct squares | 1,863/1,920 (97.03%) | 1,871/1,920 (97.45%) |
| Digital: exact boards | 3,131/3,132 | 3,128/3,132 |
| Digital: correct squares | 200,447/200,448 | 200,444/200,448 |

Photo v1 recovers `chesscom-img_5400` without losing any previously correct photo.
It still fails 11 complete photo positions: seven Chess.com, two Lichess and two
video photos. Exact-board results by category are 3/10, 8/10 and 8/10 respectively.
Three digital boards regress: two clean Chess.com bases/brown variants and a
Lichess staunty/brown combined-arrow variant. Do not set this artifact as a shared
replacement merely because its photo score improved.

The [versioned report](../../data/reports/neural-phone-v1.json) retains training
history, hashes, class precision/recall, confusion matrices, category/condition
results, paired gains/losses and the 49 remaining photo square errors. Full local
comparison records are in `.cache/neural-phone-v1/{phone,digital}-validation.json`.
No decision was based on a final reserved evaluation.

On this CPU, the photo model's warm 64-square classification median was about
1.41 ms on photos and 1.59 ms on digital crops, excluding decoding, rectification
and detection. Peak comparison-process RSS was about 330 MiB and 1,196 MiB;
these figures include both models, imports and indexes, not just model memory.
They are not mobile performance measurements.

## Try a new image

From the repository root with `.venv` activated, the existing automatic CLI can
use the experimental model explicitly:

```bash
boardsnap "my-photo.jpg" --model .cache/neural-phone-v1/best.pt --orientation white-bottom
```

This still uses the **digital detector**. A `BOARD_NOT_FOUND` result on a tilted
photograph does not test the new classifier. The camera input must be PNG/JPEG;
export HEIC to JPEG first. Use `black-bottom` when appropriate.

To test classification independently, use the development helper with manual
board corners, measured on the full image after EXIF orientation:

```bash
python -m tools.recognize_photo "my-photo.jpg" --model .cache/neural-phone-v1/best.pt --orientation white-bottom --corners 120 80 900 100 920 880 100 900
```

**Those coordinates are an example; replace all eight numbers for your image.**
Order: top-left, top-right, bottom-right, bottom-left, each as x y. Mark the grid
boundaries, excluding the frame/coordinates. The helper corrects perspective and
uses the same preprocessing as training. It does not infer corners or consult labels.

Alternatively, supply an already perspective-corrected square board with no margins:

```bash
python -m tools.recognize_photo "rectified-board.png" --model .cache/neural-phone-v1/best.pt --orientation white-bottom --rectified
```

A square crop of a tilted board is not a rectified board. This option asserts
that the input contains exactly the complete grid, at least 128 pixels per side.
Both helper modes return only `piecePlacement`, or structured input/model/geometry
errors. Invocation errors use exit code 2; processing errors use 1; success uses 0.

## Reproduce and next steps

The completed run already exists; do not rerun it just to use its model. For an
intentional reproduction, choose a fresh run directory:

```bash
python -m tools.train_neural --dataset .cache/phone-training-v1 --run .cache/neural-phone-v1-reproduction --config tools/train-phone-v1.json --initialize-from .cache/neural-tolerance-v1-conservative/best.pt
python -m tools.compare_validation --dataset .cache/phone-training-v1 --baseline .cache/neural-tolerance-v1-conservative/best.pt --candidate .cache/neural-phone-v1/best.pt --output .cache/phone-validation-recheck.json
python -m tools.compare_validation --dataset .cache/digital-style-squares-v2 --baseline .cache/neural-tolerance-v1-conservative/best.pt --candidate .cache/neural-phone-v1/best.pt --output .cache/digital-validation-recheck.json
python -m pytest tests/test_phone_inference.py tests/test_neural.py tests/test_phone_training_dataset.py tests/test_phone_squares.py tests/test_phone_geometry.py -q
```

The 71 targeted tests pass; manual-corner inference also matches known placements
through actual CLI subprocesses in both orientations. Next, inspect the remaining
photographic style errors and consider audited digital replay before training a
shared replacement. The [photographic localization pilot](photo-detection.md) is now
measured; its integration with recognition and independent final acceptance remain
pending. Keep collecting new trials as development
data once their results have been inspected.
