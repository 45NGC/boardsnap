"""Remember consulted source games independently of cache directory names."""

import hashlib
import json
from pathlib import Path

from tools.position_dataset import ROOT, placement_family

HISTORY = ROOT / 'data/reports/acceptance-attempts'


def identities(plan):
    games = {hashlib.sha256(json.dumps({
        'initialPosition': group['source']['initialPosition'],
        'moves': group['source']['moves'],
    }, sort_keys=True).encode()).hexdigest() for group in plan['groups']}
    families = {placement_family(p['piecePlacement']) for p in plan['positions']}
    return games, families


def consulted(history=HISTORY):
    games, families = set(), set()
    for path in sorted(history.glob('*.json')):
        record = json.loads(path.read_text())
        games.update(record['games'])
        families.update(record['families'])
    return games, families


def require_unobserved(plan, history=HISTORY):
    games, families = identities(plan)
    old_games, old_families = consulted(history)
    # Reviewed video examples are development data, even under new filenames,
    # group IDs, orientations or equivalent piece-placement transformations.
    from tools.development_cases import load_cases
    development = load_cases(verify_images=False)['samples']
    old_families.update(placement_family(row['piecePlacement']) for row in development)
    known_groups = {row['sourceGroupId'] for row in development}
    if any(group['groupId'] in known_groups or group['source'].get('sourceId') in known_groups
           for group in plan['groups']):
        raise ValueError('Development source groups cannot enter independent acceptance.')
    if games & old_games or families & old_families:
        raise ValueError('Acceptance sources were already consulted; prepare an independent plan.')


def consume(plan, policy_hash, model_hash, history=HISTORY):
    """Retain this ledger with reports, including after a failed/crashed run."""
    history.mkdir(parents=True, exist_ok=True)
    # Exclusive lock prevents simultaneous attempts with overlapping source sets.
    lock = history / '.lock'
    with lock.open('x'):
        try:
            require_unobserved(plan, history)
            games, families = identities(plan)
            key = hashlib.sha256('\n'.join(sorted(games)).encode()).hexdigest()
            with (history / f'{key}.json').open('x') as stream:
                json.dump({'games': sorted(games), 'families': sorted(families),
                           'policySha256': policy_hash, 'modelSha256': model_hash,
                           'status': 'consulted, including if evaluation fails'}, stream, indent=2)
                stream.write('\n')
        finally:
            lock.unlink()
