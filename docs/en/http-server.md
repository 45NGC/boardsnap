# BoardSnap HTTP adapter

**English** | [Español](../es/http-server.md)

**The adapter is implemented and CLI parity is verified over local HTTPS.**
`boardsnap.adapters.http` is optional; core recognition remains independent of
Starlette, Uvicorn and Flutter. Local verification is not a public deployment or
final photographic quality acceptance.

- [Per-mode contract](http-contract.md).
- [Verification report](../../data/reports/http-adapter-v1.json).
- [Overall project report](project-status.md).

## Installation and startup

From the repository with `.venv` activated:

```bash
python -m pip install -e ".[ml,server]"
boardsnap-http --config data/manifests/local-trial-v1.json --model-root . --port 8000 --allow-origin http://localhost:3000
```

The default bind is `127.0.0.1` for local development. Set the exact Flutter web
origin, including its port. Repeat `--allow-origin` as needed; `*` is rejected.
Native mobile clients do not need CORS but do need a reachable service URL: a
phone's loopback is not the development computer. The verification server is
stopped after testing; these commands start it again.

With TLS certificate and key:

```bash
boardsnap-http --config data/manifests/local-trial-v1.json --model-root . --port 8443 --ssl-certfile /path/cert.pem --ssl-keyfile /path/key.pem --allow-origin https://your-app.example
```

Uvicorn supplies TLS; alternatively terminate HTTPS at a proxy while keeping the
Python process on loopback. No public certificates, hosting accounts or deployment
are created. See [Uvicorn settings](https://uvicorn.dev/settings/) for TLS/binding.

## Models and processing

Application creation reads the pinned configuration, verifies SHA-256 checksums
and loads both classifiers once. Missing or changed models prevent startup; no
downloads or silent fallback. Resolve configured paths beneath `--model-root`,
independently of the installed package directory.

- Digital: `.cache/neural-tolerance-v1-conservative/best.pt`.
- Photo: `.cache/neural-mixed-sqrt-v1/last.pt`, experimental.

The adapter reuses the CLI's `NeuralClassifier`, selects the method by mode and
passes orientation explicitly. Original upload filenames, manual corners and
expected labels never reach recognition. No CLI subprocess handles requests.

Inference runs outside the async event loop and is serialized to one request per
process. Startup sets four PyTorch threads, one OpenCV thread, one Uvicorn worker,
a limit of eight concurrent connections/tasks and a five-second keep-alive.
Saturation can produce an infrastructure 503; Flutter must handle infrastructure
and network errors alongside structured recognition errors. Sustained load and
concurrent service capacity have not been benchmarked.

## Upload handling

Require multipart and preserve duplicates for rejection. Starlette enforces one
file, two fields and 4 KiB per text field. A streaming counter rejects total body
sizes above 21 MiB with or without Content-Length. Image size is limited to 20 MiB.
Filename and supplied MIME do not establish format: existing PNG/JPEG decoding
checks content.

Parser uploads are closed on parse failure too. Recognition uses a separate
temporary directory removed on success, known error or unexpected exception.
Inference completion is shielded against cancellation so its input is not removed
while its worker still reads it. Uploaded images are not retained by default.
The maintained [Starlette multipart parser](https://starlette.dev/requests/) is used.

Known exceptions preserve codes. Unexpected failures are logged to stderr and
return generic `PROCESSING_FAILED` without traces in JSON. Config/model checksum
headers are exposed to configured CORS origins. Bodies contain only `piecePlacement`
or `error`.

## Executed evidence

On November 16, 2026 the real server ran at
`https://localhost:8443/v1/recognize`, bound to loopback, with a local test
certificate explicitly trusted by clients. **TLS certificate verification remained
enabled.** No Internet-facing service was published.

- Eight CLI-parity cases pass: digital/photo in both views, no board and corrupt
  input in each mode. Placement/error code, status and model/config hashes match.
- Thirteen live HTTPS checks pass: missing field, invalid orientation, unknown
  field, duplicate field, extra file, malformed multipart, wrong content type,
  empty image, GIF disguised as PNG, file/body limits, allowed/rejected CORS origins.
- **97 targeted tests pass**, covering adapter, contract, probe, local config, CLI
  and photo pipeline. They include temporary/parser-file cleanup, unexpected
  exceptions, exact size boundary, streamed bodies without Content-Length, changed
  model rejection and serialized inference.
- `pip check` finds no broken requirements. Starlette's test client emits an httpx
  deprecation warning; the recorded versions pass. Dependencies were not changed
  solely to hide the warning.

Reports record versions and hashes. This verifies integration/transport, not global
accuracy or independent final evaluation. No training occurred. Prior CPU figures
used one resident model; they are not presented as a two-model HTTP server or
network benchmark.

## Reproduction

```bash
python -m pip install -e ".[dev,ml,server,server-test]"
python -m pytest tests/test_http_adapter.py tests/test_http_contract.py tests/test_http_cli_probe.py tests/test_local_trial.py tests/test_cli.py tests/test_photo_pipeline.py -q
python -m tools.check_http_cli --endpoint https://YOUR_SERVER/v1/recognize
```

To reproduce only the local TLS setup:

```bash
mkdir -p .cache/http-adapter-v1
openssl req -x509 -newkey rsa:2048 -nodes -keyout .cache/http-adapter-v1/key.pem -out .cache/http-adapter-v1/cert.pem -days 1 -subj /CN=localhost -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1'
boardsnap-http --config data/manifests/local-trial-v1.json --model-root . --port 8443 --allow-origin https://scanner.example --ssl-certfile .cache/http-adapter-v1/cert.pem --ssl-keyfile .cache/http-adapter-v1/key.pem
```

In another activated terminal:

```bash
SSL_CERT_FILE="$PWD/.cache/http-adapter-v1/cert.pem" python -m tools.check_http_cli --endpoint https://localhost:8443/v1/recognize
python -m tools.check_http_requests --endpoint https://localhost:8443/v1/recognize --ca-file .cache/http-adapter-v1/cert.pem --output .cache/http-adapter-v1/request-checks.json
```

Test certificates expire after one day; regenerate them for later runs. Keys and
certificates remain in ignored `.cache`.

## Before offering a public service

Configure hosting, trusted domain/TLS and Flutter web origins; decide authentication
and quotas when exposing the service; set deployment request deadlines and capacity/
cancellation strategy; distribute versioned weights/dependencies; test actual
Android, iOS and web clients. The app should allow editor corrections and identify
photographic mode as experimental.
