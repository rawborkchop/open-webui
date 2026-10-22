from copy import deepcopy
from open_webui.openrouter.catalog import catalog
def describe(evaluator, *, is_admin=False):
    paths = set(item['path'] for item in catalog())
    paths.update(path for policy in evaluator.policies for path in policy.rules)
    result = {}
    for path in sorted(paths):
        matching = [evaluator.matching_rule(policy, path) for policy in evaluator.policies]
        access = 'editable' if matching and matching[0] else 'read_only'
        rule = {'access': access}
        for item in matching:
            if not item:
                continue
            if item['access'] != 'editable':
                rule['access'] = item['access'] if rule['access'] not in {'hidden', 'server_only'} else rule['access']
            for key in ('type', 'description'):
                if key in item:
                    rule[key] = item[key]
            if 'minimum' in item:
                rule['minimum'] = max(rule.get('minimum', item['minimum']), item['minimum'])
            if 'maximum' in item:
                rule['maximum'] = min(rule.get('maximum', item['maximum']), item['maximum'])
            if 'enum' in item:
                rule['enum'] = [entry for entry in rule['enum'] if entry in item['enum']] if 'enum' in rule else deepcopy(item['enum'])
            if 'value' in item and 'value' not in rule:
                rule['value'] = deepcopy(item['value'])
        if rule['access'] in {'hidden', 'server_only'} and not is_admin:
            continue
        result[path] = rule
    return result
