"""Freeze a digital acceptance policy and new source games before recognition."""

import argparse
from collections import Counter
import json
from pathlib import Path

from tools.capture_lichess import expand_placement
from tools.neural_data import digest
from tools.position_dataset import DEFAULT_MANIFEST, LABELS, ROOT, legacy_families, placement_family
from tools.prepare_positions import generate_sequence


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


def prepare_plan():
    from tools.acceptance_history import consulted, identities
    consumed_games, consumed_families = consulted()
    old = json.loads(DEFAULT_MANIFEST.read_text())
    excluded = legacy_families() | consumed_families | {placement_family(p['piecePlacement']) for p in old['positions']}
    sources = {g['source']['sourceId'] for g in old['groups']}
    groups, positions = [], []
    for seed in range(24001001, 24003001):
        if f'seed-{seed}' in sources:
            continue
        generated = generate_sequence(seed)
        if generated is None:
            continue
        moves, samples = generated
        game_keys, _ = identities({'groups': [{'source': {'initialPosition': 'standard', 'moves': moves}}], 'positions': []})
        if game_keys & consumed_games:
            continue
        families = {placement_family(p) for _, p in samples.values()}
        if len(families) != 4 or families & excluded:
            continue
        excluded.update(families)
        gid = f'acceptance-game-{len(groups)+1:03d}'
        groups.append({'groupId': gid, 'split': 'acceptance', 'source': {
            'sourceId': f'seed-{seed}', 'kind': 'generated-legal-play', 'seed': seed,
            'initialPosition': 'standard', 'moves': moves}})
        for category in ('opening', 'middlegame', 'endgame', 'promotion'):
            ply, placement = samples[category]
            positions.append({'positionId': f'acceptance-{len(positions)+1:03d}',
                              'groupId': gid, 'ply': ply, 'piecePlacement': placement, 'category': category})
        if len(groups) == 10:
            break
    if len(groups) != 10:
        raise ValueError('Could not prepare ten independent source games.')
    counts = Counter((('empty' if symbol == '.' else symbol), (r+c)%2)
                     for p in positions for r, row in enumerate(expand_placement(p['piecePlacement']))
                     for c, symbol in enumerate(row))
    if any(counts[label, color] < 2 for label in LABELS for color in (0, 1)):
        raise ValueError('Insufficient class/background coverage; no recognition was run.')
    return {'schemaVersion': 1, 'datasetId': 'digital-acceptance-v1', 'status': 'reserved-unobserved',
            'previousPlanSha256': digest(DEFAULT_MANIFEST),
            'scope': '40 positions from ten new synthetic legal games; not representative human play',
            'groups': groups, 'positions': positions}


def prepare_policy(model, plan_path):
    configurations = []
    for name in ('capture-digital-clean-v1.json', 'capture-digital-styles-v2.json'):
        configurations.extend(json.loads((ROOT/'tools'/name).read_text())['configurations'])
    return {'schemaVersion': 1, 'policyId': 'digital-acceptance-v1',
            'scope': 'desktop web Lichess editor / Chess.com analysis; controlled overlays and layouts',
            'excluded': ['native-mobile', 'unreviewed-real-game-labels', 'books', 'auto-orientation', 'fully-occluded-pieces'],
            'modelSha256': digest(model), 'planSha256': digest(plan_path),
            'runtimeSha256': {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT/'src/boardsnap').rglob('*.py'))},
            'configurations': configurations,
            'conditions': ['clean', 'last-move', 'selection', 'check', 'circle', 'move-dot',
                           'arrow-empty', 'arrow-piece', 'arrow-crossed', 'arrow-combined'],
            'layouts': ['captured-desktop', 'board-crop-384', 'synthetic-margins-256'],
            'thresholds': {'minimumImages': 4560, 'minimumNegatives': 200,
                'minimumImagesPerCombination': 190, 'minimumImagesPerCondition': 240,
                'minimumImagesPerLayout': 240, 'minimumClassSquares': 100,
                'exactBoardRate': 0.99, 'stratumExactBoardRate': 0.98,
                'classPrecision': 0.995, 'classRecall': 0.995,
                'maximumDetectionMissRate': 0.005, 'maximumFalseDetectionRate': 0.005,
                'minimumBoundsWithinTwoPixelsRate': 0.995,
                'explicitOrientationMappingRate': 1.0,
                'maximumWarmP95Milliseconds': 1000, 'maximumColdMilliseconds': 5000,
                'maximumPeakRssMiB': 1024},
            'cpu': {'torchThreads': 4, 'opencvThreads': 1, 'minimumWarmSamples': 40,
                    'scope': 'Linux CPU; warm full pipeline; cold process includes imports and model; no HTTP'},
            'prerequisites': {'maximumNewRegressionErrors': 0, 'maximumUnresolvedDetectionMisses': 0,
                              'cleanInstallRequired': True},
            'finalEvaluationPolicy': 'Refuse before readiness passes. One exclusive attempt marker; even failed attempts consume the set. Never tune on final results.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--reuse-plan', action='store_true', help='Reuse an existing, still unobserved plan with a new policy')
    args = parser.parse_args()
    if (args.plan.exists() and not args.reuse_plan) or args.policy.exists():
        raise ValueError('Never overwrite a frozen acceptance plan or policy.')
    if args.reuse_plan:
        from tools.acceptance_corpus import validate_plan
        validate_plan(json.loads(args.plan.read_text()))
    else:
        plan = prepare_plan()
        plan['datasetId'] = args.plan.stem
        write_new(args.plan, plan)
    policy = prepare_policy(args.model, args.plan)
    policy['policyId'] = args.policy.stem
    write_new(args.policy, policy)
    print('Frozen policy and 40 new positions. No images recognized; acceptance remains reserved.')


if __name__ == '__main__':
    main()
