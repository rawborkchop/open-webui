from open_webui.openrouter.catalog import default_rules
from open_webui.openrouter.parameter_policy import ParameterPolicy
from open_webui.openrouter.parameter_policy_evaluator import ParameterPolicyEvaluator
def repository():
    from open_webui.internal.db import AsyncSessionLocal
    from open_webui.openrouter.sqlalchemy_exchange_repository import SQLAlchemyExchangeRepository
    return SQLAlchemyExchangeRepository(AsyncSessionLocal)
async def evaluator_for(user, model, *, group_ids=None, store=None):
    store = store or repository()
    if group_ids is None:
        from open_webui.models.groups import Groups
        group_ids = {group.id for group in await Groups.get_groups_by_member_id(user.id, include_inherited=True)}
    models = {model} if isinstance(model, str) else set(model)
    records = await store.policies()
    selected = [ParameterPolicy('global', '*', 0, default_rules())]
    for record in records:
        scope, target = record['scope'], record['target']
        if scope == 'global':
            selected[0] = ParameterPolicy(scope, target, record['version'], record['rules'])
        elif (scope == 'model' and target in models) or (scope == 'user' and target == user.id) or (scope == 'group' and target in group_ids):
            selected.append(ParameterPolicy(scope, target, record['version'], record['rules']))
    return ParameterPolicyEvaluator(selected)
