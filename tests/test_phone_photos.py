"""Photographic intake preserves sources and never invents training labels."""

import json
from pathlib import Path

from PIL import Image
import pytest

from tools.prepare_phone_photos import audit, decode_photo, digest, prepare, write_review_index

pytestmark = pytest.mark.unit


def make_corpus(tmp_path):
    source = tmp_path / "originals" / "lichess-photos"
    source.mkdir(parents=True)
    image = Image.new("RGB", (80, 40), "white")
    image.paste("black", (0, 0, 40, 20))
    exif = Image.Exif()
    exif[274] = 6
    exif[272] = "test-camera"
    image.save(source / "one.jpg", exif=exif)
    return source.parent


def test_intake_rotates_once_preserves_original_and_leaves_labels_pending(tmp_path):
    source = make_corpus(tmp_path)
    original = source / "lichess-photos/one.jpg"
    before = original.read_bytes()
    data = prepare(source, tmp_path / "review", tmp_path / "manifest.json", root=tmp_path)
    row = data["samples"][0]
    assert original.read_bytes() == before
    assert row["imageSize"] == [40, 80]
    assert row["captureMetadata"]["originalOrientation"] == 6
    assert row["source"]["referenceScreenshot"] is None
    assert row["label"]["piecePlacement"] is None
    with Image.open(tmp_path / row["imagePath"]) as converted:
        assert converted.getpixel((30, 10))[0] < 30
        assert converted.getpixel((10, 10))[0] > 220
        assert not converted.getexif()
        assert converted.info["icc_profile"]
    report = audit(data, root=tmp_path)
    assert report["readyForTraining"] is False
    assert sum(sum(v.values()) for v in report["transcribedClassBackgroundCounts"].values()) == 0
    assert report["splitCounts"] == {"development": 1, "training": 0, "validation": 0, "evaluation": 0}
    assert json.loads((tmp_path / "manifest.json").read_text()) == data
    assert "one.jpg" in (tmp_path / "review/index.html").read_text()


def test_duplicate_files_are_counted_but_kept_in_same_partition(tmp_path):
    source = make_corpus(tmp_path)
    (source / "lichess-photos/two.jpg").write_bytes((source / "lichess-photos/one.jpg").read_bytes())
    data = prepare(source, tmp_path / "review", tmp_path / "manifest.json", root=tmp_path)
    assert audit(data, root=tmp_path)["exactDuplicateOriginals"] == 1
    assert len({r["groupId"] for r in data["samples"]}) == 1
    assert len({r["id"] for r in data["samples"]}) == 2


@pytest.mark.parametrize("change", ["original", "derived", "split", "group", "prediction", "pending-label", "path"])
def test_audit_rejects_tampering_and_unsafe_labels(tmp_path, change):
    source = make_corpus(tmp_path)
    data = prepare(source, tmp_path / "review", tmp_path / "manifest.json", root=tmp_path)
    row = data["samples"][0]
    if change in {"original", "derived"}:
        key = "originalPath" if change == "original" else "imagePath"
        (tmp_path / row[key]).write_bytes(b"changed")
    elif change == "split":
        row["split"] = "validation"
    elif change == "group":
        row["groupId"] = "invented-independent-game"
    elif change == "prediction":
        row["label"].update(status="visual-transcription", piecePlacement="8/8/8/8/8/8/8/8",
                            orientation="white-bottom", method="model-prediction", reviewedBy="model")
    elif change == "pending-label":
        row["label"]["piecePlacement"] = "8/8/8/8/8/8/8/8"
    else:
        row["originalPath"] = "../outside.jpg"
    with pytest.raises(ValueError):
        audit(data, root=tmp_path)


def test_conversion_failure_does_not_publish_partial_corpus(tmp_path):
    source = make_corpus(tmp_path)
    (source / "broken.jpg").write_bytes(b"not an image")
    with pytest.raises(OSError):
        prepare(source, tmp_path / "review", tmp_path / "manifest.json", root=tmp_path)
    assert not (tmp_path / "manifest.json").exists()
    assert not (tmp_path / "review").exists()


def test_preparation_never_overwrites_review_or_writes_into_originals(tmp_path):
    source = make_corpus(tmp_path)
    with pytest.raises(ValueError, match="outside the originals"):
        prepare(source, source / "review", tmp_path / "manifest.json", root=tmp_path)
    prepare(source, tmp_path / "review", tmp_path / "manifest.json", root=tmp_path)
    before = digest(tmp_path / "manifest.json")
    with pytest.raises(ValueError, match="overwrite"):
        prepare(source, tmp_path / "review2", tmp_path / "manifest.json", root=tmp_path)
    assert digest(tmp_path / "manifest.json") == before


def test_heic_review_preserves_decoded_size_and_colors(tmp_path):
    heif = pytest.importorskip("pillow_heif")
    image = Image.new("RGB", (80, 40), (200, 30, 10))
    path = tmp_path / "photo.HEIC"
    heif.from_pillow(image).save(path, quality=95)
    before = digest(path)
    converted, metadata = decode_photo(path)
    assert converted.size == (80, 40)
    assert converted.mode == "RGB"
    assert all(abs(a - b) < 8 for a, b in zip(converted.getpixel((20, 20)), (200, 30, 10)))
    assert digest(path) == before


def test_tracked_intake_has_honest_review_states_without_local_photos():
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / "data/manifests/phone-photos-v1.json").read_text())
    report = audit(data, root=root, verify_files=False)
    assert report["sampleCount"] == 161
    assert report["categories"] == {"chesscom": 55, "lichess": 53, "video": 53}
    assert report["labels"] == {"visual-transcription": 160, "ambiguous": 1}
    assert report["readyForTraining"] is False
    assert sum(sum(v.values()) for v in report["transcribedClassBackgroundCounts"].values()) == 160 * 64
    assert all(min(counts.values()) > 0 for counts in report["transcribedClassBackgroundCounts"].values())
    assert report["distinctTranscribedPositions"] == 153
    assert len(report["repeatedPlacements"]) == 7
    assert not any(r["originalPath"].endswith("IMG_5205.HEIC") for r in data["samples"])
    assert data["removedSamples"][0]["originalPath"].endswith("IMG_5205.HEIC")
    assert all(r["label"]["userVerified"] is False for r in data["samples"])
    added = [r for r in data["samples"] if r.get("intakeBatch") == "2026-10-27"]
    assert len(added) == 72
    assert all(r["label"]["visualRows"] for r in added)
    assert all(r["boardCorners"] is not None and r["split"] == "development" for r in added)
    assert report["reviewedCornerAnnotations"] == 161
    assert report["placementsReviewedAfterRectification"] == 160
    assert report["classificationExclusions"] == ["lichess-photo-8.HEIC"]
    assert all(r["label"]["rectifiedReview"]["independentReview"] is False for r in data["samples"])
    assert len({r["groupId"] for r in data["samples"]}) == 1
    assert all(r["source"].get("targetBoard") for r in added
               if "multiple-visible-boards" in r["conditions"])
    by_name = {Path(r["originalPath"]).stem: r for r in added}
    for first, second in [("lichess-photo-31", "lichess-photo-39"),
                          ("video-photo-37", "video-photo-40")]:
        assert by_name[first]["label"]["piecePlacement"] == by_name[second]["label"]["piecePlacement"]
    ambiguous = next(r for r in data["samples"] if r["originalPath"].endswith("lichess-photo-8.HEIC"))
    assert ambiguous["previousOriginalPath"].endswith("IMG_5265.HEIC")
    assert ambiguous["label"]["piecePlacement"] is None
    assert ambiguous["label"]["orientation"] == "white-bottom"
    assert "piece-animation" in ambiguous["conditions"]


def test_visual_rows_check_both_axes_when_converting_black_view(tmp_path):
    source = make_corpus(tmp_path)
    data = prepare(source, tmp_path / "review", tmp_path / "manifest.json", root=tmp_path)
    row = data["samples"][0]
    row["label"].update(
        status="visual-transcription", piecePlacement="k7/8/8/8/8/8/8/6NK",
        visualRows="KN6/8/8/8/8/8/8/7k", orientation="black-bottom",
        method="visual-board-review", reviewedBy="assistant", sourceSha256=row["originalSha256"],
    )
    assert audit(data, root=tmp_path)["distinctTranscribedPositions"] == 1
    row["label"]["orientation"] = "white-bottom"
    with pytest.raises(ValueError, match="Visual rows disagree"):
        audit(data, root=tmp_path)
    row["label"]["orientation"] = "black-bottom"
    row["label"]["visualRows"] = "6NK/8/8/8/8/8/8/k7"  # Only the ranks were reversed.
    with pytest.raises(ValueError, match="Visual rows disagree"):
        audit(data, root=tmp_path)


def test_review_page_displays_ambiguous_status_without_inventing_placement(tmp_path):
    source = make_corpus(tmp_path)
    data = prepare(source, tmp_path / "review", tmp_path / "manifest.json", root=tmp_path)
    row = data["samples"][0]
    row["label"].update(status="ambiguous", orientation="white-bottom", note="Overlap <f7>")
    write_review_index(tmp_path / "review", data["samples"])
    page = (tmp_path / "review/index.html").read_text()
    assert "ambiguous | white-bottom" in page
    assert "No placement assigned" in page
    assert "Overlap &lt;f7&gt;" in page
    row["label"]["piecePlacement"] = "8/8/8/8/8/8/8/8"
    with pytest.raises(ValueError, match="ambiguous photos"):
        audit(data, root=tmp_path)
