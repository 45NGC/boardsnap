# Flutter integration design

[Spanish](../es/flutter-integration.md) · [Overview](README.md)

Target platforms: **Android, iOS and web**, as requested for chess-scanner.
The proposed transport is **an HTTPS API around the Python core**. This gives all
three clients the same recognition implementation. This document specifies that
adapter; **no server, deployment or Flutter client is implemented here**.
The CLI remains a local development tool. A mobile or browser client cannot use
an installed desktop Python command as its integration mechanism.

## Responsibilities and proposed request

A separately implemented backend calls
`recognize_image(temporary_path, profile=profile_id)`. It owns temporary uploads,
request limits, concurrency and response serialization. The core remains
independent of its web framework. Flutter owns image selection, HTTP transport,
the board editor and all remaining game state.

Proposed endpoint: `POST /v1/recognize`, multipart form data:

- `image`: one PNG/JPEG file, sent as bytes; do not send a local device path.
- `profile`: one of the [evaluated profile IDs](profiles.md). Omission uses
  `lichess-cburnett-brown-v1`, matching the CLI. Unknown IDs are request errors.

Success, HTTP 200, `Content-Type: application/json`:

```json
{"piecePlacement":"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"}
```

The [existing contract](output-contract.md) is unchanged. Errors use only
`{"error":{"code":"...","message":"..."}}`, without a success payload.
Suggested mappings for the future adapter:

| HTTP status | Code | Meaning |
| --- | --- | --- |
| 400 | `INVALID_REQUEST` | Missing/multiple files or unknown profile; adapter validation. |
| 413 | `PAYLOAD_TOO_LARGE` | Upload exceeds the configured byte limit; adapter validation. |
| 422 | `INVALID_IMAGE`, `UNSUPPORTED_IMAGE`, `BOARD_NOT_FOUND` | Core cannot process the supplied image. |
| 500 | `INPUT_READ_ERROR`, `PROCESSING_FAILED` | Server could not read its temporary file or process the image. |

The two request-validation codes above are **proposed HTTP-only codes**, not
new CLI/core errors. Exception details belong in server logs, never responses.
No confidence, confirmation requests, turn, castling rights, en passant or full
FEN are added. Missing readable orientation clues still mean White at the bottom.

## Work in chess-scanner and the future backend

1. Implement and deploy the small Python HTTP adapter separately before connecting
   Flutter. Set explicit upload/dimension/time limits and delete temporary files
   after both success and failure. Do not retain uploaded images by default.
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
   Verify that the exact placement matches the Python CLI for the same profile.

This approach requires connectivity, sends images to a server and introduces
hosting/latency costs. If offline recognition becomes a requirement, revisit the
architecture explicitly: model export/native runtimes or a different engine build
would be a separate project, not something this HTTP design already provides.
