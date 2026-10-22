from copy import deepcopy
def leaves(value, prefix=''):
    if isinstance(value, dict) and value:
        for key, child in value.items():
            if not isinstance(key, str) or '.' in key or key.startswith('__'):
                raise ValueError('Invalid parameter key')
            yield from leaves(child, f'{prefix}.{key}' if prefix else key)
    else:
        yield prefix, value
def get_path(value, path, missing=None):
    for key in path.split('.'):
        if not isinstance(value, dict) or key not in value:
            return missing
        value = value[key]
    return value
def set_path(value, path, item):
    keys = path.split('.')
    for key in keys[:-1]:
        if not isinstance(value.get(key), dict):
            value[key] = {}
        value = value[key]
    value[keys[-1]] = deepcopy(item)
def remove_path(value, path):
    keys = path.split('.')
    parent = value
    for key in keys[:-1]:
        if not isinstance(parent.get(key), dict):
            return
        parent = parent[key]
    parent.pop(keys[-1], None)
