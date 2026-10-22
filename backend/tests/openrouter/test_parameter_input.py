from open_webui.openrouter.parameter_input import parameter_input, canonical_payload
def test_custom_json_and_token_aliases_are_normalized_before_authorization():
    # Arrange
    body = {'model': 'm', 'messages': [], 'params': {'custom_params': {'reasoning': '{"effort":"high"}'}, 'max_completion_tokens': 200}}
    # Act
    result = parameter_input(body)
    # Assert
    assert result == {'reasoning': {'effort': 'high'}, 'max_tokens': 200}
def test_top_level_parameters_cannot_hide_behind_nested_params():
    # Arrange
    body = {'temperature': 2, 'params': {'temperature': 0.5}}
    # Act
    error = None
    try:
        parameter_input(body)
    except ValueError as failure:
        error = failure
    # Assert
    assert error is not None
def test_unknown_top_level_parameter_remains_subject_to_policy():
    # Arrange
    body = {'model': 'm', 'messages': [], 'future_parameter': True, 'chat_id': 'c'}
    # Act
    result = parameter_input(body)
    # Assert
    assert result == {'future_parameter': True}
def test_system_messages_are_treated_as_a_controlled_input():
    # Arrange
    body = {'messages': [{'role': 'system', 'content': 'override'}, {'role': 'user', 'content': 'question'}]}
    # Act
    result = parameter_input(body)
    # Assert
    assert result['system'] == 'override'
def test_response_payload_uses_same_canonical_token_limit():
    # Arrange
    body = {'model': 'm', 'max_output_tokens': 500}
    # Act
    result = canonical_payload(body)
    # Assert
    assert result == {'model': 'm', 'max_tokens': 500}
def test_webui_duplicate_system_source_is_normalized_once():
    # Arrange
    body = {'params': {'system': 'Allowed prompt'}, 'messages': [{'role': 'system', 'content': 'Allowed prompt'}]}
    # Act
    result = parameter_input(body)
    # Assert
    assert result == {'system': 'Allowed prompt'}
