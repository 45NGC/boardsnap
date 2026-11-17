# Per-mode HTTP contract and CLI parity probe

**English** | [Español](../es/http-contract.md)

**The v1 contract is implemented and CLI parity is verified over local HTTPS.**
The [HTTP adapter](http-server.md) passes eight parity cases and thirteen additional
live request/CORS checks. Local verification is not public deployment or model
accuracy acceptance.

- [Machine-readable contract](../../data/manifests/http-contract-v1.json).
- [Framework-independent rules](../../src/boardsnap/adapters/http_contract.py).
- [Pinned trial models](local-trial.md).
- [Flutter integration](flutter-integration.md).

## Request

`POST /v1/recognize`, `Content-Type: multipart/form-data`, over HTTPS. Plain HTTP
is permitted only on loopback for local testing.

| Field | Type | Required | Values |
| --- | --- | --- | --- |
| `image` | File | Exactly one | PNG or JPEG content |
| `inputType` | Text | Exactly one | `digital`, `photo` |
| `orientation` | Text | Exactly one | `white-bottom`, `black-bottom`; `auto` for digital only |

HTTP has no implicit values for omitted fields. Core/CLI defaults remain unchanged.
Orientation describes the board view, not the side to move. Explicit values override
coordinates; digital `auto` retains the existing white-bottom fallback.

Unknown/duplicate fields, extra files and text fields supplied as files return
`INVALID_REQUEST` (400). Multipart parsing must preserve multiplicities, not collapse
parts into a dictionary. `validate_fields` checks ordered text fields and image
count/size; the future adapter must also validate multipart part names/types.

The image limit is **20 MiB (20,971,520 bytes)** inclusive; the total multipart
body limit is **21 MiB**, enforced before buffering the entire body. Exceeding a
limit returns `PAYLOAD_TOO_LARGE` (413). An empty file with otherwise valid fields
reaches the decoder and produces `INVALID_IMAGE` (422). Decode content rather than
trusting filename/MIME assertions. Existing decoder pixel/format limits still apply.

Clients never send model/profile names, local paths or expected positions. The
server selects its pinned model:

| inputType | Current trial model |
| --- | --- |
| `digital` | `neural-tolerance-v1-conservative/best.pt` |
| `photo` | `neural-mixed-sqrt-v1/last.pt`, experimental |

Call the core with explicit `model`, `input_type` and `orientation`. Verify pinned
weights/configuration on startup and optionally retain a loaded classifier per
model. No silent `BOARDSNAP_MODEL` fallback. Do not invoke the CLI per request;
it is only the external test reference. Full paths/hashes are in `local-trial-v1.json`.

## Response

Success: HTTP 200, `Content-Type: application/json` (optional `charset=utf-8`):

```json
{"piecePlacement":"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"}
```

Only canonical piece placement, without additional metadata or FEN fields. An
actually recognized empty board is valid, but never a failure substitute. Chess
legality is not required. The probe rejects extra fields, full FEN, duplicate JSON
keys and invalid rank lengths/compression.

Errors contain exactly `{"error":{"code":"...","message":"..."}}`:

| Status | Codes |
| --- | --- |
| 400 | `INVALID_REQUEST` |
| 413 | `PAYLOAD_TOO_LARGE` |
| 422 | `INVALID_IMAGE`, `UNSUPPORTED_IMAGE`, `BOARD_NOT_FOUND` |
| 500 | `INPUT_READ_ERROR`, `PROCESSING_FAILED` |

`INPUT_READ_ERROR` refers to reading the server temporary file, not a client-device
path. Internal exceptions must yield generic errors without traces. Clients branch
on `code`; message text can vary. Proxy-generated HTML/timeouts are integration
failures, not valid BoardSnap responses.

Recognition responses, including decoder/detection failures, include:

- `X-BoardSnap-Model-SHA256`: selected weight-file hash.
- `X-BoardSnap-Config-SHA256`: exact pinned configuration-file byte hash.

These verify versions without changing JSON. Headers are optional when request
validation fails before a mode can be selected. Expose them through CORS to
configured Flutter web origins. Authentication, proxy, concurrency and deployment
remain server implementation decisions. Delete temporary files on every outcome;
do not retain uploaded images by default.

## Prepared comparison

`tools.check_http_cli` uses eight previously consulted development cases, with
no training or independent final evaluation:

1. Digital screenshots from each orientation.
2. Screen photographs from each orientation.
3. A no-board image in each mode.
4. A corrupt file in each mode.

It builds references through `python -m boardsnap`, selecting pinned models per
mode. It records image/configuration/model/runtime hashes and reuses compatible
CLI results. The same bytes are uploaded through multipart, with no supplied
corners, original filenames or expected position. It checks:

- Identical placement for identical bytes, mode, view and weights.
- Matching error code; CLI 0/1 mapped to HTTP 200/400/413/422/500 by contract.
- Strict JSON schema and correct `Content-Type`.
- Matching model/configuration headers.

Parity tests interface equivalence, not recognition accuracy: both may agree on an
incorrect piece. Request/size rules have contract tests; the eight-case probe is now complemented by `tools.check_http_requests`, which
checks oversized uploads, total body limits, malformed multipart and other rules
against the real adapter. See the server report.

## Commands and current evidence

From the repository with `.venv` activated:

```bash
python -m tools.check_http_cli --prepare-only
python -m pytest tests/test_http_contract.py tests/test_http_cli_probe.py tests/test_local_trial.py -q
```

References are in `.cache/http-cli-contract-v1/cli-references.json`. All eight real
CLI calls completed; **39 tests pass**, covering modes, orientations, duplicates,
size, schemas, errors and mismatched output detection. Those probe tests use a transport double. Subsequent adapter tests and live HTTPS
checks are documented in [http-server](http-server.md).

With the adapter running on the same config and weights:

```bash
python -m tools.check_http_cli --endpoint https://YOUR_SERVER/v1/recognize
```

This sends development images to that endpoint. Local servers may use
`http://127.0.0.1:8000/v1/recognize`. The probe disables redirects and allows up to
1 MiB per response. Its 90-second client timeout is a test-tool setting, not an
availability guarantee. A mismatch exits with an error and keeps CLI references.
On complete success, `.cache/http-cli-contract-v1/http-comparison.json` is saved.

**Current status: eight local HTTPS parity cases pass.** Real multipart, upload-limit
and CORS checks and adapter cleanup/internal-error tests also pass. Public deployment
and Flutter connection remain pending.
