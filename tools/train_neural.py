"""Train a reproducible CPU baseline, selecting only on validation positions."""

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import platform
import random
import time

import numpy as np
import torch
from torch import nn

from boardsnap.neural import ARCHITECTURE, CLASSES, PREPROCESSING, SquareNet, preprocess
from tools.neural_data import digest, load_split, read_index

ROOT = Path(__file__).resolve().parents[1]


def seed_run(config):
    if set(config) != {"seed", "epochs", "batchSize", "learningRate", "weightDecay", "threads"}:
        raise ValueError("Unknown or missing training settings.")
    for key in ("seed", "epochs", "batchSize", "threads"):
        if type(config[key]) is not int or config[key] <= 0:
            raise ValueError(f"Invalid {key}.")
    if config["learningRate"] <= 0 or config["weightDecay"] < 0:
        raise ValueError("Invalid optimizer settings.")
    random.seed(config["seed"])
    np.random.seed(config["seed"])
    torch.manual_seed(config["seed"])
    torch.set_num_threads(config["threads"])
    torch.use_deterministic_algorithms(True)


def atomic_save(value, path):
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(value, temporary)
    os.replace(temporary, path)


@torch.inference_mode()
def validate(model, images, labels, batch_size):
    model.eval()
    guesses, total_loss = [], 0.0
    for start in range(0, len(images), batch_size):
        target = torch.from_numpy(labels[start:start + batch_size])
        logits = model(preprocess(images[start:start + batch_size]))
        total_loss += nn.functional.cross_entropy(logits, target, reduction="sum").item()
        guesses.append(logits.argmax(1).numpy())
    predictions = np.concatenate(guesses)
    correct = predictions == labels
    recalls = [float(correct[labels == i].mean()) for i in range(13) if np.any(labels == i)]
    return {"loss": total_loss / len(labels), "squareAccuracy": float(correct.mean()),
            "macroRecall": float(np.mean(recalls)),
            "exactBoards": int(correct.reshape(-1, 64).all(1).sum()), "boards": len(labels) // 64}


def selection_key(metrics):
    return (metrics["exactBoards"], metrics["macroRecall"], -metrics["loss"])


def fit(train, validation, config, run, data_version, *, resume=False, stop_after=None):
    """Checkpoint every completed epoch; deterministic shuffle is seed + epoch.

    stop_after supports interrupted-run tests without changing the frozen horizon.
    Resuming repeats only an unfinished epoch and rejects data/config changes.
    """
    seed_run(config)
    run.mkdir(parents=True, exist_ok=True)
    checkpoint = run / "last.pt"
    if checkpoint.exists() and not resume:
        raise ValueError("Run exists; use --resume or a new run directory.")
    if resume and not checkpoint.exists():
        raise ValueError("No checkpoint to resume.")
    model = SquareNet()
    optimizer = torch.optim.AdamW(model.parameters(), lr=config["learningRate"], weight_decay=config["weightDecay"])
    images, labels = train
    counts = np.bincount(labels, minlength=13)
    if np.any(counts == 0):
        raise ValueError("Training requires all thirteen classes.")
    weights = torch.tensor(len(labels) / (13 * counts), dtype=torch.float32)
    criterion = nn.CrossEntropyLoss(weight=weights)
    metadata = {"formatVersion": 1, "architecture": ARCHITECTURE, "classOrder": list(CLASSES),
                "preprocessing": PREPROCESSING, "dataVersion": data_version, "trainingConfig": config,
                "selection": "maximum validation exact boards, then macro recall, then lower unweighted loss; earlier tie",
                "loss": "cross entropy with inverse class frequency from training only",
                "classWeights": weights.tolist(), "environment": {"torch": str(torch.__version__),
                    "numpy": np.__version__, "python": platform.python_version(), "device": "cpu"},
                "parameterCount": sum(p.numel() for p in model.parameters())}
    start_epoch, history, best, best_state = 0, [], None, None
    if resume:
        saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
        if saved["metadata"] != metadata:
            raise ValueError("Checkpoint data, configuration or environment changed.")
        model.load_state_dict(saved["state_dict"])
        optimizer.load_state_dict(saved["optimizer"])
        torch.set_rng_state(saved["rngState"])
        start_epoch, history, best, best_state = saved["epoch"], saved["history"], saved["best"], saved["bestState"]
    for epoch in range(start_epoch, min(config["epochs"], stop_after or config["epochs"])):
        started = time.perf_counter()
        model.train()
        order = np.random.default_rng(config["seed"] + epoch).permutation(len(labels))
        for offset in range(0, len(order), config["batchSize"]):
            indices = order[offset:offset + config["batchSize"]]
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(preprocess(images[indices])), torch.from_numpy(labels[indices]))
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite training loss.")
            loss.backward()
            optimizer.step()
        metrics = validate(model, *validation, config["batchSize"])
        if best is None or selection_key(metrics) > selection_key(best["metrics"]):
            best = {"epoch": epoch + 1, "metrics": metrics}
            best_state = deepcopy(model.state_dict())
        history.append({"epoch": epoch + 1, "validation": metrics, "seconds": time.perf_counter() - started})
        atomic_save({"metadata": metadata, "state_dict": model.state_dict(), "optimizer": optimizer.state_dict(),
                     "rngState": torch.get_rng_state(), "epoch": epoch + 1, "history": history,
                     "best": best, "bestState": best_state}, checkpoint)
        print(f"Epoch {epoch + 1}/{config['epochs']}: validation {metrics['exactBoards']}/{metrics['boards']} boards, "
              f"{metrics['squareAccuracy']:.4%} squares; {history[-1]['seconds']:.1f}s", flush=True)
    atomic_save({"metadata": dict(metadata, selectedEpoch=best["epoch"]), "state_dict": best_state}, run / "best.pt")
    report = {"metadata": metadata, "completedEpochs": len(history), "selected": best, "history": history,
              "complete": len(history) == config["epochs"], "weightsSha256": digest(run / "best.pt"),
              "evaluationUsedForSelection": False, "templatesRemainDefault": True}
    (run / "training.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "tools/train-clean-v1.json")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text())
    seed_run(config)
    metadata, rows = read_index(args.dataset)
    print("Loading verified training and validation arrays; evaluation arrays remain unopened.", flush=True)
    train = load_split(args.dataset, rows, "training")
    validation = load_split(args.dataset, rows, "validation")
    data_version = {"datasetId": metadata["datasetId"], "manifestSha256": digest(args.dataset / "dataset.json"),
                    "verifiedIndexSha256": metadata["indexes"]["verified"]["sha256"],
                    "trainingBoards": len(train[1]) // 64, "validationBoards": len(validation[1]) // 64,
                    "trainingCodeSha256": digest(Path(__file__)),
                    "modelCodeSha256": digest(ROOT / "src/boardsnap/neural.py")}
    fit(train, validation, config, args.run, data_version, resume=args.resume)


if __name__ == "__main__":
    main()
