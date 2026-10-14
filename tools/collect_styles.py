"""Capture the next style group while excluding reserved pairs from development."""

import argparse
import json
from pathlib import Path

from tools.collect_clean_corpus import build_jobs, collect, audit_corpus
from tools.position_dataset import DEFAULT_MANIFEST

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "tools/capture-digital-styles-v2.json"
POLICY = ROOT / "data/manifests/digital-styles-v2.json"


def style_jobs(manifest, recipe, policy):
    reserved = policy["heldOutCombinations"]
    configs = {c["id"] for c in recipe["configurations"]}
    if not reserved or len(set(reserved)) != len(reserved) or not set(reserved) < configs:
        raise ValueError("Reserve distinct known combinations while retaining development combinations.")
    groups = {g["groupId"]: g["split"] for g in manifest["groups"]}
    splits = {p["positionId"]: groups[p["groupId"]] for p in manifest["positions"]}
    jobs = []
    for job in build_jobs(manifest, recipe):
        base = job["configurations"][0]["id"].rsplit("-", 1)[0]
        if base in reserved:
            job["positionIds"] = [pid for pid in job["positionIds"] if splits[pid] == "evaluation"]
        if job["positionIds"]:
            job["batchId"] = job["batchId"].replace("clean-", "styles-", 1)
            jobs.append(job)
    return jobs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    manifest = json.loads(DEFAULT_MANIFEST.read_text())
    recipe, policy = json.loads(RECIPE.read_text()), json.loads(POLICY.read_text())
    jobs = style_jobs(manifest, recipe, policy)
    args.report.unlink(missing_ok=True)
    if not args.audit_only:
        collect(manifest, jobs, args.output_root)
    report = audit_corpus(manifest, recipe, jobs, args.output_root)
    report.update(stylePolicy=policy)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Captured and audited {report['imageCount']} images.")


if __name__ == "__main__":
    main()
