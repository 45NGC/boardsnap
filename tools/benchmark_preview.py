"""Measure frozen preview models on consulted validation in a fresh CPU process."""

import argparse
from collections import defaultdict, deque
import json
from pathlib import Path

from tools.verify_preview import sha256

ROOT = Path(__file__).resolve().parents[1]


def validation_samples(mode):
    if mode == 'photo':
        manifest = ROOT / 'data/manifests/phone-validation-v1.json'
        rows = json.loads(manifest.read_text())['samples']
        samples = [dict(id=r['id'], image=str(ROOT/r['imagePath']), imageSha256=r['imageSha256'],
                        orientation=r['label']['orientation'], piecePlacement=r['label']['piecePlacement'],
                        split=r['split'], groupId=r['groupId']) for r in rows]
        provenance = {str(manifest.relative_to(ROOT)): sha256(manifest)}
    elif mode == 'digital':
        dataset = ROOT / '.cache/digital-style-squares-v2'
        metadata = json.loads((dataset/'dataset.json').read_text())
        buckets, seen = defaultdict(deque), set()
        with (dataset/'verified.jsonl').open() as stream:
            for line in stream:
                row = json.loads(line)
                if row['split'] != 'validation' or row['image'] in seen:
                    continue
                seen.add(row['image'])
                key = (row['style']['platform'], tuple(row['conditions']), row['style']['layout'])
                buckets[key].append(dict(id=row['image'], image=str(Path(metadata['sourceRoot'])/row['image']),
                    imageSha256=row['sha256'], orientation=row['orientation'], piecePlacement=row['piecePlacement'],
                    split=row['split'], groupId=row['groupId']))
        samples = []
        while len(samples) < 40 and any(buckets.values()):
            for key in sorted(buckets):
                if buckets[key] and len(samples) < 40:
                    samples.append(buckets[key].popleft())
        provenance = {str((dataset/name).relative_to(ROOT)): sha256(dataset/name)
                      for name in ('dataset.json', 'verified.jsonl')}
    else:
        raise ValueError('Unsupported input type.')
    for row in samples:
        if row['split'] != 'validation':
            raise ValueError('Only consulted validation may be benchmarked.')
        if sha256(row['image']) != row['imageSha256']:
            raise ValueError('Benchmark image changed.')
    return samples, provenance


def performance_passed(report, limits):
    import math
    values = [(report['warm']['samples'], limits['minimumSamples'], True),
              (report['warm']['p95Milliseconds'], limits['warmP95Ms'], False),
              (report['coldMilliseconds'], limits['coldMs'], False),
              (report['peakRssMiB'], limits['peakRssMiB'], False)]
    return all(type(value) in (int, float) and math.isfinite(value) and value >= 0
               and (value >= threshold if minimum else value <= threshold)
               for value, threshold, minimum in values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--input-type', choices=('digital', 'photo'), required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Preserve existing measurements; choose a new output path.')
    policy = json.loads(args.policy.read_text())
    if sha256(args.model) != policy['models'][args.input_type]['sha256']:
        raise ValueError('Model differs from the frozen candidate.')
    samples, provenance = validation_samples(args.input_type)
    from tools.benchmark_cpu import benchmark
    result = benchmark(args.model, samples, input_type=args.input_type)
    import boardsnap
    result.update(samples=samples, provenance=provenance, policySha256=sha256(args.policy),
                  benchmarkSha256={name: sha256(ROOT/name) for name in ('tools/benchmark_cpu.py', 'tools/benchmark_preview.py')},
                  runtimeLocation=boardsnap.__file__, finalEvaluationAccessed=False,
                  performancePassed=performance_passed(result, policy['cpu'][args.input_type]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        stream.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('warm', 'coldMilliseconds', 'peakRssMiB', 'correctImages', 'performancePassed')}))


if __name__ == '__main__':
    main()
