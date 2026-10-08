"""Collect and audit the fixed clean corpus in resumable, atomic source-group batches."""

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

from tools.capture_batch import check_png, plan_hash, record_capture, run_batch, validate_recipe
from tools.capture_lichess import expand_placement
from tools.position_dataset import DEFAULT_MANIFEST, validate_manifest, variant_identity

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECIPE = ROOT / 'tools/capture-digital-clean-v1.json'


def build_jobs(manifest, recipe):
    """80 base positions plus one compact position per group, chosen before capture."""
    validate_manifest(manifest)
    validate_recipe(recipe, manifest)
    if set(recipe['positionIds']) != {p['positionId'] for p in manifest['positions']}:
        raise ValueError('The collection recipe must include the complete frozen position plan.')
    groups = sorted(manifest['groups'], key=lambda g: g['groupId'])
    positions = {g['groupId']: [p['positionId'] for p in manifest['positions'] if p['groupId'] == g['groupId']]
                 for g in groups}
    jobs = []
    for base in recipe['configurations']:
        for size in ('standard', 'compact'):
            config = deepcopy(base)
            config['id'] = f"{base['id']}-{size}"
            if size == 'compact':
                config['viewport'] = {'width': 1024, 'height': 900}
            for index, group in enumerate(groups):
                ids = positions[group['groupId']]
                if size == 'compact':
                    ids = [ids[index % len(ids)]]
                job = {'schemaVersion': 1,
                       'batchId': f"clean-{config['id']}-{group['groupId']}",
                       'positionIds': ids, 'configurations': [config]}
                validate_recipe(job, manifest)
                jobs.append(job)
    return jobs


def audit_batch(target, manifest, recipe):
    """Reject stale, incomplete, edited or differently labeled checkpoint batches."""
    batch = json.loads((target / 'batch.json').read_text())
    if batch['recipe'] != recipe or batch['positionPlanSha256'] != plan_hash(manifest):
        raise ValueError(f'Checkpoint uses another recipe or position plan: {target}')
    expected = {(pid, c['id'], view): c for pid in recipe['positionIds']
                for c in recipe['configurations'] for view in c['orientations']}
    records, seen, paths = [], set(), set()
    for ann in batch['samples']:
        key = (ann['positionId'], ann['configuration']['id'], ann['orientation'])
        if key not in expected or key in seen or ann['configuration'] != expected[key]:
            raise ValueError('Unexpected or duplicated capture configuration/position/view.')
        seen.add(key)
        config = expected[key]
        identity = variant_identity(manifest, ann['positionId'])
        if any(ann.get(k) != v for k, v in identity.items()):
            raise ValueError('Capture label or partition differs from frozen identity.')
        filename = f"{ann['positionId']}-{ann['orientation']}.png"
        relative = Path(ann['split']) / config['id'] / filename
        if ann['image'] != filename:
            raise ValueError('Image filename does not describe this capture.')
        path = target / relative
        if json.loads(path.with_suffix('.json').read_text()) != ann:
            raise ValueError('Sidecar differs from batch annotation.')
        png = path.read_bytes()
        if hashlib.sha256(png).hexdigest() != ann['sha256']:
            raise ValueError('PNG hash differs from its verified annotation.')
        factor = config['deviceScaleFactor']
        size = (config['viewport']['width'] * factor, config['viewport']['height'] * factor)
        if check_png(png, ann['boardBounds'], size) != ann['imageSize']:
            raise ValueError('PNG dimensions do not match the annotation.')
        source = ann['source']
        if {k: v * factor for k, v in source['cssBoardBounds'].items()} != ann['boardBounds']:
            raise ValueError('DOM bounds and PNG bounds disagree.')
        rows = expand_placement(identity['piecePlacement'])
        if ann['orientation'] == 'black-bottom':
            rows = [r[::-1] for r in rows[::-1]]
        if source['renderedRows'] != rows or source['renderedOrientation'] != ann['orientation']:
            raise ValueError('Recorded rendered pieces/view disagree with position label.')
        paths.add(relative)
        records.append({'image': str(Path(target.name) / relative), 'sha256': ann['sha256'],
                        **identity, 'configurationId': config['id'], 'orientation': ann['orientation'],
                        'boardBounds': ann['boardBounds'], 'imageSize': ann['imageSize']})
    if seen != set(expected) or {p.relative_to(target) for p in target.rglob('*.png')} != paths:
        raise ValueError('Batch has missing or unexpected images.')
    if {p.relative_to(target) for p in target.rglob('*.json')} != {Path('batch.json'), *(p.with_suffix('.json') for p in paths)}:
        raise ValueError('Batch has missing or unexpected annotations.')
    return records


def collect(manifest, jobs, output_root):
    from playwright.sync_api import sync_playwright
    from tools.capture_sites import CaptureSession

    dataset_root = output_root / manifest['datasetId']
    context, session, config_id = None, None, None
    with sync_playwright() as engine:
        browser = engine.chromium.launch()
        try:
            for index, job in enumerate(jobs):
                target = dataset_root / job['batchId']
                config = job['configurations'][0]
                if target.exists():
                    audit_batch(target, manifest, job)
                    print(f'[{index+1}/{len(jobs)}] Verified existing {job["batchId"]}', flush=True)
                    continue
                for attempt in range(3):
                    try:
                        if config_id != config['id'] or session is None:
                            if context:
                                context.close()
                            context = browser.new_context(viewport=config['viewport'], device_scale_factor=config['deviceScaleFactor'],
                                                          locale='en-GB', color_scheme='light')
                            page = context.new_page()
                            page.set_default_timeout(30000)
                            session = CaptureSession(page, config)
                            config_id = config['id']

                        def capture(staging, plan, specification, headed):
                            annotations = []
                            for pid in specification['positionIds']:
                                placement = variant_identity(plan, pid)['piecePlacement']
                                for view in config['orientations']:
                                    png, observed = session.capture(placement, view)
                                    annotations.append(record_capture(staging, plan, pid, config, view, png, observed, browser.version))
                            return annotations

                        target = run_batch(manifest, job, output_root,
                                           capture_fn=capture, audit_fn=audit_batch)
                        break
                    except Exception as error:
                        # Failed staging is discarded by run_batch. A bad published
                        # checkpoint must never be treated as resumable success.
                        if target.exists() or attempt == 2:
                            raise
                        print(f'Retrying {job["batchId"]}: {error}', file=sys.stderr, flush=True)
                        session = None
                print(f'[{index+1}/{len(jobs)}] Captured {job["batchId"]}',flush=True)
        finally:
            if context:
                context.close()
            browser.close()


def audit_corpus(manifest, recipe, jobs, output_root):
    dataset_root = output_root / manifest['datasetId']
    if {p.parent.name for p in dataset_root.glob('*/batch.json')} != {j['batchId'] for j in jobs}:
        raise ValueError('Corpus contains missing or unexpected batches; use a dedicated output root.')
    records = [r for job in jobs for r in audit_batch(dataset_root / job['batchId'], manifest, job)]
    hashes, groups = {}, {}
    for row in records:
        identity = (row['groupId'], row['split'], row['piecePlacement'])
        if hashes.setdefault(row['sha256'], identity) != identity or groups.setdefault(row['groupId'], row['split']) != row['split']:
            raise ValueError('Duplicate PNG identities or source groups cross partitions.')
    return {'schemaVersion':1,'datasetId':manifest['datasetId'],'stage':'capture-integrity-only',
            'complete':True,'positionPlanSha256':plan_hash(manifest),'baseRecipeSha256':plan_hash(recipe),
            'outputRoot':str(output_root),'batchCount':len(jobs),'imageCount':len(records),
            'positionCount':len({r['positionId'] for r in records}),'sourceGroupCount':len(groups),
            'splitCounts':dict(Counter(r['split'] for r in records)),
            'configurationCounts':dict(Counter(r['configurationId'] for r in records)),
            'sizePolicy':'standard: all 80; compact: sorted source group index modulo four selects one of its four positions',
            'modelTrained':False,'classificationEvaluated':False,'images':records}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument('--recipe', type=Path, default=DEFAULT_RECIPE)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--audit-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text())
        recipe = json.loads(args.recipe.read_text())
        jobs = build_jobs(manifest, recipe)
        # Remove a stale success report before attempting to verify/extend data.
        args.report.unlink(missing_ok=True)
        if not args.audit_only:
            collect(manifest, jobs, args.output_root)
        report = audit_corpus(manifest, recipe, jobs, args.output_root)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
        print(f'Complete: {report["imageCount"]} verified PNG/JSON pairs; {args.report}')
        return 0
    except Exception as error:
        print(f'Collection incomplete: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
