"""Exercise real HTTP multipart and CORS failures beyond the CLI parity cases."""
import argparse
import json
from pathlib import Path
import ssl
from urllib.parse import urlsplit


def check(endpoint, ca_file=None):
    import httpx
    parsed=urlsplit(endpoint)
    if parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in ('127.0.0.1','localhost','::1')):
        raise ValueError('Use HTTPS or loopback HTTP.')
    records=[]
    with httpx.Client(verify=ssl.create_default_context(cafile=ca_file),trust_env=False,timeout=90,follow_redirects=False) as client:
        def expect(name,response,status,code):
            assert response.status_code==status,(name,response.status_code,response.text)
            assert response.headers['content-type'].split(';')[0]=='application/json'
            payload=response.json()
            assert set(payload)=={'error'} and set(payload['error'])=={'code','message'}
            assert payload['error']['code']==code,(name,payload)
            records.append({'id':name,'status':response.status_code,'result':payload})
        fields={'inputType':'photo','orientation':'white-bottom'}
        expect('missing-orientation',client.post(endpoint,data={'inputType':'photo'},files={'image':('x',b'x')}),400,'INVALID_REQUEST')
        expect('photo-auto',client.post(endpoint,data={**fields,'orientation':'auto'},files={'image':('x',b'x')}),400,'INVALID_REQUEST')
        expect('unknown-field',client.post(endpoint,data={**fields,'model':'client.pt'},files={'image':('x',b'x')}),400,'INVALID_REQUEST')
        duplicate=[('inputType',(None,'digital')),('inputType',(None,'photo')),('orientation',(None,'white-bottom')),('image',('x',b'x'))]
        expect('duplicate-field',client.post(endpoint,files=duplicate),400,'INVALID_REQUEST')
        expect('extra-file',client.post(endpoint,data=fields,files=[('image',('x',b'x')),('image',('y',b'y'))]),400,'INVALID_REQUEST')
        expect('malformed-multipart',client.post(endpoint,content=b'bad',headers={'Content-Type':'multipart/form-data'}),400,'INVALID_REQUEST')
        expect('wrong-content-type',client.post(endpoint,json=fields),400,'INVALID_REQUEST')
        expect('empty-image',client.post(endpoint,data=fields,files={'image':('x',b'')}),422,'INVALID_IMAGE')
        from io import BytesIO
        from PIL import Image
        stream=BytesIO()
        with Image.new('RGB',(16,16),'white') as image:image.save(stream,format='GIF')
        expect('unsupported-format',client.post(endpoint,data=fields,files={'image':('fake.png',stream.getvalue(),'image/png')}),422,'UNSUPPORTED_IMAGE')
        expect('file-limit',client.post(endpoint,data=fields,files={'image':('x',b'x'*(20*1024*1024+1))}),413,'PAYLOAD_TOO_LARGE')
        expect('body-limit',client.post(endpoint,content=b'x'*(21*1024*1024+1),headers={'Content-Type':'multipart/form-data; boundary=x'}),413,'PAYLOAD_TOO_LARGE')
        # CORS origin matches the documented local test server command.
        preflight={'Origin':'https://scanner.example','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'}
        response=client.options(endpoint,headers=preflight)
        assert response.status_code==200 and response.headers['access-control-allow-origin']=='https://scanner.example'
        records.append({'id':'allowed-cors','status':response.status_code})
        response=client.options(endpoint,headers={**preflight,'Origin':'https://unconfigured.example'})
        assert response.status_code==400 and 'access-control-allow-origin' not in response.headers
        records.append({'id':'rejected-cors','status':response.status_code})
    return {'schemaVersion':1,'endpoint':endpoint,'tlsCertificateValidated':parsed.scheme=='https','passed':True,
            'records':records,'scope':'Real adapter validation and CORS; internal-error and temporary cleanup are tested in ASGI tests.',
            'trainingRun':False,'finalEvaluationAccessed':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--endpoint',required=True)
    parser.add_argument('--ca-file')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=check(args.endpoint,args.ca_file)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(f"Real HTTP request checks passed: {len(report['records'])}")


if __name__=='__main__':main()
