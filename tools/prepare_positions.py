"""Reproduce the v1 position plan; no downloads, rendering or model evaluation."""

import argparse
from collections import Counter
import json
from pathlib import Path
import random
import sys

from tools.capture_lichess import expand_placement
from tools.position_dataset import (LABELS, SPLITS, legacy_families, legacy_snapshot,
                                    placement_family, replay_sources, validate_manifest)


GENERATION_SEED = 20261007
PARTITION_SEED = 1729


def generate_sequence(seed: int):
    """Four snapshots of one synthetic legal sequence, not expert game play."""
    import chess

    rng = random.Random(seed)
    board = chess.Board()
    moves, samples = [], {}
    for ply in range(1, 501):
        if board.is_game_over():
            return None
        legal = sorted(board.legal_moves, key=lambda move: move.uci())
        # Encourage exchanges and pawn advances to reach sparse/promoted cases.
        weights = [1 + 5 * board.is_capture(move)
                   + 3 * (board.piece_type_at(move.from_square) == chess.PAWN)
                   + 20 * bool(move.promotion) for move in legal]
        move = rng.choices(legal, weights=weights)[0]
        board.push(move)
        moves.append(move.uci())
        occupied = len(board.piece_map())
        placement = board.board_fen()
        if ply == 12 and occupied >= 28:
            samples["opening"] = (ply, placement)
        if ply >= 32 and 12 <= occupied <= 26 and "middlegame" not in samples:
            samples["middlegame"] = (ply, placement)
        if move.promotion and "promotion" not in samples:
            samples["promotion"] = (ply, placement)
        if 3 <= occupied <= 10 and "endgame" not in samples and not move.promotion:
            samples["endgame"] = (ply, placement)
        if len(samples) == 4 and len({p for _, p in samples.values()}) == 4:
            return moves, samples
    return None


def assign_splits(groups: list[dict], positions: list[dict]) -> None:
    """Deterministic group stratification using labels only, before any images.

    The first shuffled 14/3/3 allocation with >=2 cells of each class/background
    per split and both promotion colors in each split is frozen into the file.
    This is dataset design, never selection based on recognition performance.
    """
    rng = random.Random(PARTITION_SEED)
    counts, promotion_colors = {}, {}
    for group in groups:
        gid = group["groupId"]
        counts[gid] = Counter()
        for position in (p for p in positions if p["groupId"] == gid):
            rows = expand_placement(position["piecePlacement"])
            for row, line in enumerate(rows):
                for col, symbol in enumerate(line):
                    counts[gid][("empty" if symbol == "." else symbol, (row + col) % 2)] += 1
            if "promotion" in position["categories"]:
                promotion_colors[gid] = position["ply"] % 2  # Standard start: odd = White.
    ids = [g["groupId"] for g in groups]
    for _ in range(10000):
        order = rng.sample(ids, len(ids))
        allocation = dict(zip(SPLITS, (order[:14], order[14:17], order[17:]), strict=True))
        valid = True
        for subset in allocation.values():
            total = sum((counts[gid] for gid in subset), Counter())
            if (any(total[label, color] < 2 for label in LABELS for color in (0, 1))
                    or {promotion_colors[gid] for gid in subset} != {0, 1}):
                valid = False
                break
        if valid:
            for group in groups:
                group["split"] = next(split for split, subset in allocation.items() if group["groupId"] in subset)
            return
    raise ValueError("Could not satisfy the declared group coverage constraints")


def build_manifest() -> dict:
    import chess

    if chess.__version__ != "1.11.2":
        raise ValueError("Reproduction requires chess==1.11.2 (install .[dataset])")
    groups, positions = [], []
    excluded = legacy_families()
    for seed in range(GENERATION_SEED, GENERATION_SEED + 1000):
        result = generate_sequence(seed)
        if result is None:
            continue
        moves, samples = result
        families = {placement_family(placement) for _, placement in samples.values()}
        if len(families) != 4 or families & excluded:
            continue
        excluded.update(families)
        gid = f"sequence-{len(groups) + 1:03d}"
        groups.append({"groupId": gid, "source": {
            "sourceId": f"seed-{seed}", "kind": "generated-legal-play", "seed": seed,
            "initialPosition": "standard", "moves": moves,
        }})
        for category in ("opening", "middlegame", "endgame", "promotion"):
            ply, placement = samples[category]
            occupied = sum(c != "." for row in expand_placement(placement) for c in row)
            tags = [category]
            if occupied >= 28:
                tags.append("dense")
            if occupied <= 10:
                tags.append("sparse")
            positions.append({"positionId": f"digital-{len(positions) + 1:03d}",
                              "groupId": gid, "ply": ply,
                              "piecePlacement": placement, "categories": tags})
        if len(groups) == 20:
            break
    if len(groups) != 20:
        raise ValueError("Could not produce twenty eligible source sequences")
    assign_splits(groups, positions)
    manifest = {
        "schemaVersion": 1, "datasetId": "digital-positions-v1", "status": "frozen-position-plan",
        "notes": "80 distinct placements from 20 synthetic legal sequences, not 80 independent games. "
                 "No images or recognition measurements. Not representative of human play. "
                 "All descendants inherit their source group's split across every style and client.",
        "generation": {"tool": "tools.prepare_positions", "chessVersion": "1.11.2",
                       "seedStart": GENERATION_SEED, "partitionSeed": PARTITION_SEED,
                       "groupCounts": {"training": 14, "validation": 3, "evaluation": 3},
                       "minimumClassBackgroundSquaresPerSplit": 2,
                       "bothPromotionColorsPerSplit": True},
        "legacyExclusions": legacy_snapshot(), "groups": groups, "positions": positions,
    }
    validate_manifest(manifest)
    replay_sources(manifest)
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New manifest path; existing files are refused")
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise ValueError("Output already exists; never overwrite a frozen position plan")
        manifest = build_manifest()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(manifest, indent=2) + "\n")
    except (OSError, ValueError, ImportError) as error:
        print(f"Cannot prepare positions: {error}", file=sys.stderr)
        return 2
    print(f"Prepared {len(manifest['positions'])} positions in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
