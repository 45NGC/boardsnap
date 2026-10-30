"""Inventory local screen photographs and prepare review copies, without inference.

This intake format is deliberately development-only. It is not a training index
or a replacement for the reviewed, partitioned screenshot import format.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
from html import escape
from importlib.metadata import PackageNotFoundError, version
from io import BytesIO
import json
import math
from pathlib import Path
import tempfile

from PIL import Image, ImageCms, ImageDraw, ImageOps

from tools.capture_lichess import expand_placement

ROOT = Path(__file__).resolve().parents[1]
EXTENSIONS = {".heic", ".heif", ".png", ".jpg", ".jpeg"}
CATEGORIES = {"video-photos": "video", "chesscom-photos": "chesscom", "lichess-photos": "lichess"}
UNRESOLVED_GROUP = "phone-photos-unresolved-origin-v1"
CORNER_ORDER = ["top-left", "top-right", "bottom-right", "bottom-left"]


def validate_corners(corners, size):
    """Validate image-space TL/TR/BR/BL boundaries, independently of chess view.

    Coordinates refer to the full EXIF-normalized RGB image, with x rightward
    and y downward. Right/bottom image boundaries may equal width/height.
    This validates annotation geometry, not the presence of a chessboard.
    """
    if (not isinstance(corners, list) or len(corners) != 4
            or any(not isinstance(p, list) or len(p) != 2 for p in corners)):
        raise ValueError("Board corners must contain four [x, y] points.")
    if any(type(v) not in (int, float) or not math.isfinite(v) for p in corners for v in p):
        raise ValueError("Board corners must be finite numbers.")
    width, height = size
    if any(not (0 <= x <= width and 0 <= y <= height) for x, y in corners):
        raise ValueError("Board corners must stay inside the normalized image.")
    for i in range(4):
        a, b, c = corners[i], corners[(i + 1) % 4], corners[(i + 2) % 4]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if cross <= 0:
            raise ValueError("Board corners must form a convex clockwise quadrilateral.")
    tl, tr, br, bl = corners
    if not (tl[0] < tr[0] and bl[0] < br[0] and tl[1] < bl[1] and tr[1] < br[1]):
        raise ValueError("Board corners must follow image TL/TR/BR/BL order.")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def conversion_versions():
    result = {}
    for name in ("Pillow", "pillow-heif"):
        try:
            result[name] = version(name)
        except PackageNotFoundError:
            result[name] = None
    return result


def child(root, relative):
    path = root / relative
    if Path(relative).is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Photo paths must stay inside the project root.")
    return path


def decode_photo(path):
    """Apply file orientation once, convert embedded ICC colors to sRGB, keep size.

    pillow-heif already applies HEIF orientation and resets its EXIF tag. Pillow
    handles remaining JPEG/PNG EXIF orientation here. No board crop or denoising.
    """
    if path.suffix.lower() in {".heic", ".heif"}:
        try:
            import pillow_heif
        except ImportError as exc:
            raise ValueError("HEIC review requires: python -m pip install -e '.[photos]'") from exc
        pillow_heif.register_heif_opener()
    with Image.open(path) as source:
        if getattr(source, "n_frames", 1) != 1:
            raise ValueError(f"Expected one still photograph: {path.name}")
        source.load()
        exif = source.getexif()
        metadata = {
            "cameraMake": exif.get(271), "cameraModel": exif.get(272),
            "fileDateTime": exif.get(306), "timeZone": None,
            "originalOrientation": source.info.get("original_orientation", exif.get(274)),
            "decodedBitDepth": source.info.get("bit_depth", 8),
        }
        icc = source.info.get("icc_profile")
        image = ImageOps.exif_transpose(source).convert("RGB")
        if icc:
            image = ImageCms.profileToProfile(image, ImageCms.ImageCmsProfile(BytesIO(icc)),
                                              ImageCms.createProfile("sRGB"), outputMode="RGB")
        metadata["colorConversion"] = "embedded-icc-to-srgb" if icc else "untagged-assumed-srgb"
        metadata["sourceIccSha256"] = hashlib.sha256(icc).hexdigest() if icc else None
        image.info.clear()  # Do not propagate GPS, EXIF, or stale orientation.
        return image, metadata


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_review_index(destination, samples):
    """Link review copies, preferring exported JPEGs when available."""
    cards = []
    for row in samples:
        name = escape(Path(row["originalPath"]).name)
        sample_id = escape(row["id"])
        label = row["label"]
        details = escape(f"{label['status']} | {label['orientation'] or 'orientation pending'}")
        placement = escape(label["piecePlacement"] or "No placement assigned")
        note = escape(label.get("note", ""))
        geometry = (f'<p><a href="geometry/{sample_id}.jpg">Corners, rectified board and label diagram</a></p>'
                    if (destination / "geometry" / f"{row['id']}.jpg").is_file() else "")
        jpeg = Path("jpg") / row["source"]["category"] / (Path(row["originalPath"]).stem + ".jpg")
        target = escape(jpeg.as_posix()) if (destination / jpeg).is_file() else f"images/{sample_id}.png"
        cards.append(f'<figure><a href="{target}"><img loading="lazy" '
                     f'src="thumbnails/{sample_id}.jpg" alt="{name}"></a>'
                     f'<figcaption>{name} ({escape(row["source"]["category"])})'
                     f'<p>{details}</p><code>{placement}</code><p>{note}</p>{geometry}'
                     '</figcaption></figure>')
    (destination / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>BoardSnap photo review</title>'
        '<style>body{font-family:sans-serif}main{display:flex;flex-wrap:wrap}'
        'figure{margin:10px;width:290px}code{overflow-wrap:anywhere}'
        'img{max-height:360px;max-width:270px}</style>'
        '<h1>Photo review copies</h1><p>Open an image for the full-size RGB review copy '
        '(JPEG when exported, otherwise PNG). '
        'These are converted photographs, not direct screenshot references. '
        'Labels are assistant visual transcriptions, not user-confirmed references. '
        'Canonical placement runs from a8 to h1, regardless of photo orientation.</p><main>'
        + "\n".join(cards) + '</main>\n', encoding="utf-8")


def prepare(source, destination, manifest, *, root=ROOT):
    source, destination, manifest, root = (p.resolve() for p in (source, destination, manifest, root))
    for path in (source, destination, manifest):
        if not path.is_relative_to(root):
            raise ValueError("Inputs and outputs must stay inside the project root.")
    if destination.is_relative_to(source) or manifest.is_relative_to(source):
        raise ValueError("Keep derived files outside the originals directory.")
    if destination.exists() or manifest.exists():
        raise ValueError("Refusing to overwrite an existing corpus or review manifest.")
    files = sorted(p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS)
    if not files:
        raise ValueError("No supported photographs found.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    samples = []
    srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    with tempfile.TemporaryDirectory(prefix="phone-intake-", dir=destination.parent) as temporary:
        stage = Path(temporary) / "corpus"
        (stage / "images").mkdir(parents=True)
        (stage / "thumbnails").mkdir()
        for path in files:
            relative = path.relative_to(source)
            original = child(root, str(path.relative_to(root)))
            before = digest(original)
            sample_id = "phone-" + hashlib.sha256(relative.as_posix().encode()).hexdigest()[:16]
            image, metadata = decode_photo(original)
            if digest(original) != before:
                raise ValueError(f"Original changed during conversion: {relative}")
            png = Path("images") / f"{sample_id}.png"
            image.save(stage / png, icc_profile=srgb, compress_level=3)
            pixel_hash = hashlib.sha256(image.tobytes()).hexdigest()
            size = list(image.size)
            image.thumbnail((290, 450), Image.Resampling.LANCZOS)
            image.save(stage / "thumbnails" / f"{sample_id}.jpg", quality=92)
            samples.append({
                "id": sample_id, "originalPath": original.relative_to(root).as_posix(),
                "originalSha256": before, "originalBytes": original.stat().st_size,
                "imagePath": (destination / png).relative_to(root).as_posix(),
                "imageSha256": digest(stage / png), "pixelSha256": pixel_hash, "imageSize": size,
                "captureMetadata": metadata,
                "source": {"category": CATEGORIES.get(relative.parts[0], "unknown"),
                           "url": None, "gameId": None, "videoTimestamp": None,
                           "referenceScreenshot": None, "referenceStatus": "not-provided"},
                "groupId": UNRESOLVED_GROUP, "groupingStatus": "unresolved-conservative-bucket",
                "split": "development", "conditions": [],
                "label": {"status": "pending", "piecePlacement": None, "orientation": None,
                          "reviewedBy": None, "method": None, "userVerified": False},
                "boardCorners": None,
            })
        sheets = []
        for start in range(0, len(samples), 10):
            sheet = Image.new("RGB", (1500, 1000), "#dddddd")
            draw = ImageDraw.Draw(sheet)
            for index, row in enumerate(samples[start:start + 10]):
                x, y = index % 5 * 300, index // 5 * 500
                original = Path(row["originalPath"])
                draw.text((x + 6, y + 5), f"{row['source']['category']}: {original.name}", fill="black")
                with Image.open(stage / "thumbnails" / f"{row['id']}.jpg") as thumb:
                    sheet.paste(thumb, (x + (300 - thumb.width) // 2, y + 27))
            name = f"contact-{start // 10 + 1:02d}.jpg"
            sheet.save(stage / name, quality=92)
            sheets.append((destination / name).relative_to(root).as_posix())
        data = {
            "schemaVersion": 1, "datasetId": "phone-photos-v1", "dataRole": "photo-intake",
            "independentFinalEvaluation": False,
            "partitionPolicy": "Development-only until source groups, labels and cross-corpus overlaps are reviewed. Never randomly split individual photographs or squares.",
            "conversion": "Full-size RGB sRGB PNG; file orientation applied; no cropping, rectification, sharpening or recognition. Review copies are not direct screenshots.",
            "conversionLibraryVersions": conversion_versions(),
            "contactSheets": sheets, "samples": samples,
        }
        write_review_index(stage, samples)
        stage.rename(destination)
    write_json(manifest, data)
    return data


def audit(data, *, root=ROOT, verify_files=True):
    """Check intake integrity, not recognition accuracy or readiness for training."""
    if (data.get("schemaVersion") != 1 or data.get("dataRole") != "photo-intake"
            or data.get("independentFinalEvaluation") is not False or not data.get("samples")):
        raise ValueError("Expected a development photographic intake manifest.")
    ids, paths, hashes = set(), set(), Counter()
    categories, labels, cameras, orientations = Counter(), Counter(), Counter(), Counter()
    placements = defaultdict(list)
    coverage = {label: {"light": 0, "dark": 0} for label in ("empty", *"PNBRQKpnbrqk")}
    annotated = 0
    reviewed_labels = 0
    for row in data["samples"]:
        if row["id"] in ids or row["originalPath"] in paths:
            raise ValueError("Duplicate sample identity or original path.")
        ids.add(row["id"])
        paths.add(row["originalPath"])
        if row["split"] != "development" or row["groupId"] != UNRESOLVED_GROUP:
            raise ValueError("Unresolved photographic intake must stay together in development.")
        label = row["label"]
        if label["status"] == "visual-transcription":
            board = expand_placement(label["piecePlacement"])
            if label["orientation"] not in {"white-bottom", "black-bottom"}:
                raise ValueError("Transcriptions require an explicitly reviewed orientation.")
            if label["method"] != "visual-board-review" or not label["reviewedBy"]:
                raise ValueError("Predictions cannot supply photographic reference labels.")
            if label.get("sourceSha256") != row["originalSha256"]:
                raise ValueError("Visual labels must identify the reviewed original bytes.")
            if "visualRows" in label:
                visual = expand_placement(label["visualRows"])
                if label["orientation"] == "black-bottom":
                    visual = [squares[::-1] for squares in visual[::-1]]
                if visual != board:
                    raise ValueError("Visual rows disagree with canonical placement and orientation.")
            placements[label["piecePlacement"]].append(Path(row["originalPath"]).name)
            for rank, squares in enumerate(board):
                for file, piece in enumerate(squares):
                    color = "light" if (rank + file) % 2 == 0 else "dark"
                    coverage["empty" if piece == "." else piece][color] += 1
        elif label["status"] not in {"pending", "ambiguous"} or label["piecePlacement"] is not None:
            raise ValueError("Pending or ambiguous photos cannot have ground-truth placement.")
        if row.get("boardCorners") is not None:
            validate_corners(row["boardCorners"], row["imageSize"])
            review = row.get("geometryReview", {})
            if (review.get("status") != "visual-reviewed"
                    or review.get("imageSha256") != row["imageSha256"]
                    or review.get("coordinateSpace") != "normalized-image-pixels"
                    or review.get("cornerOrder") != CORNER_ORDER
                    or not review.get("reviewedBy") or not review.get("reviewedOn")):
                raise ValueError("Corner annotations require review provenance for the normalized image.")
            annotated += 1
        second = label.get("rectifiedReview")
        if second is not None:
            if (row.get("boardCorners") is None
                    or second.get("imageSha256") != row["imageSha256"]
                    or second.get("boardCorners") != row["boardCorners"]
                    or second.get("piecePlacement") != label["piecePlacement"]
                    or second.get("orientation") != label["orientation"]
                    or not second.get("reviewedBy") or not second.get("reviewedOn")
                    or second.get("outcome") != ("ambiguous-excluded" if label["status"] == "ambiguous" else "matches-visible-pieces")):
                raise ValueError("Rectified review does not match the current image, corners or label.")
            reviewed_labels += label["status"] == "visual-transcription"
        for key, sha in (("originalPath", "originalSha256"), ("imagePath", "imageSha256")):
            path = child(root, row[key])
            if verify_files and digest(path) != row[sha]:
                raise ValueError(f"Changed photographic data: {row[key]}")
        if row["originalPath"] == row["imagePath"]:
            raise ValueError("Review copies must not replace originals.")
        if verify_files:
            with Image.open(child(root, row["imagePath"])) as image:
                if image.mode != "RGB" or list(image.size) != row["imageSize"]:
                    raise ValueError("Review image geometry or mode changed.")
        hashes[row["originalSha256"]] += 1
        categories[row["source"]["category"]] += 1
        labels[label["status"]] += 1
        cameras[str(row["captureMetadata"]["cameraModel"])] += 1
        orientations[str(label["orientation"])] += 1
    return {
        "sampleCount": len(ids), "categories": dict(categories), "labels": dict(labels),
        "reviewedCornerAnnotations": annotated,
        "placementsReviewedAfterRectification": reviewed_labels,
        "classificationExclusions": [Path(r["originalPath"]).name for r in data["samples"]
                                     if r["label"]["status"] != "visual-transcription"],
        "cameras": dict(cameras), "reviewedOrientations": dict(orientations),
        "exactDuplicateOriginals": sum(n - 1 for n in hashes.values()),
        "distinctTranscribedPositions": len(placements),
        "repeatedPlacements": [
            {"piecePlacement": placement, "originals": names}
            for placement, names in sorted(placements.items()) if len(names) > 1
        ],
        "missingDirectReferences": sum(r["source"]["referenceScreenshot"] is None for r in data["samples"]),
        "splitCounts": {"development": len(ids), "training": 0, "validation": 0, "evaluation": 0},
        "transcribedClassBackgroundCounts": coverage,
        "coverageNote": "Canonical light/dark square parity in visual transcriptions only; counts do not measure image readability or recognition accuracy.",
        "readyForTraining": False, "fileIntegrityChecked": verify_files,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("prepare")
    create.add_argument("--source", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--manifest", type=Path, required=True)
    check = sub.add_parser("audit")
    check.add_argument("--manifest", type=Path, required=True)
    check.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        data = prepare(args.source, args.output, args.manifest)
    else:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = audit(data)
    report["manifestSha256"] = digest(args.manifest)
    if getattr(args, "report", None):
        write_json(args.report, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
