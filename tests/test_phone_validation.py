"""Annotation checks do not need local photographs or a trained model."""

import copy
import json

import pytest

from tools.prepare_phone_photos import ROOT
from tools.review_phone_validation import audit, export_gallery


@pytest.fixture
def corpus():
    data = json.loads((ROOT / "data/manifests/phone-validation-v1.json").read_text())
    development = json.loads((ROOT / data["referenceDevelopmentManifest"]).read_text())
    return data, development


def test_reviewed_validation_corpus(corpus):
    data, development = corpus
    report = audit(data, development, verify_files=False)
    assert report["reviewedPlacements"] == report["reviewedCornerAnnotations"] == 30
    assert report["distinctPlacements"] == 30
    assert report["labeledSquares"] == 1920
    assert report["orientations"] == {"white-bottom": 22, "black-bottom": 8}
    assert report["allClassesOnBothBackgrounds"]
    assert report["readyForSquareExport"] and not report["readyForValidation"]
    assert report["developmentPositionFamilyOverlaps"] == []


@pytest.mark.parametrize("change,match", [
    ("orientation", "orientation disagree"),
    ("corner", "stale rectified review"),
    ("missing_review", "stale rectified review"),
    ("source", "stale visual transcription"),
    ("split", "remain together"),
    ("group", "remain together"),
    ("duplicate", "Duplicate photo"),
    ("reference", "reference changed"),
])
def test_unsafe_annotation_changes_are_rejected(corpus, change, match):
    data, development = corpus
    row = data["samples"][0]
    if change == "orientation":
        row["label"]["orientation"] = "black-bottom"
    elif change == "corner":
        row["boardCorners"][0][0] += 1
    elif change == "missing_review":
        del row["label"]["rectifiedReview"]
    elif change == "source":
        row["label"]["sourceSha256"] = "0" * 64
    elif change == "split":
        row["split"] = "training"
    elif change == "group":
        row["groupId"] = "unrelated-new-group"
    elif change == "duplicate":
        data["samples"].append(copy.deepcopy(row))
    else:
        data["referenceDevelopmentManifestSha256"] = "0" * 64
    with pytest.raises(ValueError, match=match):
        audit(data, development, verify_files=False)


def test_copied_development_position_is_rejected(corpus):
    data, development = corpus
    row = data["samples"][0]
    placement = development["samples"][0]["label"]["piecePlacement"]
    row["label"]["piecePlacement"] = row["label"]["visualRows"] = placement
    row["label"]["rectifiedReview"]["piecePlacement"] = placement
    with pytest.raises(ValueError, match="Position family overlaps"):
        audit(data, development, verify_files=False)


def test_known_development_game_is_rejected(corpus):
    data, development = corpus
    game = next(r["source"]["gameId"] for r in development["samples"] if r["source"].get("gameId"))
    data["samples"][0]["source"]["gameId"] = game
    with pytest.raises(ValueError, match="Known game overlaps"):
        audit(data, development, verify_files=False)


def test_gallery_cannot_overwrite_source_directory(corpus):
    data, _ = corpus
    with pytest.raises(ValueError, match="separate from source"):
        export_gallery(data, ROOT / data["samples"][0]["imagePath"])
