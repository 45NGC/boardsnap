"""Validate the frozen position plan before any image or square is produced."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

from tools.capture_lichess import expand_placement


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data/manifests/digital-positions-v1.json"
SPLITS = ("training", "validation", "evaluation")
LABELS = ("empty", *"PNBRQKpnbrqk")
CATEGORIES = ("opening", "middlegame", "endgame", "promotion", "dense", "sparse")
LEGACY_PATHS = tuple(f"data/manifests/{name}.json" for name in (
    "lichess-cburnett-brown-v1", "lichess-cburnett-blue-v1",
    "chesscom-default-green-v1", "book-strategy-hatched-v1",
))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def placement_family(placement: str) -> str:
    """Conservatively group reflections/rotations and color-swapped diagrams."""
    rows = expand_placement(placement)
    relatives = []
    for _ in range(4):
        for variant in (rows, [row[::-1] for row in rows]):
            flat = "".join(variant)
            relatives.extend((flat, flat.swapcase()))
        rows = ["".join(row) for row in zip(*rows[::-1])]
    return min(relatives)


def legacy_snapshot(root: Path = ROOT) -> list[dict]:
    return [{"path": path, "sha256": digest(root / path)} for path in LEGACY_PATHS]


def legacy_families(root: Path = ROOT) -> set[str]:
    return {placement_family(p["piecePlacement"]) for path in LEGACY_PATHS
            for p in json.loads((root / path).read_text())["positions"]}


def _identifier(value, field: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", value):
        raise ValueError(f"Invalid {field}: expected a safe lowercase identifier")


def _positive_int(value, field: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"Invalid {field}: expected a positive integer")


def validate_manifest(manifest: dict, *, root: Path = ROOT) -> dict:
    """Check structure, split isolation and coverage; never run recognition."""
    if not isinstance(manifest, dict) or manifest.get("schemaVersion") != 1:
        raise ValueError("Expected position manifest schemaVersion 1")
    _identifier(manifest.get("datasetId"), "datasetId")
    policy = manifest.get("generation")
    if (not isinstance(policy, dict) or policy.get("groupCounts") != dict(zip(SPLITS, (14, 3, 3)))
            or policy.get("minimumClassBackgroundSquaresPerSplit") != 2
            or policy.get("bothPromotionColorsPerSplit") is not True):
        raise ValueError("Expected the frozen v1 group counts and coverage policy")
    if manifest.get("legacyExclusions") != legacy_snapshot(root):
        raise ValueError("Legacy manifest snapshot differs; review the frozen exclusions")
    groups, positions = manifest.get("groups"), manifest.get("positions")
    if not isinstance(groups, list) or not groups or not isinstance(positions, list) or not positions:
        raise ValueError("groups and positions must be nonempty lists")
    by_group, source_ids = {}, set()
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("Each group must be an object")
        group_id = group.get("groupId")
        _identifier(group_id, "groupId")
        if group_id in by_group:
            raise ValueError(f"Duplicate groupId: {group_id}")
        if group.get("split") not in SPLITS:
            raise ValueError(f"Invalid split for {group_id}")
        source = group.get("source")
        if not isinstance(source, dict) or source.get("kind") != "generated-legal-play":
            raise ValueError("This schema requires generated-legal-play provenance")
        source_id = source.get("sourceId")
        _identifier(source_id, "sourceId")
        if source_id in source_ids:
            raise ValueError("A source sequence cannot belong to multiple groups")
        _positive_int(source.get("seed"), "source seed")
        if source_id != f"seed-{source['seed']}":
            raise ValueError("sourceId must identify the generation seed")
        moves = source.get("moves")
        if (source.get("initialPosition") != "standard" or not isinstance(moves, list)
                or not moves or any(not isinstance(m, str) or not re.fullmatch(
                    r"[a-h][1-8][a-h][1-8][qrbn]?", m) for m in moves)):
            raise ValueError("Expected a standard-start UCI move sequence")
        source_ids.add(source_id)
        by_group[group_id] = group

    stats = {split: {"positionCount": 0, "groupCount": 0,
                    "categories": {tag: 0 for tag in CATEGORIES},
                    "classes": {label: {color: {"squares": 0, "positions": 0, "groups": set()}
                                        for color in ("light", "dark")} for label in LABELS}}
             for split in SPLITS}
    for group in groups:
        stats[group["split"]]["groupCount"] += 1
    forbidden = legacy_families(root)
    seen_ids, seen_families, used_groups = set(), {}, Counter()
    group_categories = {key: Counter() for key in by_group}
    promotion_colors = {split: set() for split in SPLITS}
    for position in positions:
        if not isinstance(position, dict):
            raise ValueError("Each position must be an object")
        pid, gid = position.get("positionId"), position.get("groupId")
        _identifier(pid, "positionId")
        _identifier(gid, "position groupId")
        if pid in seen_ids:
            raise ValueError(f"Duplicate positionId: {pid}")
        if gid not in by_group:
            raise ValueError(f"Unknown source group: {gid}")
        # One source of truth: splits belong to groups, never individual positions.
        if "split" in position:
            raise ValueError("Position split must be inherited from its source group")
        ply = position.get("ply")
        _positive_int(ply, "ply")
        if ply > len(by_group[gid]["source"]["moves"]):
            raise ValueError(f"Ply exceeds source sequence: {pid}")
        rows = expand_placement(position.get("piecePlacement"))
        family = placement_family(position["piecePlacement"])
        if family in forbidden:
            raise ValueError(f"Position overlaps the legacy corpus: {pid}")
        if family in seen_families:
            raise ValueError(f"Duplicate or transformed position: {pid}, {seen_families[family]}")
        seen_families[family] = pid
        seen_ids.add(pid)
        used_groups[gid] += 1
        tags = position.get("categories")
        if (not isinstance(tags, list) or not tags or any(t not in CATEGORIES for t in tags)
                or len(set(tags)) != len(tags)):
            raise ValueError(f"Invalid categories for {pid}")
        occupied = sum(cell != "." for row in rows for cell in row)
        if ("dense" in tags) != (occupied >= 28) or ("sparse" in tags) != (occupied <= 10):
            raise ValueError(f"Density categories disagree with placement: {pid}")
        if "opening" in tags and not (ply == 12 and occupied >= 28):
            raise ValueError(f"Invalid opening sample: {pid}")
        if "middlegame" in tags and not (ply >= 32 and 12 <= occupied <= 26):
            raise ValueError(f"Invalid middlegame sample: {pid}")
        if "endgame" in tags and not (3 <= occupied <= 10):
            raise ValueError(f"Invalid endgame sample: {pid}")
        if "promotion" in tags and len(by_group[gid]["source"]["moves"][ply - 1]) != 5:
            raise ValueError(f"Promotion sample is not after a promotion: {pid}")
        if "promotion" in tags:
            promotion_colors[by_group[gid]["split"]].add(ply % 2)
        group_categories[gid].update(tags)
        stat = stats[by_group[gid]["split"]]
        stat["positionCount"] += 1
        for tag in tags:
            stat["categories"][tag] += 1
        present = set()
        for row, line in enumerate(rows):
            for col, symbol in enumerate(line):
                label, color = ("empty" if symbol == "." else symbol), ("light", "dark")[(row + col) % 2]
                count = stat["classes"][label][color]
                count["squares"] += 1
                count["groups"].add(gid)
                present.add((label, color))
        for label, color in present:
            stat["classes"][label][color]["positions"] += 1
    if set(used_groups) != set(by_group):
        raise ValueError("Every source group must contain selected positions")
    for gid, counts in group_categories.items():
        if used_groups[gid] != 4 or any(counts[tag] != 1 for tag in CATEGORIES[:4]):
            raise ValueError(f"Each group needs four samples: opening, middlegame, endgame, promotion ({gid})")
    warnings = []
    for split, stat in stats.items():
        if stat["groupCount"] != policy["groupCounts"][split]:
            raise ValueError(f"Frozen group count changed for {split}")
        if promotion_colors[split] != {0, 1}:
            raise ValueError(f"Both promotion colors are required in {split}")
        for label, colors in stat["classes"].items():
            for color, counts in colors.items():
                counts["groups"] = len(counts["groups"])
                if counts["squares"] < policy["minimumClassBackgroundSquaresPerSplit"]:
                    raise ValueError(f"Insufficient class/background coverage: {split}/{label}/{color}")
                if counts["squares"] < 5 or counts["groups"] < 3:
                    warnings.append({"split": split, "class": label, "background": color,
                                     **counts})
    return {"datasetId": manifest["datasetId"], "positionCount": len(positions),
            "sourceGroupCount": len(groups), "splits": stats, "underrepresented": warnings,
            "coverageOnly": True}


def variant_identity(manifest: dict, position_id: str) -> dict:
    """Metadata every future theme/view/overlay/crop must inherit unchanged.

    The caller must validate the complete manifest once before creating variants.
    This does not generate an image or supply a recognition prediction.
    """
    for position in manifest["positions"]:
        if position["positionId"] == position_id:
            group = next(g for g in manifest["groups"] if g["groupId"] == position["groupId"])
            return {"datasetId": manifest["datasetId"], "positionId": position_id,
                    "groupId": group["groupId"], "split": group["split"],
                    "piecePlacement": position["piecePlacement"]}
    raise ValueError(f"Unknown positionId: {position_id}")


def validate_variants(manifest: dict, annotations: list[dict]) -> None:
    """Reject split/label drift, regardless of the rendering or crop options."""
    if not isinstance(annotations, list):
        raise ValueError("Variant annotations must be a list")
    for annotation in annotations:
        if not isinstance(annotation, dict):
            raise ValueError("Each variant annotation must be an object")
        expected = variant_identity(manifest, annotation.get("positionId"))
        if any(annotation.get(key) != value for key, value in expected.items()):
            raise ValueError("Variant must inherit dataset, position, group, split and placement")


def replay_sources(manifest: dict) -> None:
    """Optional chess dependency: verify legality and labels from recorded moves."""
    import chess

    for group in manifest["groups"]:
        board = chess.Board()
        positions = {p["ply"]: p for p in manifest["positions"] if p["groupId"] == group["groupId"]}
        if len(positions) != 4:
            raise ValueError("A source group needs four distinct sample plies")
        for ply, uci in enumerate(group["source"]["moves"], 1):
            move = chess.Move.from_uci(uci)
            if board.is_game_over() or move not in board.legal_moves:
                raise ValueError(f"Illegal source move: {group['groupId']} ply {ply}")
            board.push(move)
            if not board.is_valid():
                raise ValueError("Invalid generated board")
            if ply in positions and board.board_fen() != positions[ply]["piecePlacement"]:
                raise ValueError(f"Source placement mismatch: {positions[ply]['positionId']}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--replay", action="store_true", help="Verify legal source moves (requires .[dataset])")
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text())
        report = validate_manifest(manifest)
        if args.replay:
            replay_sources(manifest)
        report["manifestSha256"] = digest(args.manifest)
    except (OSError, ValueError, ImportError) as error:
        print(f"Invalid position plan: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
