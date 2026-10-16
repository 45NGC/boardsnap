"""Train a reproducible CPU baseline, selecting only on validation positions."""

import argparse
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import time

import numpy as np
import torch
from torch import nn

from boardsnap.neural import ARCHITECTURE, CLASSES, PREPROCESSING, SquareNet, load_model, preprocess
from tools.neural_data import digest, load_split, read_index

ROOT = Path(__file__).resolve().parents[1]


def seed_run(config):
    base = {"seed", "epochs", "batchSize", "learningRate", "weightDecay", "threads"}
    if set(config) not in (base, base | {'distillationTemperature', 'distillationWeight'}):
        raise ValueError("Unknown or missing training settings.")
    for key in ('distillationTemperature', 'distillationWeight'):
        if key in config and (type(config[key]) not in (int, float) or not math.isfinite(config[key]) or config[key] <= 0):
            raise ValueError(f'Invalid {key}.')
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
def validate(model, images, labels, batch_size, control_boards=None):
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
    metrics = {"loss": total_loss / len(labels), "squareAccuracy": float(correct.mean()),
            "macroRecall": float(np.mean(recalls)),
            "exactBoards": int(correct.reshape(-1, 64).all(1).sum()), "boards": len(labels) // 64}
    if control_boards is not None:
        if control_boards.dtype != np.bool_ or control_boards.shape != (len(labels)//64,) or not control_boards.any():
            raise ValueError("Validation controls must identify existing whole boards.")
        metrics["controlExactBoards"] = int(correct.reshape(-1, 64).all(1)[control_boards].sum())
        metrics["controlBoards"] = int(control_boards.sum())
    return metrics


def selection_key(metrics):
    return (metrics.get("controlExactBoards", 0), metrics["exactBoards"], metrics["macroRecall"], -metrics["loss"])


def fit(train, validation, config, run, data_version, *, resume=False, stop_after=None, control_boards=None,
        initialize_from=None, teacher_from=None, teacher_mask=None, expansion_teacher_from=None):
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
    initialization = None
    if initialize_from is not None:
        source_model, source_metadata = load_model(initialize_from)
        model.load_state_dict(source_model.state_dict())
        initialization = {'weightsSha256': digest(initialize_from),
                          'dataVersion': source_metadata['dataVersion'],
                          'optimizer': 'new AdamW; previous optimizer state is not inherited'}
    optimizer = torch.optim.AdamW(model.parameters(), lr=config["learningRate"], weight_decay=config["weightDecay"])
    images, labels = train
    teacher_targets = None
    distillation = None
    temperature = config.get('distillationTemperature', 2)
    distillation_weight = config.get('distillationWeight', 1)
    if teacher_from is None and 'distillationTemperature' in config:
        raise ValueError('Distillation settings require teacher weights.')
    if teacher_from is not None:
        if (not isinstance(teacher_mask, np.ndarray) or teacher_mask.dtype != np.bool_
                or teacher_mask.shape != labels.shape or not teacher_mask.any()):
            raise ValueError('Distillation requires an explicit nonempty training-only mask.')
        teacher, teacher_metadata = load_model(teacher_from)
        teacher_targets = np.zeros((len(labels), 13), dtype=np.float32)
        selected = np.flatnonzero(teacher_mask)
        with torch.inference_mode():
            for offset in range(0, len(selected), config['batchSize']):
                indices = selected[offset:offset+config['batchSize']]
                teacher_targets[indices] = (teacher(preprocess(images[indices])) / temperature).softmax(1).numpy()
        distillation = {'teacherSha256': digest(teacher_from), 'dataVersion': teacher_metadata['dataVersion'],
                        'temperature': temperature, 'weight': distillation_weight,
                        'trainingMaskSha256': hashlib.sha256(teacher_mask.tobytes()).hexdigest(),
                        'trainingSquares': int(teacher_mask.sum()),
                        'scope': 'teacher predictions on designated training squares only; no validation/evaluation targets'}
        del teacher
        if expansion_teacher_from is not None:
            if teacher_mask.all():
                raise ValueError('An expansion teacher requires expansion training squares.')
            teacher, teacher_metadata = load_model(expansion_teacher_from)
            selected = np.flatnonzero(~teacher_mask)
            with torch.inference_mode():
                for offset in range(0, len(selected), config['batchSize']):
                    indices = selected[offset:offset+config['batchSize']]
                    teacher_targets[indices] = (teacher(preprocess(images[indices])) / temperature).softmax(1).numpy()
            distillation['expansionTeacher'] = {
                'weightsSha256': digest(expansion_teacher_from), 'dataVersion': teacher_metadata['dataVersion'],
                'trainingSquares': int((~teacher_mask).sum()), 'scope': 'complement of previous-cohort training mask'}
            del teacher
    elif teacher_mask is not None:
        raise ValueError('A teacher mask requires teacher weights.')
    elif expansion_teacher_from is not None:
        raise ValueError('An expansion teacher requires a previous-cohort teacher and training mask.')
    counts = np.bincount(labels, minlength=13)
    if np.any(counts == 0):
        raise ValueError("Training requires all thirteen classes.")
    weights = torch.tensor(len(labels) / (13 * counts), dtype=torch.float32)
    criterion = nn.CrossEntropyLoss(weight=weights)
    metadata = {"formatVersion": 1, "architecture": ARCHITECTURE, "classOrder": list(CLASSES),
                "preprocessing": PREPROCESSING, "dataVersion": data_version, "trainingConfig": config,
                "selection": ("maximum designated validation control exact boards first; " if control_boards is not None else "")
                    + "maximum validation exact boards, then macro recall, then lower unweighted loss; earlier tie",
                "loss": "cross entropy with inverse class frequency from training only",
                "classWeights": weights.tolist(), "environment": {"torch": str(torch.__version__),
                    "numpy": np.__version__, "python": platform.python_version(), "device": "cpu"},
                "parameterCount": sum(p.numel() for p in model.parameters())}
    if initialization is not None:
        metadata['initialization'] = initialization
    if distillation is not None:
        metadata['distillation'] = distillation
    if control_boards is not None:
        if (not isinstance(control_boards, np.ndarray) or control_boards.dtype != np.bool_
                or control_boards.shape != (len(validation[1])//64,) or not control_boards.any()):
            raise ValueError("Validation controls must identify existing whole boards.")
        metadata["validationControlMaskSha256"] = hashlib.sha256(control_boards.tobytes()).hexdigest()
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
            logits = model(preprocess(images[indices]))
            loss = criterion(logits, torch.from_numpy(labels[indices]))
            if teacher_targets is not None:
                keep = np.ones(len(indices), dtype=np.bool_) if expansion_teacher_from is not None else teacher_mask[indices]
                if keep.any():
                    # Preserve the previous expert on its training cohort while
                    # supervised labels teach the expanded catalogue as usual.
                    loss = loss + distillation_weight * temperature**2 * nn.functional.kl_div(
                        (logits[keep] / temperature).log_softmax(1),
                        torch.from_numpy(teacher_targets[indices[keep]]), reduction='batchmean')
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite training loss.")
            loss.backward()
            optimizer.step()
        metrics = validate(model, *validation, config["batchSize"], control_boards=control_boards)
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
    parser.add_argument("--initialize-from", type=Path,
                        help="Fine-tune compatible weights with a new optimizer; keep this argument when resuming")
    parser.add_argument('--teacher', type=Path,
                        help='Preserve previous-cohort training predictions using this compatible model')
    parser.add_argument('--expansion-teacher', type=Path,
                        help='Also preserve expansion-cohort training predictions from this model; requires --teacher')
    parser.add_argument('--extra-training-dataset', type=Path,
                        help='Additional audited variants of existing training sources; validation stays unchanged')
    parser.add_argument("--marked-cells-only", action="store_true",
                        help="Training only: keep marked cells and resize neighbours; retain all clean cells")
    parser.add_argument("--real-dataset", type=Path,
                        help="Optional independently reviewed real-use square dataset; preserve its partitions")
    parser.add_argument("--preserve-controls", action="store_true",
                        help="Prioritize clean/simple-mark whole-board validation accuracy before arrow accuracy")
    parser.add_argument("--control-cohort", choices=("previous",),
                        help="Prioritize every validation board of the previous style cohort, including overlays")
    args = parser.parse_args(argv)
    if args.preserve_controls and args.control_cohort:
        parser.error("Choose one validation control policy.")
    if args.teacher and args.control_cohort != 'previous':
        parser.error('--teacher requires --control-cohort previous.')
    if args.teacher and args.real_dataset:
        parser.error('Teacher cohort alignment with an additional real dataset is not implemented.')
    if args.expansion_teacher and not args.teacher:
        parser.error('--expansion-teacher requires --teacher.')
    if args.extra_training_dataset and (args.teacher or args.real_dataset):
        parser.error('Extra training variants currently require supervised training without teachers or a real-data addition.')
    config = json.loads(args.config.read_text())
    seed_run(config)
    metadata, rows = read_index(args.dataset)
    print("Loading verified training and validation arrays; evaluation arrays remain unopened.", flush=True)
    train = load_split(args.dataset, rows, "training", marked_cells_only=args.marked_cells_only)
    extra_version = None
    if args.extra_training_dataset:
        from tools.training_augmentation import add_training_variants
        train, extra_version = add_training_variants(args.extra_training_dataset, rows, train,
                                                     marked_cells_only=args.marked_cells_only)
    validation = load_split(args.dataset, rows, "validation")
    real_version = None
    if args.real_dataset:
        from tools.real_training import add_real_training
        train, validation, real_version = add_real_training(args.real_dataset, rows, train, validation)
    data_version = {"datasetId": metadata["datasetId"], "manifestSha256": digest(args.dataset / "dataset.json"),
                    "verifiedIndexSha256": metadata["indexes"]["verified"]["sha256"],
                    "trainingBoards": sum(row["split"] == "training" for row in rows)
                        + (real_version["trainingBoards"] if real_version else 0)
                        + (extra_version['trainingBoards'] if extra_version else 0),
                    "trainingSquares": len(train[1]), "validationBoards": len(validation[1]) // 64,
                    "markedCellsOnlyInTraining": args.marked_cells_only,
                    "trainingCodeSha256": digest(Path(__file__)),
                    "dataLoaderCodeSha256": digest(ROOT / "tools/neural_data.py"),
                    "modelCodeSha256": digest(ROOT / "src/boardsnap/neural.py")}
    if extra_version is not None:
        data_version['trainingAugmentation'] = extra_version
        data_version['augmentationLoaderCodeSha256'] = digest(ROOT/'tools/training_augmentation.py')
    if real_version is not None:
        data_version["reviewedRealData"] = real_version
        data_version["realLoaderCodeSha256"] = digest(ROOT / "tools/real_training.py")
    controls = None
    teacher_mask = None
    if args.teacher:
        from tools.neural_data import training_indices
        teacher_mask = np.concatenate([
            np.full(len(training_indices(r)) if args.marked_cells_only else 64,
                    r.get('cohort') == 'previous', dtype=np.bool_)
            for r in rows if r['split'] == 'training'])
    if args.preserve_controls or args.control_cohort:
        validation_rows = [r for r in rows if r["split"] == "validation"]
        if args.real_dataset:
            _, real_rows = read_index(args.real_dataset)
            validation_rows.extend(r for r in real_rows if r["split"] == "validation")
        controls = np.asarray([r.get("cohort") == args.control_cohort if args.control_cohort else
                               not any(c in ("arrow", "arrows") for c in r.get("conditions", []))
                               for r in validation_rows], dtype=np.bool_)
        data_version["validationControlBoards"] = int(controls.sum())
        # The array order is pinned by the parent/real index hashes above.
        data_version["controlSelectionPolicy"] = (f"cohort={args.control_cohort}; include all conditions"
            if args.control_cohort else "conditions without arrow/arrows; retain all clean/simple controls")
    fit(train, validation, config, args.run, data_version, resume=args.resume, control_boards=controls,
        initialize_from=args.initialize_from, teacher_from=args.teacher, teacher_mask=teacher_mask,
        expansion_teacher_from=args.expansion_teacher)


if __name__ == "__main__":
    main()
