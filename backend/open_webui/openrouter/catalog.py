"""Versioned starter catalog; unknown fields remain inspectable and denied to users."""
CATALOG_VERSION = '2026-10-22'
_FIELDS = [
    ('stream', 'boolean', 'Transport', 'Stream the provider response.', None, None),
    ('stream_options.include_usage', 'boolean', 'Transport', 'Include final usage in streams.', None, None),
    ('temperature', 'number', 'Sampling', 'Controls randomness.', 0, 2),
    ('top_p', 'number', 'Sampling', 'Nucleus sampling probability.', 0, 1),
    ('top_k', 'integer', 'Sampling', 'Number of candidate tokens.', 0, None),
    ('min_p', 'number', 'Sampling', 'Minimum relative token probability.', 0, 1),
    ('top_a', 'number', 'Sampling', 'Adaptive token sampling.', 0, 1),
    ('seed', 'integer', 'Sampling', 'Optional generation seed.', None, None),
    ('frequency_penalty', 'number', 'Sampling', 'Penalizes repeated tokens.', -2, 2),
    ('presence_penalty', 'number', 'Sampling', 'Penalizes tokens already present.', -2, 2),
    ('repetition_penalty', 'number', 'Sampling', 'Controls repetition.', 0, 2),
    ('max_tokens', 'integer', 'Output', 'Output limit; includes reasoning on most providers. Also governs max_completion_tokens and max_output_tokens.', 1, None),
    ('stop', 'any', 'Output', 'Stop sequence or sequence array.', None, None),
    ('response_format', 'object', 'Output', 'JSON mode or structured output schema.', None, None),
    ('text', 'object', 'Output', 'Responses API text output options.', None, None),
    ('logit_bias', 'object', 'Output', 'Per-token bias map.', None, None),
    ('logprobs', 'boolean', 'Output', 'Return token log probabilities.', None, None),
    ('top_logprobs', 'integer', 'Output', 'Number of token alternatives.', 0, 20),
    ('prediction', 'object', 'Output', 'Predicted output configuration.', None, None),
    ('verbosity', 'string', 'Output', 'Provider-specific response verbosity.', None, None),
    ('reasoning.effort', 'string', 'Reasoning', 'Model-supported reasoning effort.', None, None),
    ('reasoning.max_tokens', 'integer', 'Reasoning', 'Reasoning token budget.', 1, None),
    ('reasoning.enabled', 'boolean', 'Reasoning', 'Enable reasoning when supported.', None, None),
    ('reasoning.exclude', 'boolean', 'Reasoning', 'Whether to omit available reasoning from the response.', None, None),
    ('reasoning.summary', 'string', 'Reasoning', 'Reasoning summary preference.', None, None),
    ('provider.order', 'array', 'Routing', 'Ordered provider slugs.', None, None),
    ('provider.allow_fallbacks', 'boolean', 'Routing', 'Allow provider fallback.', None, None),
    ('provider.require_parameters', 'boolean', 'Routing', 'Require support for requested parameters.', None, None),
    ('provider.data_collection', 'string', 'Routing', 'Provider data collection policy.', None, None),
    ('provider.zdr', 'boolean', 'Routing', 'Require zero data retention.', None, None),
    ('provider.only', 'array', 'Routing', 'Allowed providers.', None, None),
    ('provider.ignore', 'array', 'Routing', 'Excluded providers.', None, None),
    ('provider.quantizations', 'array', 'Routing', 'Allowed quantizations.', None, None),
    ('provider.sort', 'any', 'Routing', 'Provider sorting strategy.', None, None),
    ('provider.max_price', 'object', 'Routing', 'Maximum provider pricing.', None, None),
    ('provider.preferred_min_throughput', 'any', 'Routing', 'Preferred throughput threshold.', None, None),
    ('provider.preferred_max_latency', 'any', 'Routing', 'Preferred latency threshold.', None, None),
    ('models', 'array', 'Routing', 'Fallback model IDs; model access is checked separately.', None, None),
    ('route', 'string', 'Routing', 'Model routing strategy.', None, None),
    ('tools', 'array', 'Tools', 'Tool definitions.', None, None),
    ('tool_choice', 'any', 'Tools', 'Tool selection strategy.', None, None),
    ('parallel_tool_calls', 'boolean', 'Tools', 'Allow parallel tool calls.', None, None),
    ('plugins', 'array', 'Extensions', 'OpenRouter plugins and their options.', None, None),
    ('transforms', 'array', 'Extensions', 'Message transforms.', None, None),
    ('modalities', 'array', 'Multimodal', 'Requested output modalities.', None, None),
    ('audio', 'object', 'Multimodal', 'Audio generation options.', None, None),
    ('image_config', 'object', 'Multimodal', 'Image generation options.', None, None),
    ('dimensions', 'integer', 'Embeddings', 'Embedding vector dimensions.', 1, None),
    ('encoding_format', 'string', 'Embeddings', 'Embedding response encoding.', None, None),
    ('truncation', 'string', 'Responses', 'Context truncation strategy.', None, None),
    ('store', 'boolean', 'Responses', 'Provider-side response storage.', None, None),
    ('previous_response_id', 'string', 'Responses', 'Previous provider response; restricted to the same owner.', None, None),
    ('system', 'any', 'Messages', 'System/developer messages supplied by the client.', None, None),
    ('user', 'string', 'Identity', 'Stable end-user identifier managed by the server.', None, None),
    ('debug', 'object', 'Advanced', 'Provider debugging options.', None, None),
    ('metadata', 'object', 'Advanced', 'Provider request metadata.', None, None),
]
def catalog():
    return [dict(path=path, type=kind, category=category, description=description,
        **({'minimum': minimum} if minimum is not None else {}),
        **({'maximum': maximum} if maximum is not None else {}))
        for path, kind, category, description, minimum, maximum in _FIELDS]
def default_rules():
    rules = {field['path']: {key: value for key, value in field.items() if key in {'type', 'minimum', 'maximum'}} | {'access': 'read_only'} for field in catalog()}
    rules['reasoning.exclude']['value'] = False
    rules['stream']['access'] = 'editable'
    rules['stream_options.include_usage']['value'] = True
    rules['user']['access'] = 'server_only'
    rules['debug']['access'] = 'hidden'
    return rules
