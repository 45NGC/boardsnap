# Flutter integration design

[Spanish](../es/flutter-integration.md) · [Overview](README.md)

The [per-mode HTTP contract and parity probe](http-contract.md) specify required fields, models, errors and version headers. Local HTTPS parity is verified with the [implemented adapter](http-server.md).

Target platforms: **Android, iOS and web**, as requested for chess-scanner.
The proposed transport is **an HTTPS API around the Python core**. This gives all
three clients the same recognition implementation. This document specifies that
adapter, now [implemented and locally verified](http-server.md).
**Public deployment and the Flutter client remain pending.**
The CLI remains a local development tool. A mobile or browser client cannot use
an installed desktop Python command as its integration mechanism.

## Responsibilities and proposed request

The separate backend reuses the classifier with the same arguments as
`recognize_image(temporary_path, model=model_path, input_type=input_type, orientation=orientation)`
with an explicitly configured model per input mode. The [local trial configuration](local-trial.md)
pins a digital reference and an experimental photographic candidate as an example
for the future backend. A loaded `NeuralClassifier(model_path)` can also be reused per model.
Model/version selection is deployment configuration, not a theme choice in Flutter.
It owns temporary uploads,
request limits, concurrency and response serialization. The core remains
independent of its web framework. Flutter owns image selection, HTTP transport,
the board editor and all remaining game state.

Endpoint fixed for the trial: `POST /v1/recognize`, multipart form data:

- `image`: one PNG/JPEG file, sent as bytes; do not send a local device path.
- `inputType`: explicitly select `digital` or `photo` for this trial. The server
  selects its configured model; clients do not send weight paths or theme names.
  Photos require explicit orientation. This HTTP field and the Python/CLI parameter are implemented.
- `orientation`: `white-bottom`, `black-bottom` or `auto` (digital only). Flutter can
  ask which side is at the bottom after image selection and send that choice.
  It describes the image view, not the side to move. Explicit values override
  image coordinates. Unknown values map to the proposed `INVALID_REQUEST` (400).
  The Python/CLI parameter and HTTP field are implemented; Flutter UI remains pending.

Success, HTTP 200, `Content-Type: application/json`:

```json
{"piecePlacement":"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"}
```

The [existing contract](output-contract.md) is unchanged. Errors use only
`{"error":{"code":"...","message":"..."}}`, without a success payload.
Contract mappings for the future adapter:

| HTTP status | Code | Meaning |
| --- | --- | --- |
| 400 | `INVALID_REQUEST` | Missing/multiple files or invalid orientation; adapter validation. |
| 413 | `PAYLOAD_TOO_LARGE` | Upload exceeds the configured byte limit; adapter validation. |
| 422 | `INVALID_IMAGE`, `UNSUPPORTED_IMAGE`, `BOARD_NOT_FOUND` | Core cannot process the supplied image. |
| 500 | `INPUT_READ_ERROR`, `PROCESSING_FAILED` | Server could not read its temporary file or process the image. |

The two request-validation codes above are **HTTP-only codes**, not
new CLI/core errors. Exception details belong in server logs, never responses.
No confidence, confirmation requests, turn, castling rights, en passant or full
FEN are added. Only `auto` falls back to White at the bottom when readable clues are absent.

## Work in chess-scanner and the future backend

1. Deploy the [implemented HTTP adapter](http-server.md) at a device-reachable URL.
   It already bounds upload bytes, uses decoder pixel limits and deletes temporary
   files; configure deployment deadlines/capacity and access controls.
2. Use a configurable service URL and multipart bytes in Flutter. Dart's
   [`http` package](https://pub.dev/documentation/http/latest/http/MultipartRequest-class.html)
   exposes `MultipartRequest`; use `MultipartFile.fromBytes` for a shared mobile/web
   path. The [Flutter networking guide](https://docs.flutter.dev/cookbook/networking/send-data)
   describes request handling. Do not bundle Python, OpenCV or a CLI subprocess in Flutter.
3. Decode the JSON once. Pass `piecePlacement` to the existing editor; keep game
   state decisions in the app. Show a clear error for malformed responses, network
   failures, timeouts or structured recognition errors. Allow cancellation/retry
   without creating duplicate board imports.
4. For web, configure CORS for the actual app origins and required methods/headers.
   Use HTTPS for deployed clients. Mobile builds need their platform's networking
   configuration. Authentication/rate limits and hosting belong to deployment design.
5. Test on Android, iOS and a real browser: known images, invalid upload, no board,
   timeout/offline, server failure, CORS and unchanged editor state on failure.
   Verify that the exact placement matches the Python CLI for the same model and view.

This approach requires connectivity, sends images to a server and introduces
hosting/latency costs. If offline recognition becomes a requirement, revisit the
architecture explicitly: model export/native runtimes or a different engine build
would be a separate project, not something this HTTP design already provides.
