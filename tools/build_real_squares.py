"""Build classification squares only from previously reviewed real-use imports."""

import argparse
import json
from pathlib import Path

from tools.build_square_dataset import build_dataset
from tools.capture_batch import check_real_isolation
from tools.neural_data import digest
from tools.position_dataset import DEFAULT_MANIFEST, validate_manifest


def build_real_squares(root, manifest, output):
    check_real_isolation(root, [], manifest)
    records, batches = [], []
    for path in sorted(root.glob("*/batch.json")):
        batch = json.loads(path.read_text())
        for sample in batch["samples"]:
            if sample["provenanceKind"] != "reviewed-real-use":
                continue
            record = dict(sample, image=str(path.parent.relative_to(root) / sample["split"] / "real-use" / sample["image"]),
                          configurationId=Path(sample["image"]).stem,
                          conditions=sample["configuration"]["conditions"])
            records.append(record)
        batches.append({"batch": str(path.relative_to(root)), "sha256": digest(path)})
    if not records:
        raise ValueError("No reviewed real-use imports; predictions are not ground truth.")
    return build_dataset(root.resolve(), records, manifest, output,
                         provenance={"datasetId": "real-use-squares-v1", "reviewedBatches": batches})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--imports", type=Path, required=True, help="Dataset directory containing imported batches")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = json.loads(args.manifest.read_text())
    validate_manifest(manifest)
    build_real_squares(args.imports, manifest, args.output)


if __name__ == "__main__":
    main()
