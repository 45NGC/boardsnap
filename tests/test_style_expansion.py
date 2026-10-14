"""Style holdouts are independent of position splits and survive derived variants."""

from copy import deepcopy
import json
from pathlib import Path

from PIL import Image
import pytest

from tools.build_square_dataset import build_dataset
from tools.build_style_dataset import check_reservation, merge_datasets
from tools.collect_styles import RECIPE, POLICY, style_jobs
from tools.evaluate_marks import dimensions, summarize
from tools.neural_data import digest, read_index
from tools.position_dataset import DEFAULT_MANIFEST, variant_identity

MANIFEST = json.loads(DEFAULT_MANIFEST.read_text())
RECIPE_DATA, POLICY_DATA = json.loads(RECIPE.read_text()), json.loads(POLICY.read_text())
pytestmark = pytest.mark.unit


def test_fixed_capture_plan_keeps_reserved_pairs_out_of_training_and_validation():
    jobs = style_jobs(MANIFEST, RECIPE_DATA, POLICY_DATA)
    total = reserved = 0
    by_group = {}
    for job in jobs:
        config = job["configurations"][0]
        held_out = config["id"].rsplit("-", 1)[0] in POLICY_DATA["heldOutCombinations"]
        for pid in job["positionIds"]:
            identity = variant_identity(MANIFEST, pid)
            assert by_group.setdefault(identity["groupId"], identity["split"]) == identity["split"]
            if held_out:
                assert identity["split"] == "evaluation"
                reserved += len(config["orientations"])
            total += len(config["orientations"])
    assert len(jobs) == 172 and total == 860 and reserved == 60
    assert len(by_group) == 20


@pytest.mark.parametrize("held_out", [[], ["missing"], ["lichess-blue-staunty"]*2])
def test_invalid_holdout_plan_fails_before_capture(held_out):
    with pytest.raises(ValueError, match="Reserve"):
        style_jobs(MANIFEST, RECIPE_DATA, dict(POLICY_DATA, heldOutCombinations=held_out))


@pytest.mark.parametrize("split", ["training", "validation"])
def test_any_reserved_variant_is_rejected_from_development(split):
    row = {"split": split, "style": {"combination": "lichess-blue-staunty"}, "conditions": ["arrow"]}
    with pytest.raises(ValueError, match="Reserved"):
        check_reservation([row], POLICY_DATA["heldOutCombinations"])


def test_merge_preserves_pixels_and_rejects_reserved_pair_tampering(tmp_path, monkeypatch):
    from tools import build_style_dataset
    monkeypatch.setattr(build_style_dataset, "ROOT", tmp_path)
    for cohort, pid, config, rgb in (("parent", "digital-009", "lichess-brown-cburnett-standard", "white"),
                                    ("addition", "digital-001", "lichess-blue-staunty-standard", "gray")):
        image = tmp_path / f"{cohort}.png"
        Image.new("RGB", (512, 512), rgb).save(image)
        record = dict(variant_identity(MANIFEST, pid), image=image.name, sha256=digest(image),
                      configurationId=config, baseConfigurationId=config, orientation="white-bottom",
                      conditions=["clean"], overlayCase="clean", pairId=pid,
                      boardBounds={"x": 0, "y": 0, "width": 512, "height": 512},
                      imageSize={"width": 512, "height": 512})
        build_dataset(tmp_path, [record], MANIFEST, tmp_path / cohort)
    output = tmp_path / "merged"
    merged = merge_datasets(tmp_path / "parent", tmp_path / "addition", output, POLICY_DATA)
    _, rows = read_index(output)
    assert merged["sourceBoardCount"] == 2
    assert [r["cohort"] for r in rows] == ["previous", "expansion"]
    for row in rows:
        assert digest(output / row["array"]) == row["arraySha256"]
        assert digest(tmp_path / row["image"]) == row["sha256"]
        assert len(row["cells"]) == 64
    assert rows[1]["generalization"] is True
    rows[1]["split"] = "training"
    index = output / "verified.jsonl"
    index.write_text("".join(json.dumps(r)+"\n" for r in rows))
    metadata = json.loads((output / "dataset.json").read_text())
    metadata["indexes"]["verified"]["sha256"] = digest(index)
    (output / "dataset.json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="Reserved"):
        read_index(output)


def test_metrics_separate_platform_specific_piece_names_and_held_out_pairs():
    records = []
    for platform, correct in (("lichess", True), ("chesscom", False)):
        row = dict(style={"platform": platform, "pieces": "alpha", "background": "blue", "layout": "desktop",
                          "combination": f"{platform}-blue-alpha", "client": "desktop-web"},
                   orientation="white-bottom", cohort="expansion", generalization=not correct, boardBounds={"width": 512})
        records.append(dict(positionId=platform, pairId=platform, image=f"{platform}.png", conditions=["clean"],
                            expected=[0]*64, predictions=[0 if correct else 1]*64, dimensions=dimensions(row)))
    report = summarize(records)
    assert report["strata"]["pieces"]["lichess/alpha"]["exactBoards"] == 1
    assert report["strata"]["pieces"]["chesscom/alpha"]["exactBoards"] == 0
    assert report["strata"]["generalization"]["held-out-combination"]["images"] == 1
