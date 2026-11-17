"""Framework-independent contract for the future HTTP adapter; no server or I/O."""
import json

from boardsnap.output import build_result

MAX_IMAGE_BYTES = 20 * 1024 * 1024
HTTP_STATUS_BY_ERROR = {
    'INVALID_REQUEST': 400,
    'PAYLOAD_TOO_LARGE': 413,
    'INVALID_IMAGE': 422,
    'UNSUPPORTED_IMAGE': 422,
    'BOARD_NOT_FOUND': 422,
    'INPUT_READ_ERROR': 500,
    'PROCESSING_FAILED': 500,
}


class RequestError(ValueError):
    """Transport validation failure, before calling recognition."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message
        self.status = HTTP_STATUS_BY_ERROR[code]

    def to_dict(self):
        return {'error': {'code': self.code, 'message': self.message}}


def validate_fields(fields, *, image_count, image_bytes):
    """Validate ordered text parts, preserving duplicates instead of collapsing them.

    A future multipart parser must pass unexpected file parts as invalid requests
    too, and enforce the total body limit before buffering uploaded bytes.
    """
    if (len(fields) != 2 or {key for key, _ in fields} != {'inputType', 'orientation'}
            or image_count != 1):
        raise RequestError('INVALID_REQUEST', 'Provide exactly one image, inputType and orientation.')
    values = dict(fields)
    mode, view = values['inputType'], values['orientation']
    if mode not in ('digital', 'photo') or view not in ('white-bottom', 'black-bottom', 'auto'):
        raise RequestError('INVALID_REQUEST', 'Invalid inputType or orientation.')
    if mode == 'photo' and view == 'auto':
        raise RequestError('INVALID_REQUEST', 'Photographs require an explicit orientation.')
    if type(image_bytes) is not int or image_bytes < 0:
        raise ValueError('Expected an upload byte count.')
    if image_bytes > MAX_IMAGE_BYTES:
        raise RequestError('PAYLOAD_TOO_LARGE', 'Image exceeds the 20 MiB upload limit.')
    # Empty content is passed to the decoder, producing INVALID_IMAGE (422).
    return {'input_type': mode, 'orientation': view}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key.')
        result[key] = value
    return result


def decode_response(body):
    return json.loads(body.decode('utf-8'), object_pairs_hook=_unique_object)


def response_status(result):
    """Validate the exact JSON schema, including canonical piece placement."""
    if not isinstance(result, dict):
        raise ValueError('Expected a JSON object.')
    if set(result) == {'piecePlacement'}:
        placement = result['piecePlacement']
        if not isinstance(placement, str):
            raise ValueError('Expected piece placement text.')
        board = []
        for rank in placement.split('/'):
            row = []
            for symbol in rank:
                if symbol in '12345678': row.extend([None] * int(symbol))
                elif symbol in 'PNBRQKpnbrqk': row.append(symbol)
                else: raise ValueError('Invalid piece placement symbol.')
            board.append(row)
        if build_result(board) != result:
            raise ValueError('Piece placement must use canonical empty runs.')
        return 200
    if set(result) == {'error'} and isinstance(result['error'], dict):
        error = result['error']
        if (set(error) == {'code', 'message'} and isinstance(error['message'], str)
                and error['message'] and isinstance(error['code'], str)
                and error['code'] in HTTP_STATUS_BY_ERROR):
            return HTTP_STATUS_BY_ERROR[error['code']]
    raise ValueError('Unexpected response fields or error code.')


def assert_cli_parity(cli_result, cli_exit, status, content_type, body):
    """Success placement must match exactly; error messages may vary by transport."""
    if content_type.split(';', 1)[0].strip().lower() != 'application/json':
        raise ValueError('Expected application/json.')
    http_result = decode_response(body)
    expected_status = response_status(cli_result)
    if cli_exit != (0 if expected_status == 200 else 1):
        raise ValueError('CLI exit status disagrees with its JSON.')
    if response_status(http_result) != status or status != expected_status:
        raise ValueError('HTTP status or error mapping disagrees with CLI.')
    if status == 200:
        if http_result != cli_result:
            raise ValueError('HTTP piece placement disagrees with CLI.')
    elif http_result['error']['code'] != cli_result['error']['code']:
        raise ValueError('HTTP error code disagrees with CLI.')
    return http_result
