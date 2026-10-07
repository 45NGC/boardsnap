"""BoardSnap: a chessboard recognition engine in development.

Piece placement serialization is available in boardsnap.output.
PNG/JPEG loading and input errors are available in boardsnap.image_input.
First-profile board detection is available in boardsnap.detection.
Board normalization and square crops are available in boardsnap.normalization
and boardsnap.segmentation, with original pixels retained for orientation.
First-profile coordinate reading and canonical cell ordering are available in
boardsnap.orientation, with white-bottom fallback when clues are insufficient.
First-profile template classification is available in boardsnap.classification.
boardsnap.pipeline.recognize_image composes the stages into piecePlacement;
the separate CLI adapter exposes boardsnap image.png and python -m boardsnap.
Flutter integration remains undecided.
"""
