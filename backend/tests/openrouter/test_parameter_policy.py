import pytest
from open_webui.openrouter.parameter_policy import ParameterPolicy
from open_webui.openrouter.parameter_policy_evaluator import ParameterPolicyEvaluator
def policy(rules, scope='global', target='*'):
    return ParameterPolicy(scope=scope, target=target, version=1, rules=rules)
def test_user_can_only_change_explicitly_editable_parameters():
    # Arrange
    evaluator = ParameterPolicyEvaluator([policy({'temperature': {'access': 'editable', 'type': 'number', 'minimum': 0, 'maximum': 1}})])
    # Act
    accepted = evaluator.authorize({'temperature': 0.7}, is_admin=False)
    rejected = None
    try:
        evaluator.authorize({'top_p': 0.9}, is_admin=False)
    except ValueError as error:
        rejected = str(error)
    # Assert
    assert accepted == {'temperature': 0.7}
    assert 'top_p' in rejected
@pytest.mark.parametrize('value', [True, '0.5', -1, 2, float('nan'), float('inf'), None])
def test_numeric_rules_reject_invalid_types_and_ranges(value):
    # Arrange
    evaluator = ParameterPolicyEvaluator([policy({'temperature': {'access': 'editable', 'type': 'number', 'minimum': 0, 'maximum': 1}})])
    # Act
    error = None
    try:
        evaluator.authorize({'temperature': value}, is_admin=False)
    except ValueError as failure:
        error = failure
    # Assert
    assert error is not None
def test_nested_allowance_does_not_allow_its_siblings():
    # Arrange
    evaluator = ParameterPolicyEvaluator([policy({'reasoning.effort': {'access': 'editable', 'type': 'string', 'enum': ['low', 'high']}})])
    # Act
    allowed = evaluator.authorize({'reasoning': {'effort': 'high'}}, is_admin=False)
    error = None
    try:
        evaluator.authorize({'reasoning': {'effort': 'high', 'exclude': True}}, is_admin=False)
    except ValueError as failure:
        error = str(failure)
    # Assert
    assert allowed['reasoning']['effort'] == 'high'
    assert 'reasoning.exclude' in error
def test_specific_scope_cannot_widen_global_permissions():
    # Arrange
    evaluator = ParameterPolicyEvaluator([policy({'temperature': {'access': 'read_only', 'value': 0.5}}), policy({'temperature': {'access': 'editable'}}, 'user', 'a')])
    # Act
    error = None
    try:
        evaluator.authorize({'temperature': 1}, is_admin=False)
    except ValueError as failure:
        error = failure
    # Assert
    assert error is not None
def test_specific_scope_can_restrict_global_range():
    # Arrange
    evaluator = ParameterPolicyEvaluator([policy({'temperature': {'access': 'editable', 'type': 'number', 'maximum': 2}}), policy({'temperature': {'access': 'editable', 'maximum': 0.5}}, 'model', 'm')])
    # Act
    error = None
    try:
        evaluator.authorize({'temperature': 0.8}, is_admin=False)
    except ValueError as failure:
        error = failure
    # Assert
    assert error is not None
def test_mandatory_values_override_model_defaults_without_mutating_input():
    # Arrange
    evaluator = ParameterPolicyEvaluator([policy({'reasoning.exclude': {'access': 'read_only', 'type': 'boolean', 'value': False}})])
    payload = {'messages': [], 'reasoning': {'exclude': True, 'effort': 'high'}}
    # Act
    result = evaluator.apply(payload)
    # Assert
    assert result['reasoning'] == {'exclude': False, 'effort': 'high'}
    assert payload['reasoning']['exclude'] is True
def test_parent_rule_does_not_override_more_specific_restriction():
    # Arrange
    evaluator = ParameterPolicyEvaluator([policy({'provider': {'access': 'editable', 'type': 'object'}, 'provider.allow_fallbacks': {'access': 'read_only', 'value': False}})])
    # Act
    error = None
    try:
        evaluator.authorize({'provider': {'allow_fallbacks': True}}, is_admin=False)
    except ValueError as failure:
        error = failure
    # Assert
    assert error is not None
def test_admin_can_inspect_and_send_unknown_provider_parameters():
    # Arrange
    evaluator = ParameterPolicyEvaluator([policy({})])
    # Act
    result = evaluator.authorize({'future_parameter': {'x': 1}}, is_admin=True)
    # Assert
    assert result == {'future_parameter': {'x': 1}}
@pytest.mark.parametrize('rule', [{'access': 'anything'}, {'access': 'editable', 'minimum': 2, 'maximum': 1}, {'access': 'editable', 'type': 'unknown'}])
def test_invalid_policy_cannot_be_saved(rule):
    # Arrange
    error = None
    # Act
    try:
        policy({'temperature': rule})
    except ValueError as failure:
        error = failure
    # Assert
    assert error is not None
def test_hidden_and_server_only_values_are_removed_from_user_inspection():
    # Arrange
    evaluator = ParameterPolicyEvaluator([policy({'provider.order': {'access': 'hidden', 'value': ['private']}, 'user': {'access': 'server_only'}})])
    # Act
    result = evaluator.visible({'provider': {'order': ['private'], 'allow_fallbacks': False}, 'user': 'internal-id', 'messages': []})
    # Assert
    assert result == {'provider': {'allow_fallbacks': False}, 'messages': []}
def test_specific_defaults_cannot_bypass_global_range():
    # Arrange
    evaluator = ParameterPolicyEvaluator([policy({'max_tokens': {'access': 'editable', 'type': 'integer', 'maximum': 100}}), policy({'max_tokens': {'access': 'editable', 'value': 1000}}, 'model', 'm')])
    error = None
    # Act
    try:
        evaluator.apply({'model': 'm'})
    except ValueError as failure:
        error = failure
    # Assert
    assert error is not None
