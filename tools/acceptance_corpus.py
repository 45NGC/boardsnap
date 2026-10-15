"""Capture a reserved digital corpus without importing a classifier or model."""

import argparse
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import random
import tempfile

from PIL import Image, ImageDraw

from tools.arrow_marks import CASES, arrow_plan
from tools.board_marks import KINDS, mark_plan, mark_png
from tools.capture_batch import plan_hash, record_capture, validate_config
from tools.collect_clean_corpus import audit_batch, audit_corpus
from tools.neural_data import digest
from tools.position_dataset import DEFAULT_MANIFEST, legacy_families, placement_family


def validate_plan(plan):
    """Reject consulted positions and source games, including equivalent diagrams."""
    import chess
    from tools.acceptance_history import require_unobserved
    require_unobserved(plan)
    old = json.loads(DEFAULT_MANIFEST.read_text())
    if plan['previousPlanSha256'] != digest(DEFAULT_MANIFEST):
        raise ValueError('The earlier source plan changed.')
    if len(plan['positions']) != 40 or len(plan['groups']) != 10:
        raise ValueError('Acceptance requires forty positions in ten source games.')
    families = legacy_families() | {placement_family(p['piecePlacement']) for p in old['positions']}
    sources = {g['source']['sourceId'] for g in old['groups']}
    groups, ids = set(), set()
    for group in plan['groups']:
        if group['split'] != 'acceptance' or group['groupId'] in groups or group['source']['sourceId'] in sources:
            raise ValueError('Acceptance source games must be independent and reserved.')
        groups.add(group['groupId'])
        sources.add(group['source']['sourceId'])
        selected = {p['ply']:p for p in plan['positions'] if p['groupId']==group['groupId']}
        if len(selected)!=4 or {p['category'] for p in selected.values()} != {'opening','middlegame','endgame','promotion'}:
            raise ValueError('Each game requires four distinct categories.')
        board = chess.Board()
        for ply, move in enumerate(group['source']['moves'],1):
            board.push_uci(move)
            if ply in selected:
                p=selected.pop(ply)
                if board.board_fen()!=p['piecePlacement'] or p['positionId'] in ids:
                    raise ValueError('Acceptance position differs from its source moves.')
                ids.add(p['positionId'])
                family=placement_family(p['piecePlacement'])
                if family in families:
                    raise ValueError('Acceptance overlaps consulted or equivalent positions.')
                families.add(family)
        if selected:
            raise ValueError('Source moves are incomplete.')
    if len(ids)!=40:
        raise ValueError('Unassigned acceptance positions.')


def jobs_for(plan, policy):
    jobs=[]
    for base in policy['configurations']:
        for index, group in enumerate(plan['groups']):
            config=deepcopy(base)
            size='compact' if index%2 else 'standard'
            config['id']=f"{base['id']}-{size}"
            if size=='compact': config['viewport']={'width':1024,'height':900}
            validate_config(config)
            jobs.append({'schemaVersion':1,'batchId':f"accept-{config['id']}-{group['groupId']}",
                         'configurations':[config], 'positionIds':[p['positionId'] for p in plan['positions'] if p['groupId']==group['groupId']]})
    return jobs


def capture(plan, jobs, root):
    from playwright.sync_api import sync_playwright
    from tools.capture_sites import CaptureSession
    placements={p['positionId']:p['piecePlacement'] for p in plan['positions']}
    dataset=root/plan['datasetId']
    dataset.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as engine:
        browser=engine.chromium.launch()
        try:
            for number, job in enumerate(jobs,1):
                target=dataset/job['batchId']
                if target.exists():
                    audit_batch(target,plan,job)
                    continue
                config=job['configurations'][0]
                context=browser.new_context(viewport=config['viewport'],device_scale_factor=config['deviceScaleFactor'],
                                            locale='en-GB',color_scheme='light')
                try:
                    page=context.new_page()
                    page.set_default_timeout(30000)
                    session=CaptureSession(page,config)
                    with tempfile.TemporaryDirectory(dir=dataset,prefix='.capture-') as tmp:
                        stage=Path(tmp)
                        samples=[]
                        for pid in job['positionIds']:
                            for view in config['orientations']:
                                png, observed=session.capture(placements[pid],view)
                                samples.append(record_capture(stage,plan,pid,config,view,png,observed,browser.version))
                        (stage/'batch.json').write_text(json.dumps({'recipe':job,'positionPlanSha256':plan_hash(plan),'samples':samples},indent=2)+'\n')
                        audit_batch(stage,plan,job)
                        stage.rename(target)
                finally:
                    context.close()
                print(f'Captured {number}/{len(jobs)} reserved batches',flush=True)
        finally:
            browser.close()


def derive(plan, policy, capture_root, output, policy_hash, plan_hash_value):
    if output.exists(): raise ValueError('Never overwrite a reserved corpus.')
    jobs=jobs_for(plan,policy)
    audit=audit_corpus(plan,{'configurations':policy['configurations']},jobs,capture_root)
    representatives={}
    for i, group in enumerate(plan['groups']):
        p=[p for p in plan['positions'] if p['groupId']==group['groupId']][i%4]
        representatives[group['groupId']]=(p['positionId'],('white-bottom','black-bottom')[i%2])
    positives, negatives=[],[]
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='.acceptance-') as tmp:
        stage=Path(tmp)
        def save(row,png):
            path=stage/'images'/f'{len(positives):05d}.png'
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(png)
            positives.append(dict(row,image=str(path.relative_to(stage)),sha256=digest(path)))
        for row in audit['images']:
            combo=row['configurationId'].rsplit('-',1)[0]
            base=next(c for c in policy['configurations'] if c['id']==combo)
            png=(capture_root/plan['datasetId']/row['image']).read_bytes()
            common=dict(row,combination=combo,platform=base['platform'],pieces=base['pieceSet'],
                        background=base['boardTheme'],layout='captured-desktop',condition='clean')
            save(common,png)
            if (row['positionId'],row['orientation'])!=representatives[row['groupId']]:continue
            for case in (*KINDS,*CASES):
                key=f"acceptance-v1:{combo}:{row['positionId']}:{case}"
                marks=arrow_plan(row['piecePlacement'],case,key)[0] if case in CASES else mark_plan(row['piecePlacement'],case,key)
                if marks is None:raise ValueError('Required arrow scenario cannot be rendered; do not omit it.')
                marked,evidence=mark_png(png,row['boardBounds'],row['orientation'],marks,row['piecePlacement'])
                save(dict(common,condition=case,marks=marks,augmentation=evidence),marked)
            from tools.build_square_dataset import raster_bounds
            for layout,side,margin in [('board-crop-384',384,0),('synthetic-margins-256',256,64)]:
                with Image.open(BytesIO(png)) as image, image.crop(raster_bounds(row['boardBounds']).as_box()) as crop:
                    with crop.resize((side,side),Image.Resampling.LANCZOS) as resized, Image.new('RGB',(side+2*margin,side+2*margin),(45,49,55)) as canvas:
                        canvas.paste(resized,(margin,margin))
                        buffer=BytesIO(); canvas.save(buffer,format='PNG')
                save(dict(common,layout=layout,boardBounds={'x':margin,'y':margin,'width':side,'height':side},
                          imageSize={'width':side+2*margin,'height':side+2*margin}),buffer.getvalue())
        rng=random.Random(24001001)
        for i in range(240):
            rows,cols=[(6,6),(7,7),(9,9),(10,10),(7,8),(0,0)][i%6]
            side=rng.choice([24,32,48,64])
            colors=[tuple(rng.randrange(30,240) for _ in range(3)) for _ in range(2)]
            with Image.new('RGB',(800,700),(47,51,59)) as image:
                draw=ImageDraw.Draw(image)
                for r in range(rows):
                    for c in range(cols):draw.rectangle((40+c*side,40+r*side,39+(c+1)*side,39+(r+1)*side),fill=colors[(r+c)%2])
                if not rows:
                    for j in range(15):draw.rectangle((40,20+40*j,rng.randrange(150,700),35+40*j),fill=colors[j%2])
                path=stage/f'negative-{i:03d}.png'; image.save(path)
            negatives.append({'image':path.name,'sha256':digest(path),'kind':f'{rows}x{cols}' if rows else 'interface-blocks'})
        if len(positives)!=4560:raise ValueError('Incomplete positive acceptance coverage.')
        result={'schemaVersion':1,'status':'reserved-unobserved','policySha256':policy_hash,'planSha256':plan_hash_value,
                'positives':positives,'negatives':negatives,'captureAuditSha256':plan_hash(audit),
                'generationCodeSha256':digest(Path(__file__))}
        (stage/'corpus.json').write_text(json.dumps(result,indent=2)+'\n')
        stage.rename(output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy',type=Path,required=True)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--capture-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    plan=json.loads(args.plan.read_text()); policy=json.loads(args.policy.read_text())
    if digest(args.plan)!=policy['planSha256']:raise ValueError('Frozen position plan changed.')
    validate_plan(plan)
    capture(plan,jobs_for(plan,policy),args.capture_root)
    derive(plan,policy,args.capture_root,args.output,digest(args.policy),digest(args.plan))


if __name__=='__main__':main()
