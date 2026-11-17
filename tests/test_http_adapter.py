"""Exercise the real ASGI multipart parser, cleanup, selection and error transport."""
import json
from pathlib import Path
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

pytest.importorskip('starlette')
pytest.importorskip('httpx')
pytest.importorskip('python_multipart')
from starlette.testclient import TestClient

from boardsnap.adapters.http import MAX_BODY_BYTES, create_app, digest
from boardsnap.adapters.http_contract import MAX_IMAGE_BYTES
from boardsnap.detection import BoardDetectionError


@pytest.fixture
def setup(tmp_path):
    models={}
    for mode in ('digital','photo'):
        file=tmp_path/(mode+'.pt');file.write_bytes(mode.encode())
        models[mode]={'path':file.name,'sha256':digest(file)}
    config=tmp_path/'config.json';config.write_text(json.dumps({'schemaVersion':1,'status':'local-trial-not-accepted','models':models}))
    uploads=tmp_path/'uploads';uploads.mkdir()
    calls=[];factories=[]
    class Fake:
        def __init__(self,path):self.model=path.name;factories.append(path)
        def classify(self,path,mode,orientation):
            calls.append({'path':Path(path),'mode':mode,'orientation':orientation,'content':Path(path).read_bytes(),'model':self.model})
            if Path(path).read_bytes()==b'no-board':raise BoardDetectionError('BOARD_NOT_FOUND','No board.')
            if Path(path).read_bytes()==b'crash':raise RuntimeError('private failure detail')
            return {'piecePlacement':'8/8/8/8/8/8/8/8'}
        def recognize_image(self,path,*,orientation):return self.classify(path,'digital',orientation)
        def recognize_photo(self,path,*,orientation):return self.classify(path,'photo',orientation)
    app=create_app(config,model_root=tmp_path,temp_root=uploads,allowed_origins=['https://scanner.example'],classifier_factory=Fake)
    return app,config,uploads,calls,factories,Fake


def send(client,mode='photo',orientation='black-bottom',content=b'image'):
    return client.post('/v1/recognize',data={'inputType':mode,'orientation':orientation},files={'image':('untrusted/filename.exe',content,'application/octet-stream')})


@pytest.mark.parametrize('mode,orientation',[('digital','auto'),('digital','black-bottom'),('photo','white-bottom'),('photo','black-bottom')])
def test_pinned_model_selection_orientation_and_temporary_cleanup(setup,mode,orientation):
    app,config,uploads,calls,factories,_=setup
    with TestClient(app) as client:
        response=send(client,mode,orientation)
        assert response.status_code==200 and response.json()=={'piecePlacement':'8/8/8/8/8/8/8/8'}
        assert response.headers['X-BoardSnap-Config-SHA256']==digest(config)
        assert response.headers['X-BoardSnap-Model-SHA256']==json.loads(config.read_text())['models'][mode]['sha256']
        assert calls[-1]['mode']==mode and calls[-1]['orientation']==orientation
        assert calls[-1]['model']==mode+'.pt' and calls[-1]['content']==b'image'
        assert not calls[-1]['path'].exists() and not list(uploads.iterdir())
        send(client,mode,orientation)
        assert len(factories)==2  # Models are loaded once, not per request.


@pytest.mark.parametrize('content,status,code',[(b'no-board',422,'BOARD_NOT_FOUND'),(b'crash',500,'PROCESSING_FAILED')])
def test_expected_and_unexpected_failures_cleanup_without_internal_details(setup,content,status,code):
    app,_,uploads,calls,_,_=setup
    with TestClient(app) as client:
        response=send(client,content=content)
    assert response.status_code==status and response.json()['error']['code']==code
    assert 'private failure detail' not in response.text
    assert 'X-BoardSnap-Model-SHA256' in response.headers
    assert not list(uploads.iterdir()) and not calls[-1]['path'].exists()


@pytest.mark.parametrize('parts',[
 [('inputType',(None,'photo')),('orientation',(None,'auto')),('image',('a',b'x'))],
 [('inputType',(None,'digital')),('orientation',(None,'white-bottom')),('model',(None,'fake.pt')),('image',('a',b'x'))],
 [('inputType',(None,'digital')),('inputType',(None,'photo')),('orientation',(None,'white-bottom')),('image',('a',b'x'))],
 [('inputType',(None,'photo')),('orientation',(None,'black-bottom')),('image',('a',b'x')),('image',('b',b'x'))],
 [('inputType',(None,'photo')),('orientation',(None,'black-bottom')),('other',('a',b'x'))],
 [('inputType',('field.txt',b'photo')),('orientation',(None,'black-bottom')),('image',('a',b'x'))],
 [('inputType',(None,'photo')),('image',('a',b'x'))],
])
def test_invalid_multipart_parts_never_reach_recognition(setup,parts):
    app,_,uploads,calls,_,_=setup
    with TestClient(app) as client:
        response=client.post('/v1/recognize',files=parts)
    assert response.status_code==400 and response.json()['error']['code']=='INVALID_REQUEST'
    assert not calls and not list(uploads.iterdir())


def test_limits_cover_file_and_streamed_body_without_content_length(setup):
    app,_,uploads,calls,_,_=setup
    with TestClient(app) as client:
        response=send(client,content=b'x'*(MAX_IMAGE_BYTES+1))
        assert response.status_code==413 and response.json()['error']['code']=='PAYLOAD_TOO_LARGE'
        # Declared lengths rejected before parsing, and chunked streams counted too.
        response=client.post('/v1/recognize',content=b'',headers={'Content-Length':str(MAX_BODY_BYTES+1),'Content-Type':'multipart/form-data; boundary=test'})
        assert response.status_code==413 and response.headers['content-type']=='application/json'
        def chunks():
            yield b'--test\r\nContent-Disposition: form-data; name="image"; filename="x"\r\n\r\n'
            for _ in range(22):yield b'x'*(1024*1024)
        response=client.post('/v1/recognize',content=chunks(),headers={'Content-Type':'multipart/form-data; boundary=test'})
        assert response.status_code==413 and response.json()['error']['code']=='PAYLOAD_TOO_LARGE'
    assert not calls and not list(uploads.iterdir())


def test_malformed_multipart_and_wrong_content_type_are_structured(setup):
    app,_,_,calls,_,_=setup
    with TestClient(app) as client:
        for content_type,body in [('application/json',b'{}'),('multipart/form-data',b'bad'),('multipart/form-data; boundary=x',b'--x\r\nnot a header')]:
            response=client.post('/v1/recognize',content=body,headers={'Content-Type':content_type})
            assert response.status_code==400 and response.json()['error']['code']=='INVALID_REQUEST'
    assert not calls


def test_cors_exposes_model_headers_only_for_configured_origin(setup):
    app,_,_,_,_,_=setup
    with TestClient(app) as client:
        headers={'Origin':'https://scanner.example','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'}
        response=client.options('/v1/recognize',headers=headers)
        assert response.status_code==200 and response.headers['access-control-allow-origin']=='https://scanner.example'
        response=client.post('/v1/recognize',content=b'bad',headers={'Origin':'https://scanner.example','Content-Type':'application/json'})
        assert response.status_code==400 and 'X-BoardSnap-Model-SHA256' in response.headers['access-control-expose-headers']
        response=client.options('/v1/recognize',headers={**headers,'Origin':'https://unconfigured.example'})
        assert response.status_code==400 and 'access-control-allow-origin' not in response.headers


def test_changed_weights_prevent_startup(setup,tmp_path):
    _,config,_,_,_,Fake=setup
    (tmp_path/'photo.pt').write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed model'):
        create_app(config,model_root=tmp_path,classifier_factory=Fake)


def test_concurrent_requests_serialize_inference(setup,tmp_path):
    _,config,uploads,_,_,Fake=setup
    active=0;peak=0;lock=threading.Lock()
    class Slow(Fake):
        def classify(self,*args):
            nonlocal active,peak
            with lock:active+=1;peak=max(peak,active)
            time.sleep(.03)
            try:return super().classify(*args)
            finally:
                with lock:active-=1
    app=create_app(config,model_root=tmp_path,temp_root=uploads,classifier_factory=Slow)
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda _:send(client),range(2)))
    assert all(r.status_code==200 for r in responses) and peak==1 and not list(uploads.iterdir())


def test_exact_file_limit_is_accepted_and_multipart_files_are_closed(setup,monkeypatch):
    app,_,uploads,calls,_,_=setup
    from starlette.datastructures import UploadFile
    closed=[]
    original=UploadFile.close
    async def close(self):
        await original(self);closed.append(self.file.closed)
    monkeypatch.setattr(UploadFile,'close',close)
    with TestClient(app) as client:
        response=send(client,content=b'x'*MAX_IMAGE_BYTES)
        assert response.status_code==200
        response=send(client,content=b'x'*(MAX_IMAGE_BYTES+1))
        assert response.status_code==413
    assert closed==[True,True] and len(calls)==1 and not list(uploads.iterdir())


def test_route_errors_are_json_and_query_overrides_are_rejected(setup):
    app,_,_,calls,_,_=setup
    with TestClient(app) as client:
        for response in [client.get('/v1/recognize'),client.post('/unknown'),
                         client.post('/v1/recognize?inputType=photo',files={'image':('x',b'x')})]:
            assert response.status_code==400 and response.json()['error']['code']=='INVALID_REQUEST'
    assert not calls


def test_wildcard_cors_rejected_by_factory(setup,tmp_path):
    _,config,_,_,_,Fake=setup
    with pytest.raises(ValueError,match='explicit CORS'):
        create_app(config,model_root=tmp_path,allowed_origins=['*'],classifier_factory=Fake)
