import hashlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from open_webui.openrouter.exchange_recorder import ExchangeRecorder
def repository():
    return SimpleNamespace(start=AsyncMock(), append=AsyncMock(), finish=AsyncMock())
def values():
    return {'id': 'exchange', 'user_id': 'a', 'model': 'm', 'run_id': 'run', 'request_body': b'{}', 'original_request': {}, 'policies': []}
@pytest.mark.asyncio
async def test_stream_capture_preserves_bytes_with_split_utf8_and_reasoning():
    # Arrange
    repo = repository()
    recorder = ExchangeRecorder(repo, values())
    body = ('data: ' + json.dumps({'id': 'generation', 'choices': [{'index': 0, 'delta': {'reasoning': 'razón', 'reasoning_details': [{'type': 'reasoning.encrypted', 'data': 'opaque'}]}}]}, ensure_ascii=False) + '\r\n\r\ndata: ' + json.dumps({'choices': [{'index': 0, 'delta': {'content': 'answer'}, 'finish_reason': 'stop'}], 'usage': {'cost': 0.2}}) + '\n\ndata: [DONE]\n\n').encode()
    index = body.index('ó'.encode()) + 1
    chunks = [body[:index], body[index:index+2], body[index+2:]]
    # Act
    await recorder.begin()
    recorder.bind(200, True)
    for chunk in chunks:
        await recorder.record(chunk)
    await recorder.finish()
    result = repo.finish.call_args.kwargs
    # Assert
    assert b''.join(call.args[2] for call in repo.append.call_args_list) == body
    assert result['response_sha256'] == hashlib.sha256(body).hexdigest()
    assert result['state'] == 'completed'
    assert result['response']['choices'][0]['message']['reasoning'] == 'razón'
    assert result['response']['choices'][0]['message']['reasoning_details'][0]['data'] == 'opaque'
    assert result['response']['usage']['cost'] == 0.2
@pytest.mark.asyncio
async def test_stream_without_terminal_marker_is_incomplete():
    # Arrange
    repo = repository()
    recorder = ExchangeRecorder(repo, values())
    # Act
    await recorder.begin()
    recorder.bind(200, True)
    await recorder.record(b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n')
    await recorder.finish()
    # Assert
    assert repo.finish.call_args.kwargs['state'] == 'incomplete'
@pytest.mark.asyncio
async def test_capture_does_not_claim_success_on_database_failure():
    # Arrange
    repo = repository()
    repo.append.side_effect = RuntimeError('database unavailable')
    recorder = ExchangeRecorder(repo, values())
    await recorder.begin()
    recorder.bind(200, True)
    # Act
    error = None
    try:
        await recorder.record(b'sensitive response')
    except RuntimeError as failure:
        error = failure
    await recorder.finish('incomplete')
    # Assert
    assert error is not None
    assert repo.finish.call_args.kwargs['state'] == 'incomplete'
    assert repo.finish.call_args.kwargs['byte_count'] == 0
@pytest.mark.asyncio
async def test_non_streaming_provider_error_keeps_original_body():
    # Arrange
    repo = repository()
    recorder = ExchangeRecorder(repo, values())
    body = b'{ "error": {"message":"rejected"}}'
    # Act
    await recorder.begin()
    recorder.bind(429, False)
    await recorder.record(body)
    recorder.normal_response(body)
    await recorder.finish()
    # Assert
    assert repo.append.call_args.args[2] == body
    assert repo.finish.call_args.kwargs['state'] == 'error'
    assert repo.finish.call_args.kwargs['status_code'] == 429
@pytest.mark.asyncio
async def test_responses_api_terminal_event_and_late_usage_are_captured():
    # Arrange
    repo = repository()
    recorder = ExchangeRecorder(repo, values())
    # Act
    await recorder.begin()
    recorder.bind(200, True)
    await recorder.record(b'event: response.completed\ndata: {"type":"response.completed","response":{"id":"r1","output":[],"usage":{"input_tokens":10}}}\n\n')
    await recorder.finish()
    # Assert
    assert repo.finish.call_args.kwargs['state'] == 'completed'
    assert repo.finish.call_args.kwargs['provider_id'] == 'r1'
    assert repo.finish.call_args.kwargs['response']['usage']['input_tokens'] == 10
