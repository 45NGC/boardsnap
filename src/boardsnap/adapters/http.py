"""Optional ASGI adapter with pinned models; recognition remains framework-independent."""
import argparse
import asyncio
from contextlib import redirect_stdout
import hashlib
import json
import logging
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers, UploadFile
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

from boardsnap.adapters.http_contract import MAX_IMAGE_BYTES, RequestError, response_status, validate_fields
from boardsnap.classification import ClassificationError
from boardsnap.detection import BoardDetectionError
from boardsnap.image_input import ImageInputError

MAX_BODY_BYTES = 21 * 1024 * 1024
LOGGER = logging.getLogger('boardsnap.http')
EXPOSE_HEADERS = ['X-BoardSnap-Model-SHA256', 'X-BoardSnap-Config-SHA256']


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_configuration(config_path, model_root):
    """Resolve repository-relative trial paths under an explicit server root."""
    config_path, root = Path(config_path), Path(model_root).resolve()
    content = config_path.read_bytes()
    data = json.loads(content)
    if data.get('schemaVersion') != 1 or data.get('status') != 'local-trial-not-accepted':
        raise ValueError('Unsupported model configuration.')
    selected = {}
    for mode in ('digital', 'photo'):
        row = data['models'][mode]
        path = (root / row['path']).resolve()
        if not path.is_relative_to(root) or not path.is_file() or digest(path) != row['sha256']:
            raise ValueError('Missing or changed model for ' + mode)
        selected[mode] = {'path': path, 'sha256': row['sha256']}
    return selected, hashlib.sha256(content).hexdigest()


def error_response(code, message, headers=None, status=None):
    payload = {'error': {'code': code, 'message': message}}
    return JSONResponse(payload, status_code=status or response_status(payload), headers=headers)


class BodyLimit:
    """Bound streamed and declared bytes before the parser can buffer them."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        length = Headers(scope=scope).get('content-length')
        if length is not None:
            try:
                size = int(length)
                if size < 0: raise ValueError
            except ValueError:
                return await error_response('INVALID_REQUEST', 'Invalid Content-Length.')(scope, receive, send)
            if size > MAX_BODY_BYTES:
                return await error_response('PAYLOAD_TOO_LARGE', 'Request exceeds the 21 MiB body limit.')(scope, receive, send)
        total = 0

        async def bounded_receive():
            nonlocal total
            message = await receive()
            if message['type'] == 'http.request':
                total += len(message.get('body', b''))
                if total > MAX_BODY_BYTES:
                    raise RequestError('PAYLOAD_TOO_LARGE', 'Request exceeds the 21 MiB body limit.')
            return message

        await self.app(scope, bounded_receive, send)


def create_app(config_path, *, model_root, allowed_origins=(), temp_root=None, classifier_factory=None):
    """Load verified weights once. The test injection never changes model selection."""
    if '*' in allowed_origins:
        raise ValueError('Configure explicit CORS origins.')
    models, config_hash = load_configuration(config_path, model_root)
    if classifier_factory is None:
        import cv2
        import torch
        from boardsnap.neural import NeuralClassifier
        torch.set_num_threads(4)
        cv2.setNumThreads(1)
        classifier_factory = NeuralClassifier
    classifiers = {mode: classifier_factory(row['path']) for mode, row in models.items()}
    gate = asyncio.Lock()

    def recognize(path, mode, orientation):
        classifier = classifiers[mode]
        method = classifier.recognize_photo if mode == 'photo' else classifier.recognize_image
        # Only one inference thread runs at a time, so Python diagnostics do not
        # leak into the HTTP payload or race with another recognition redirect.
        with redirect_stdout(sys.stderr):
            return method(path, orientation=orientation)

    async def endpoint(request):
        headers = None
        if request.query_params:
            return error_response('INVALID_REQUEST', 'Request parameters belong in multipart fields.')
        if request.headers.get('content-type', '').split(';', 1)[0].strip().lower() != 'multipart/form-data':
            return error_response('INVALID_REQUEST', 'Expected multipart/form-data.')
        try:
            async with request.form(max_files=1, max_fields=2, max_part_size=4096) as form:
                fields, uploads = [], []
                for name, value in form.multi_items():
                    if isinstance(value, UploadFile):
                        if name != 'image':
                            raise RequestError('INVALID_REQUEST', 'Unexpected file part.')
                        uploads.append(value)
                    else:
                        fields.append((name, value))
                upload_size = uploads[0].size if len(uploads) == 1 else 0
                options = validate_fields(fields, image_count=len(uploads), image_bytes=upload_size)
                mode = options['input_type']
                headers = {'X-BoardSnap-Model-SHA256': models[mode]['sha256'],
                           'X-BoardSnap-Config-SHA256': config_hash}
                async with gate:
                    # A temporary remains valid until the worker has finished,
                    # including cancellation; threadpool cancellation is shielded.
                    import anyio
                    with anyio.CancelScope(shield=True):
                        with TemporaryDirectory(prefix='boardsnap-upload-', dir=temp_root) as folder:
                            path = Path(folder) / 'image.upload'
                            count = 0
                            with path.open('wb') as stream:
                                while chunk := await uploads[0].read(64 * 1024):
                                    count += len(chunk)
                                    if count > MAX_IMAGE_BYTES:
                                        raise RequestError('PAYLOAD_TOO_LARGE', 'Image exceeds the 20 MiB upload limit.')
                                    stream.write(chunk)
                            result = await run_in_threadpool(recognize, path, mode, options['orientation'])
                            status = response_status(result)
                return JSONResponse(result, status_code=status, headers=headers)
        except RequestError as error:
            return JSONResponse(error.to_dict(), status_code=error.status, headers=headers)
        except HTTPException as error:
            if error.status_code == 413:
                return error_response('PAYLOAD_TOO_LARGE', 'Request exceeds the upload limit.', headers)
            return error_response('INVALID_REQUEST', 'Invalid multipart request.', headers)
        except (ImageInputError, BoardDetectionError, ClassificationError) as error:
            result = error.to_dict()
            return JSONResponse(result, status_code=response_status(result), headers=headers)
        except Exception:
            LOGGER.exception('Recognition request failed')
            return error_response('PROCESSING_FAILED', 'Could not recognize the image.', headers)

    async def http_error(request, error):
        return error_response('INVALID_REQUEST', 'Unknown endpoint or HTTP method.')

    app = Starlette(routes=[Route('/v1/recognize', endpoint, methods=['POST'])],
                    exception_handlers={HTTPException: http_error})
    app.router.redirect_slashes = False
    # Outer CORS covers body-limit and processing failures too. No credentials or
    # wildcard origins; browsers receive only the explicitly configured origins.
    return CORSMiddleware(BodyLimit(app), allow_origins=list(allowed_origins),
                          allow_methods=['POST'], allow_headers=['Content-Type'],
                          expose_headers=EXPOSE_HEADERS, allow_credentials=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--model-root', type=Path, required=True)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--allow-origin', action='append', default=[])
    parser.add_argument('--ssl-certfile')
    parser.add_argument('--ssl-keyfile')
    args = parser.parse_args(argv)
    if bool(args.ssl_certfile) != bool(args.ssl_keyfile):
        parser.error('Provide both TLS certificate and private key.')
    if '*' in args.allow_origin:
        parser.error('Configure explicit CORS origins.')
    app = create_app(args.config, model_root=args.model_root, allowed_origins=args.allow_origin)
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, ssl_certfile=args.ssl_certfile,
                ssl_keyfile=args.ssl_keyfile, workers=1, access_log=False,
                limit_concurrency=8, timeout_keep_alive=5)


if __name__ == '__main__':
    main()
