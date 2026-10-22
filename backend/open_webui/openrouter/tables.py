from open_webui.openrouter.parameter_policy_record import ParameterPolicyRecord
from open_webui.openrouter.parameter_policy_revision import ParameterPolicyRevision
from open_webui.openrouter.provider_exchange import ProviderExchange
from open_webui.openrouter.provider_exchange_chunk import ProviderExchangeChunk
def tables():
    return [ParameterPolicyRecord.__table__, ParameterPolicyRevision.__table__, ProviderExchange.__table__, ProviderExchangeChunk.__table__]
