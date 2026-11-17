"""Future transport rules preserve CLI semantics without requiring a web framework."""
import json
import pytest

from boardsnap.adapters.http_contract import (
    MAX_IMAGE_BYTES, RequestError, assert_cli_parity, decode_response, response_status, validate_fields,
)


@pytest.mark.parametrize('mode,view',[('digital','auto'),('digital','white-bottom'),('digital','black-bottom'),('photo','white-bottom'),('photo','black-bottom')])
def test_mode_and_orientation_are_mapped_to_core_keywords(mode,view):
    assert validate_fields([('inputType',mode),('orientation',view)],image_count=1,image_bytes=0)=={'input_type':mode,'orientation':view}


@pytest.mark.parametrize('fields,count',[
    ([('inputType','photo'),('orientation','auto')],1),
    ([('inputType','guess'),('orientation','white-bottom')],1),
    ([('inputType','digital')],1),
    ([('inputType','digital'),('inputType','photo'),('orientation','black-bottom')],1),
    ([('inputType','digital'),('orientation','white-bottom'),('model','local.pt')],1),
    ([('inputType','digital'),('orientation','white-bottom')],0),
    ([('inputType','digital'),('orientation','white-bottom')],2),
])
def test_invalid_requests_are_rejected_before_recognition(fields,count):
    with pytest.raises(RequestError) as exc:validate_fields(fields,image_count=count,image_bytes=1)
    assert exc.value.status==400 and exc.value.to_dict()['error']['code']=='INVALID_REQUEST'


def test_byte_limit_inclusive_and_empty_content_left_for_decoder():
    fields=[('inputType','photo'),('orientation','white-bottom')]
    validate_fields(fields,image_count=1,image_bytes=MAX_IMAGE_BYTES)
    validate_fields(fields,image_count=1,image_bytes=0)
    with pytest.raises(RequestError) as exc:validate_fields(fields,image_count=1,image_bytes=MAX_IMAGE_BYTES+1)
    assert exc.value.status==413


@pytest.mark.parametrize('placement',['8/8/8/8/8/8/8/8','rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR'])
def test_only_placement_success_matches_cli(placement):
    payload={'piecePlacement':placement}
    assert assert_cli_parity(payload,0,200,'application/json; charset=utf-8',json.dumps(payload).encode())==payload


@pytest.mark.parametrize('bad',[
    {'piecePlacement':'8/8/8/8/8/8/8/8','confidence':1},
    {'piecePlacement':'8/8/8/8/8/8/8/8 w - - 0 1'},
    {'piecePlacement':'44/8/8/8/8/8/8/8'},
    {'piecePlacement':'9/8/8/8/8/8/8/8'},
    {'piecePlacement':'8/8/8'},
    {'error':{'code':'BOARD_NOT_FOUND','message':'x'},'piecePlacement':'8/8/8/8/8/8/8/8'},
])
def test_unexpected_fields_or_noncanonical_placement_rejected(bad):
    with pytest.raises(ValueError):response_status(bad)


def test_error_code_matches_but_message_is_not_an_api_identifier():
    old={'error':{'code':'BOARD_NOT_FOUND','message':'Old text'}}
    new={'error':{'code':'BOARD_NOT_FOUND','message':'New text'}}
    assert assert_cli_parity(old,1,422,'application/json',json.dumps(new).encode())==new
    with pytest.raises(ValueError):assert_cli_parity(old,1,500,'application/json',json.dumps(new).encode())
    with pytest.raises(ValueError):assert_cli_parity(old,0,422,'application/json',json.dumps(new).encode())


def test_changed_position_is_detected_even_when_http_request_succeeds():
    cli={'piecePlacement':'8/8/8/8/8/8/8/8'}
    wrong={'piecePlacement':'p7/8/8/8/8/8/8/8'}
    with pytest.raises(ValueError,match='disagrees'):assert_cli_parity(cli,0,200,'application/json',json.dumps(wrong).encode())
    with pytest.raises(ValueError):decode_response(b'{"piecePlacement":"x","piecePlacement":"y"}')
    with pytest.raises(ValueError):assert_cli_parity(cli,0,200,'text/html',b'<html>error</html>')


def test_machine_readable_contract_agrees_with_executable_rules():
    from pathlib import Path
    from boardsnap.adapters.http_contract import HTTP_STATUS_BY_ERROR
    root=Path(__file__).resolve().parents[1]
    spec=json.loads((root/'data/manifests/http-contract-v1.json').read_text())
    assert spec['errors']==HTTP_STATUS_BY_ERROR
    assert spec['limits']['imageBytes']==MAX_IMAGE_BYTES
    assert set(spec['fields'])=={'image','inputType','orientation'}
    assert all(field['required'] and field['count']==1 for field in spec['fields'].values())
