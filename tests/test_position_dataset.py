"""Position-plan integrity before rendering; these are not recognition scores."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from tools import position_dataset as dataset


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads(dataset.DEFAULT_MANIFEST.read_text())
pytestmark = pytest.mark.unit


def test_frozen_coverage_report_and_split_sizes():
    report = dataset.validate_manifest(MANIFEST)
    assert report["positionCount"] == 80
    assert report["sourceGroupCount"] == 20
    assert [(s["groupCount"], s["positionCount"]) for s in report["splits"].values()] == [
        (14, 56), (3, 12), (3, 12)]
    for stat in report["splits"].values():
        assert all(stat["categories"][tag] > 0 for tag in dataset.CATEGORIES)
        assert sum(v["squares"] for colors in stat["classes"].values()
                   for v in colors.values()) == stat["positionCount"] * 64
        assert all(v["squares"] >= 2 for colors in stat["classes"].values() for v in colors.values())
    assert report["coverageOnly"] is True
    assert len(report["underrepresented"]) == 8
    report["manifestSha256"] = dataset.digest(dataset.DEFAULT_MANIFEST)
    assert report == json.loads((ROOT / "data/reports/digital-positions-v1-coverage.json").read_text())


def test_background_parity_uses_canonical_chess_squares():
    # Independent coordinate oracle: a1 is dark, a8 is light; count White queens.
    expected = {split: {"light": 0, "dark": 0} for split in dataset.SPLITS}
    for position in MANIFEST["positions"]:
        split = dataset.variant_identity(MANIFEST, position["positionId"])["split"]
        for rank_number, rank in zip(range(8, 0, -1), position["piecePlacement"].split("/"), strict=True):
            file_number = 1
            for token in rank:
                if token.isdigit():
                    file_number += int(token)
                else:
                    if token == "Q":
                        color = "dark" if (file_number + rank_number) % 2 == 0 else "light"
                        expected[split][color] += 1
                    file_number += 1
    report = dataset.validate_manifest(MANIFEST)
    for split in dataset.SPLITS:
        assert expected[split] == {c: v["squares"] for c, v in report["splits"][split]["classes"]["Q"].items()}


@pytest.mark.parametrize("change, message", [
    (lambda m: m.update(schemaVersion=9), "schemaVersion"),
    (lambda m: m["legacyExclusions"][0].update(sha256="changed"), "Legacy"),
    (lambda m: m["groups"][0].update(split="tuning"), "Invalid split"),
    (lambda m: m["groups"][1].update(groupId=m["groups"][0]["groupId"]), "Duplicate groupId"),
    (lambda m: m["groups"][1].update(source=m["groups"][0]["source"]), "multiple groups"),
    (lambda m: m["positions"][0].update(split="evaluation"), "inherited"),
    (lambda m: m["positions"][1].update(positionId=m["positions"][0]["positionId"]), "Duplicate positionId"),
    (lambda m: m["positions"][0].update(groupId="missing"), "Unknown source"),
    (lambda m: m["positions"][0].update(ply=True), "positive integer"),
    (lambda m: m["positions"][0].update(ply=10000), "exceeds"),
    (lambda m: m["positions"][0].update(piecePlacement="invalid"), "eight ranks"),
    (lambda m: m["positions"][0].update(piecePlacement="8/8/8/8/8/8/8/8"), "legacy"),
    (lambda m: m["positions"][1].update(piecePlacement=m["positions"][0]["piecePlacement"]), "Duplicate or transformed"),
    (lambda m: m["positions"][0].update(categories=["opening"]), "Density"),
    (lambda m: m["positions"].pop(), "four samples"),
    (lambda m: m["groups"][0]["source"]["moves"].__setitem__(0, "0000"), "UCI"),
    (lambda m: m["generation"].update(minimumClassBackgroundSquaresPerSplit=0), "policy"),
])
def test_rejects_corrupt_or_leaking_plans(change, message):
    manifest = deepcopy(MANIFEST)
    change(manifest)
    with pytest.raises(ValueError, match=message):
        dataset.validate_manifest(manifest)


def test_cannot_move_a_source_group_to_another_split():
    manifest = deepcopy(MANIFEST)
    group = next(g for g in manifest["groups"] if g["split"] == "training")
    group["split"] = "evaluation"
    with pytest.raises(ValueError, match="group count"):
        dataset.validate_manifest(manifest)


def test_transformed_legacy_diagrams_are_excluded():
    original = "r6k/8/8/8/8/8/8/K6R"
    rotated = "R6K/8/8/8/8/8/8/k6r"
    assert dataset.placement_family(original) == dataset.placement_family(rotated)
    assert dataset.placement_family(original) == dataset.placement_family(original.swapcase())
    assert dataset.placement_family(rotated) in dataset.legacy_families()


@pytest.mark.parametrize("split", dataset.SPLITS)
def test_every_variant_inherits_the_whole_source_group(split):
    group = next(g for g in MANIFEST["groups"] if g["split"] == split)
    positions = [p for p in MANIFEST["positions"] if p["groupId"] == group["groupId"]]
    variants = []
    for position in positions:
        for view in ("white-bottom", "black-bottom"):
            for style in ("lichess-brown", "lichess-blue", "chesscom-green"):
                for condition in ("clean", "arrow", "highlight", "jpeg", "resized", "square-crop"):
                    variants.append(dict(dataset.variant_identity(MANIFEST, position["positionId"]),
                                         orientation=view, style=style, condition=condition))
    dataset.validate_variants(MANIFEST, variants)
    assert {v["split"] for v in variants} == {split}
    assert len({v["groupId"] for v in variants}) == 1


@pytest.mark.parametrize("field, value", [
    ("split", "wrong"), ("groupId", "another-sequence"),
    ("piecePlacement", "8/8/8/8/8/8/8/8"), ("datasetId", "another-dataset"),
    ("positionId", "missing"),
])
def test_rejects_variant_split_or_label_drift(field, value):
    annotation = dataset.variant_identity(MANIFEST, "digital-001")
    annotation[field] = value
    with pytest.raises(ValueError):
        dataset.validate_variants(MANIFEST, [annotation])


def test_missing_coverage_is_an_error():
    manifest = deepcopy(MANIFEST)
    # Replacing each White queen with a rook preserves density but removes a class.
    for position in manifest["positions"]:
        position["piecePlacement"] = position["piecePlacement"].replace("Q", "R")
    with pytest.raises(ValueError, match="class/background coverage"):
        dataset.validate_manifest(manifest)


def test_validation_command_json_and_invalid_input(tmp_path, capsys):
    assert dataset.main([]) == 0
    output = capsys.readouterr()
    assert not output.err
    assert json.loads(output.out)["positionCount"] == 80
    invalid = tmp_path / "broken.json"
    invalid.write_text("{")
    assert dataset.main([str(invalid)]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert "Invalid position plan" in output.err


def test_optional_legal_replay_and_reproduction(tmp_path):
    pytest.importorskip("chess", reason="Install .[dataset] to replay and reproduce source sequences")
    from tools import prepare_positions

    dataset.replay_sources(MANIFEST)
    assert prepare_positions.build_manifest() == MANIFEST
    output = tmp_path / "new.json"
    assert prepare_positions.main([str(output)]) == 0
    original = output.read_bytes()
    assert original == dataset.DEFAULT_MANIFEST.read_bytes()
    assert prepare_positions.main([str(output)]) == 2
    assert output.read_bytes() == original
    broken = deepcopy(MANIFEST)
    broken["groups"][0]["source"]["moves"][0] = "e2e5"
    with pytest.raises(ValueError, match="Illegal source move"):
        dataset.replay_sources(broken)
    broken = deepcopy(MANIFEST)
    broken["positions"][0]["piecePlacement"] = "8/8/8/8/8/8/8/8"
    with pytest.raises(ValueError, match="Source placement mismatch"):
        dataset.replay_sources(broken)
