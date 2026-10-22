from dataclasses import dataclass
from copy import deepcopy
import math
import re
@dataclass(frozen=True)
class ParameterPolicy:
    scope: str
    target: str
    version: int
    rules: dict
    def __post_init__(self):
        if self.scope not in {'global', 'model', 'group', 'user'}:
            raise ValueError('Invalid policy scope')
        if not self.target or len(self.target) > 256 or (self.scope == 'global' and self.target != '*'):
            raise ValueError('Invalid policy target')
        if not isinstance(self.rules, dict) or len(self.rules) > 256:
            raise ValueError('Policy rules must be an object with at most 256 paths')
        for path, rule in self.rules.items():
            if not isinstance(path, str) or len(path) > 256 or not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*', path):
                raise ValueError(f'Invalid parameter path: {path}')
            self.validate_rule(path, rule)
        object.__setattr__(self, 'rules', deepcopy(self.rules))
    @staticmethod
    def validate_rule(path, rule):
        allowed = {'access', 'type', 'minimum', 'maximum', 'enum', 'value', 'description'}
        if not isinstance(rule, dict) or set(rule) - allowed:
            raise ValueError(f'{path}: invalid rule fields')
        if rule.get('access') not in {'editable', 'read_only', 'hidden', 'server_only'}:
            raise ValueError(f'{path}: invalid access')
        if rule.get('type', 'any') not in {'any', 'number', 'integer', 'string', 'boolean', 'object', 'array'}:
            raise ValueError(f'{path}: invalid type')
        for key in ('minimum', 'maximum'):
            if key in rule and (type(rule[key]) not in (int, float) or not math.isfinite(rule[key])):
                raise ValueError(f'{path}: invalid {key}')
        if rule.get('minimum', -math.inf) > rule.get('maximum', math.inf):
            raise ValueError(f'{path}: minimum exceeds maximum')
        if 'enum' in rule and (not isinstance(rule['enum'], list) or not rule['enum']):
            raise ValueError(f'{path}: enum must be a nonempty array')
        if 'value' in rule:
            ParameterPolicy.validate_value(path, rule['value'], rule)
    @staticmethod
    def validate_value(path, value, rule):
        kind = rule.get('type', 'any')
        valid = {'any': value is not None, 'number': type(value) in (int, float), 'integer': type(value) is int,
                 'string': isinstance(value, str), 'boolean': type(value) is bool,
                 'object': isinstance(value, dict), 'array': isinstance(value, list)}
        if not valid[kind]:
            raise ValueError(f'{path}: expected {kind}')
        if type(value) in (int, float):
            if not math.isfinite(value) or value < rule.get('minimum', -math.inf) or value > rule.get('maximum', math.inf):
                raise ValueError(f'{path}: value outside permitted range')
        if 'enum' in rule and not any(type(value) is type(option) and value == option for option in rule['enum']):
            raise ValueError(f'{path}: value is not an approved option')
