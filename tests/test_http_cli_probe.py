"""Exercise the future endpoint probe using a transport double, not a real adapter."""
from email.parser import BytesParser
from email.policy import default
import json
from pathlib import Path

import pytest

from tools.check_http_cli import check_endpoint, multipart, post
from tools.trial_config import sha256


def test_multipart_preserves_image_bytes_and_explicit_fields():
    raw=b'\x89PNG\x00\xff\r\n'
    body,content_type=multipart(raw,'photo','black-bottom')
    message=BytesParser(policy=default).parsebytes(b'Content-Type: '+content_type.encode()+b'\r\nMIME-Version: 1.0\r\n\r\n'+body)
    parts=list(message.iter_parts())
    assert [p.get_param('name',header='content-disposition') for p in parts]==['inputType','orientation','image']
    assert parts[0].get_payload(decode=True)==b'photo'
    assert parts[1].get_payload(decode=True)==b'black-bottom'
    assert parts[2].get_payload(decode=True)==raw


@pytest.mark.parametrize('url',['http://example.com/v1/recognize','https://example.com/redirect','https://u:p@example.com/v1/recognize','https://example.com/v1/recognize?token=x'])
def test_probe_rejects_insecure_remote_or_ambiguous_endpoints(url):
    with pytest.raises(ValueError):post(url,b'x','photo','white-bottom')


@pytest.mark.parametrize('mode',['digital','photo'])
def test_http_probe_checks_cli_parity_and_model_provenance(tmp_path,monkeypatch,mode):
    image=tmp_path/'input.png';image.write_bytes(b'image bytes')
    config=tmp_path/'config.json';config.write_text('{}')
    result={'piecePlacement':'8/8/8/8/8/8/8/8'}
    reference={'result':result,'exitCode':0,'signature':{'modelSha256':'pinned-model'}}
    case={'path':str(image),'mode':mode,'orientation':'black-bottom'}
    headers={'Content-Type':'application/json','X-BoardSnap-Model-SHA256':'pinned-model','X-BoardSnap-Config-SHA256':sha256(config)}
    def transport(endpoint,content,selected,orientation):
        assert content==image.read_bytes() and selected==mode and orientation=='black-bottom'
        return 200,headers,json.dumps(result).encode()
    monkeypatch.setattr('tools.check_http_cli.post',transport)
    assert check_endpoint('https://example.com/v1/recognize',case,reference,config)['parityPassed']
    headers['X-BoardSnap-Model-SHA256']='wrong-model'
    with pytest.raises(ValueError,match='model checksum'):check_endpoint('https://example.com/v1/recognize',case,reference,config)


def test_http_probe_detects_transport_returning_wrong_position(tmp_path,monkeypatch):
    image=tmp_path/'input.png';image.write_bytes(b'x');config=tmp_path/'config';config.write_text('{}')
    good={'piecePlacement':'8/8/8/8/8/8/8/8'};bad={'piecePlacement':'p7/8/8/8/8/8/8/8'}
    monkeypatch.setattr('tools.check_http_cli.post',lambda *a:(200,{'Content-Type':'application/json'},json.dumps(bad).encode()))
    with pytest.raises(ValueError,match='disagrees'):
        check_endpoint('https://example.com/v1/recognize',{'path':str(image),'mode':'digital','orientation':'white-bottom'},
                       {'result':good,'exitCode':0,'signature':{'modelSha256':'x'}},config)


@pytest.mark.parametrize('status',[200,422])
def test_real_urllib_request_path_with_controlled_response(monkeypatch,status):
    from io import BytesIO
    from urllib.error import HTTPError
    class Response(BytesIO):
        code=status
        headers={'Content-Type':'application/json'}
    captured=[]
    class Opener:
        def open(self,request,timeout):
            captured.append(request)
            assert timeout==90 and request.method=='POST'
            assert request.get_header('Content-type').startswith('multipart/form-data; boundary=')
            assert b'image data' in request.data and b'black-bottom' in request.data
            if status==422:
                raise HTTPError(request.full_url,422,'Unprocessable',{'Content-Type':'application/json'},BytesIO(b'{"error":{}}'))
            return Response(b'{"piecePlacement":"8/8/8/8/8/8/8/8"}')
    monkeypatch.setattr('tools.check_http_cli.build_opener',lambda *handlers:Opener())
    actual,headers,body=post('http://127.0.0.1:8000/v1/recognize',b'image data','photo','black-bottom')
    assert actual==status and headers['Content-Type']=='application/json'
    assert json.loads(body) and len(captured)==1
