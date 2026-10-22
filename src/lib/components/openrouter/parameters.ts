import type { ParameterRule } from '$lib/apis/openrouter';
type Parameters = Record<string, any>;
const webuiFields = new Set(['stream_response', 'stream_delta_chunk_size', 'function_calling', 'reasoning_tags', 'compact_token_threshold', 'note_id', 'tool_approval_mode', 'model_controls']);
function customValues(params: Parameters): Parameters {
	const result = structuredClone(params.custom_params ?? {});
	for (const key of Object.keys(result)) if (typeof result[key] === 'string') {
		try { result[key] = JSON.parse(result[key]); } catch { /* Existing custom parameters also permit plain strings. */ }
	}
	return result;
}
export function readParameter(params: Parameters, path: string): unknown {
	let value: any = { ...params, ...customValues(params) };
	for (const key of path.split('.')) value = value?.[key];
	if (value === undefined && path === 'reasoning.effort') return params.reasoning_effort;
	if (value === undefined && path === 'max_tokens') return params.max_completion_tokens ?? params.max_output_tokens;
	return value;
}
export function updateParameter(params: Parameters, path: string, raw: string, rule: ParameterRule): Parameters {
	const result = structuredClone(params);
	const custom = customValues(params);
	const parts = path.split('.');
	if (parts.some(part => !/^[a-zA-Z][a-zA-Z0-9_]*$/.test(part) || ['constructor', 'prototype', '__proto__'].includes(part))) throw new Error('Ruta de parámetro inválida');
	let target = custom;
	if (parts.length > 1 && custom[parts[0]] === undefined && typeof result[parts[0]] === 'object') custom[parts[0]] = structuredClone(result[parts[0]]);
	for (const part of parts.slice(0, -1)) {
		if (typeof target[part] !== 'object' || target[part] === null || Array.isArray(target[part])) target[part] = {};
		target = target[part];
	}
	const key = parts.at(-1)!;
	if (raw === '') delete target[key];
	else target[key] = rule.type === 'string' ? raw : JSON.parse(raw);
	delete result[parts[0]];
	if (path === 'reasoning.effort') delete result.reasoning_effort;
	if (path === 'max_tokens') { delete result.max_completion_tokens; delete result.max_output_tokens; }
	result.custom_params = custom;
	return result;
}
export function resetProviderOverrides(params: Parameters): Parameters {
	return { ...Object.fromEntries(Object.entries(params).filter(([key]) => webuiFields.has(key))), custom_params: {} };
}
