"""Prepare CLI references or compare a future HTTP endpoint with the same fixed models."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler

from boardsnap.adapters.http_contract import assert_cli_parity, decode_response, response_status
from tools.trial_config import ROOT, DEFAULT_CONFIG, select_model, sha256

CACHE = ROOT / '.cache/http-cli-contract-v1'


def multipart(content, mode, orientation):
    boundary = 'boardsnap-' + uuid.uuid4().hex
    body = bytearray()
    for name, value in [('inputType', mode), ('orientation', orientation)]:
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="upload.png"\r\nContent-Type: image/png\r\n\r\n'.encode())
    body.extend(content)
    body.extend(f'\r\n--{boundary}--\r\n'.encode())
    return bytes(body), 'multipart/form-data; boundary=' + boundary


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def post(endpoint, content, mode, orientation):
    url = urlsplit(endpoint)
    if (url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in ('127.0.0.1', 'localhost', '::1'))
            or url.username or url.password or url.query or url.fragment or url.path != '/v1/recognize'):
        raise ValueError('Use HTTPS /v1/recognize, or loopback HTTP for local testing.')
    body, content_type = multipart(content, mode, orientation)
    request = Request(endpoint, body, {'Content-Type': content_type}, method='POST')
    # No automatic redirects or environment proxy forwarding of development images.
    opener = build_opener(ProxyHandler({}), NoRedirect())
    try:
        response = opener.open(request, timeout=90)
    except HTTPError as error:
        response = error
    with response:
        payload = response.read(1024 * 1024 + 1)
        if len(payload) > 1024 * 1024: raise ValueError('HTTP response exceeds test limit.')
        return response.code, response.headers, payload


def cases():
    digital = json.loads((ROOT/'data/manifests/real-use-development-v1.json').read_text())
    photo = json.loads((ROOT/'data/manifests/phone-validation-v1.json').read_text())
    if digital['independentFinalEvaluation'] is not False or photo['independentFinalEvaluation'] is not False:
        raise ValueError('Use consulted development cases only.')
    selected = []
    for view in ('white-bottom', 'black-bottom'):
        d = next(r for r in digital['samples'] if r['orientation'] == view)
        moved = ROOT / '.cache/real-use-tests/computer-screenshots' / Path(d['path']).name
        path = ROOT/d['path'] if (ROOT/d['path']).exists() else moved
        if sha256(path) != d['sha256']: raise ValueError('Digital development image changed.')
        selected.append({'id':'digital-'+view, 'path':str(path), 'mode':'digital', 'orientation':view})
        p = next(r for r in photo['samples'] if r['label']['orientation'] == view)
        if sha256(ROOT/p['imagePath']) != p['imageSha256']: raise ValueError('Photo changed.')
        selected.append({'id':'photo-'+view, 'path':str(ROOT/p['imagePath']), 'mode':'photo', 'orientation':view})
    from PIL import Image
    blank = CACHE/'no-board.png'
    if not blank.exists():
        with Image.new('RGB', (400,400), 'white') as image: image.save(blank)
    corrupt = CACHE/'corrupt.png'
    if not corrupt.exists(): corrupt.write_bytes(b'not an image')
    for mode in ('digital', 'photo'):
        for name, path in [('no-board',blank), ('corrupt',corrupt)]:
            selected.append({'id':mode+'-'+name, 'path':str(path), 'mode':mode, 'orientation':'white-bottom'})
    return selected


def cli_reference(case, config_path):
    model = select_model(config_path, case['mode'])
    runtime = {str(p.relative_to(ROOT)):sha256(p) for p in sorted((ROOT/'src/boardsnap').rglob('*.py'))}
    signature = {'imageSha256':sha256(case['path']), 'modelSha256':sha256(model),
                 'mode':case['mode'], 'orientation':case['orientation'], 'runtime':runtime,
                 'python':sys.version, 'configSha256':sha256(config_path)}
    key = hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
    output = CACHE/(key+'.json')
    if output.exists():
        saved = json.loads(output.read_text())
        if saved['signature'] != signature: raise ValueError('CLI reference changed.')
        status = response_status(saved['result'])
        if saved['exitCode'] != (0 if status == 200 else 1):
            raise ValueError('Cached CLI exit status disagrees with JSON.')
        return saved
    command = [sys.executable, '-m', 'boardsnap', case['path'], '--model',str(model),
               '--input-type',case['mode'],'--orientation',case['orientation']]
    process = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=90,
                             env={**os.environ,'OMP_NUM_THREADS':'4','MKL_NUM_THREADS':'4'})
    result = decode_response(process.stdout.encode())
    status = response_status(result)
    if process.stderr or process.stdout != json.dumps(result)+'\n' or process.returncode != (0 if status == 200 else 1):
        raise ValueError('CLI output contract failed.')
    saved = {'signature':signature,'result':result,'exitCode':process.returncode,'command':command}
    output.write_text(json.dumps(saved,indent=2)+'\n')
    return saved


def check_endpoint(endpoint, case, reference, config_path):
    status, headers, body = post(endpoint,Path(case['path']).read_bytes(),case['mode'],case['orientation'])
    result = assert_cli_parity(reference['result'],reference['exitCode'],status,headers.get('Content-Type',''),body)
    if headers.get('X-BoardSnap-Model-SHA256') != reference['signature']['modelSha256']:
        raise ValueError('Endpoint model checksum differs from CLI.')
    if headers.get('X-BoardSnap-Config-SHA256') != sha256(config_path):
        raise ValueError('Endpoint configuration checksum differs from local trial.')
    return {'status':status,'result':result,'parityPassed':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare-only',action='store_true')
    action.add_argument('--endpoint',help='Complete HTTPS URL /v1/recognize; sends the documented development images.')
    parser.add_argument('--config',type=Path,default=DEFAULT_CONFIG)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    CACHE.mkdir(parents=True,exist_ok=True)
    results=[]
    for case in cases():
        reference=cli_reference(case,args.config)
        row={'case':case,'cli':reference}
        if args.endpoint: row['http']=check_endpoint(args.endpoint,case,reference,args.config)
        results.append(row)
        print(case['id']+(': HTTP/CLI match' if args.endpoint else ': CLI reference ready'),flush=True)
    report={'schemaVersion':1,'contractVersion':'v1','configSha256':sha256(args.config),
            'finalEvaluationAccessed':False,'trainingRun':False,'records':results,
            'httpParityStatus':'passed' if args.endpoint else 'pending-no-real-adapter',
            'endpoint':args.endpoint,'scope':'Eight consulted development/negative cases; does not establish recognition accuracy or release acceptance.'}
    path=args.output or CACHE/('http-comparison.json' if args.endpoint else 'cli-references.json')
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
