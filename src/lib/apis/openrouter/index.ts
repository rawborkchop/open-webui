import { WEBUI_API_BASE_URL } from '$lib/constants';
export type ParameterRule = {
	access: 'editable' | 'read_only' | 'hidden' | 'server_only';
	type?: string;
	minimum?: number;
	maximum?: number;
	enum?: unknown[];
	value?: unknown;
	description?: string;
};
export type Policy = {
	scope: 'global' | 'model' | 'group' | 'user';
	target: string;
	version: number;
	rules: Record<string, ParameterRule>;
	actor_id?: string;
};
export type CatalogEntry = {
	path: string;
	type: string;
	category: string;
	description: string;
	supported: boolean | null;
};
export type EffectivePolicy = {
	model: string;
	user_id: string;
	rules: Record<string, ParameterRule>;
	versions: { scope: string; version: number }[];
};
export type ExchangeSummary = {
	id: string;
	user_id: string;
	chat_id: string | null;
	message_id: string | null;
	model: string;
	state: string;
	purpose: string;
	status_code: number | null;
	byte_count: number;
	created_at: number;
	finished_at: number | null;
	provider_id: string | null;
};
export type ExchangeDetail = ExchangeSummary & {
	request: Record<string, unknown>;
	original_request: Record<string, unknown>;
	response: Record<string, unknown> | null;
	policies: unknown[];
	request_sha256: string;
	response_sha256: string | null;
	error: string | null;
	files: unknown[];
	request_raw_base64?: string;
};
const endpoint = `${WEBUI_API_BASE_URL}/openrouter`;
export async function openrouterRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
	const response = await fetch(`${endpoint}${path}`, {
		...options,
		headers: { 'Content-Type': 'application/json', authorization: `Bearer ${localStorage.token}`, ...options.headers }
	});
	if (!response.ok) {
		const body = await response.json().catch(() => ({}));
		throw new Error(typeof body.detail === 'string' ? body.detail : `Error ${response.status}`);
	}
	return response.json();
}
export const getCatalog = (model: string, signal?: AbortSignal) =>
	openrouterRequest<{ version: string; items: CatalogEntry[] }>(`/catalog?${new URLSearchParams({ model })}`, { signal });
export const getEffectivePolicy = (model: string, userId = '', signal?: AbortSignal) =>
	openrouterRequest<EffectivePolicy>(`/effective?${new URLSearchParams({ model, ...(userId ? { user_id: userId } : {}) })}`, { signal });
export const getPolicies = () => openrouterRequest<Policy[]>('/policies');
export const savePolicy = (policy: Policy) => openrouterRequest<Policy>('/policies', {
	method: 'PUT', body: JSON.stringify({ scope: policy.scope, target: policy.target, expected_version: policy.version, rules: policy.rules })
});
export const getPolicyHistory = (scope: string, target: string) =>
	openrouterRequest<{ version: number; actor_id: string; created_at: number; rules: Record<string, ParameterRule> }[]>(`/policies/history?${new URLSearchParams({ scope, target })}`);
export const getExchanges = (query: URLSearchParams, signal?: AbortSignal) =>
	openrouterRequest<{ items: ExchangeSummary[]; total: number }>(`/exchanges?${query}`, { signal });
export const getExchange = (id: string, signal?: AbortSignal) =>
	openrouterRequest<ExchangeDetail>(`/exchanges/${encodeURIComponent(id)}`, { signal });
export async function downloadExchange(id: string, format: 'export' | 'request' | 'response') {
	const path = format === 'export' ? 'export' : `raw?direction=${format}`;
	const response = await fetch(`${endpoint}/exchanges/${encodeURIComponent(id)}/${path}`, {
		headers: { authorization: `Bearer ${localStorage.token}` }
	});
	if (!response.ok) throw new Error(`No se pudo descargar (${response.status})`);
	const url = URL.createObjectURL(await response.blob());
	const anchor = document.createElement('a');
	anchor.href = url;
	anchor.download = `${id}-${format}.${format === 'export' ? 'json' : 'bin'}`;
	anchor.click();
	URL.revokeObjectURL(url);
}
