from copy import deepcopy
from open_webui.openrouter.json_paths import get_path, leaves, remove_path, set_path
from open_webui.openrouter.parameter_policy import ParameterPolicy
class ParameterPolicyEvaluator:
    def __init__(self, policies):
        self.policies = sorted(policies, key=lambda p: ({'global': 0, 'model': 1, 'group': 2, 'user': 3}[p.scope], p.target))
    @staticmethod
    def matching_rule(policy, path):
        candidates = [key for key in policy.rules if path == key or path.startswith(key + '.')]
        return policy.rules[max(candidates, key=len)] if candidates else None
    def authorize(self, parameters, *, is_admin):
        if not isinstance(parameters, dict):
            raise ValueError('Parameters must be an object')
        if is_admin:
            return deepcopy(parameters)
        for path, value in leaves(parameters):
            if not path:
                continue
            rules = [self.matching_rule(p, path) for p in self.policies]
            if not self.policies or self.policies[0].scope != 'global' or rules[0] is None:
                raise ValueError(f'{path}: parameter is not permitted')
            for rule in rules:
                if rule is None:
                    continue
                if rule['access'] != 'editable':
                    if rule['access'] == 'read_only' and 'value' in rule and type(value) is type(rule['value']) and value == rule['value']:
                        continue
                    raise ValueError(f'{path}: parameter is {rule["access"]}')
                # An object rule authorizes its children; validate that container separately.
                leaf_rule = dict(rule)
                if rule.get('type') == 'object':
                    leaf_rule.pop('type')
                ParameterPolicy.validate_value(path, value, leaf_rule)
        for policy in self.policies:
            for path, rule in policy.rules.items():
                sentinel = object()
                value = get_path(parameters, path, sentinel)
                if value is not sentinel and rule.get('type') == 'object':
                    ParameterPolicy.validate_value(path, value, rule)
        return deepcopy(parameters)
    def apply(self, payload):
        result = deepcopy(payload)
        for policy in self.policies:
            for path, rule in policy.rules.items():
                if 'value' in rule and (rule['access'] != 'editable' or get_path(result, path) is None):
                    set_path(result, path, rule['value'])
        # Narrower scopes cannot replace a globally mandatory value.
        for policy in reversed(self.policies):
            for path, rule in policy.rules.items():
                if 'value' in rule and rule['access'] != 'editable':
                    set_path(result, path, rule['value'])
        sentinel = object()
        for policy in self.policies:
            for path, rule in policy.rules.items():
                value = get_path(result, path, sentinel)
                if value is not sentinel:
                    ParameterPolicy.validate_value(path, value, rule)
        return result
    def visible(self, payload):
        result = deepcopy(payload)
        for policy in self.policies:
            for path, rule in policy.rules.items():
                if rule['access'] in {'hidden', 'server_only'}:
                    remove_path(result, path)
        return result
    def snapshot(self):
        return [{'scope': p.scope, 'target': p.target, 'version': p.version, 'rules': p.rules} for p in self.policies]
