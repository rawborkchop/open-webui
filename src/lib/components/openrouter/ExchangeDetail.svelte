<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { getExchange, downloadExchange, type ExchangeDetail } from '$lib/apis/openrouter';
	import JsonView from './JsonView.svelte';
	export let exchangeId = '';
	export let admin = false;
	let mounted = false;
	let record: ExchangeDetail | null = null;
	let loading = false;
	let error = '';
	let tab = 'response';
	let controller: AbortController | undefined;
	const tabs = [{ id: 'response', label: 'Respuesta' }, { id: 'request', label: 'Entrada efectiva' }, { id: 'original_request', label: 'Entrada original' }, { id: 'policies', label: 'Política aplicada' }];
	async function load(id: string) {
		controller?.abort();
		const current = new AbortController(); controller = current;
		loading = true; error = ''; record = null;
		try { const result = await getExchange(id, current.signal); if (!current.signal.aborted) record = result; }
		catch (failure) { if (!current.signal.aborted) error = String(failure); }
		finally { if (!current.signal.aborted) loading = false; }
	}
	async function download(format: 'export' | 'request' | 'response') {
		try { await downloadExchange(exchangeId, format); } catch (failure) { error = String(failure); }
	}
	$: if (mounted && exchangeId) void load(exchangeId);
	$: displayed = record ? ({ response: record.response, request: record.request, original_request: record.original_request, policies: record.policies } as Record<string, unknown>)[tab] : null;
	onMount(() => { mounted = true; });
	onDestroy(() => controller?.abort());
</script>
<section aria-label="Detalle del intercambio" class="or-detail">
	{#if error}<p class="or-error" role="alert">{error}</p>{/if}
	{#if loading}<p class="or-muted" role="status">Cargando intercambio…</p>
	{:else if record}
		<div class="or-section-heading"><div><span class="or-eyebrow">INTERCAMBIO</span><h2>{record.model}</h2></div><span class="or-state" data-state={record.state}>{record.state}</span></div>
		<p class="or-muted">{new Date(record.created_at).toLocaleString()} · {record.byte_count.toLocaleString()} bytes · HTTP {record.status_code ?? '—'} · {record.purpose}</p>
		{#if record.state !== 'completed'}<p class="or-notice">{record.state === 'recording' ? 'Captura en curso. Si el proceso se interrumpe, este registro permanece sin completar.' : 'Este intercambio no terminó correctamente. Se conservan los datos recibidos.'}</p>{/if}
		{#if record.error}<p class="or-error">{record.error}</p>{/if}
		<div class="or-toolbar">
			<button class="or-button" on:click={() => load(exchangeId)}>Actualizar</button>
			<button class="or-button" on:click={() => download('export')}>Exportar intercambio</button>
			<button class="or-button" on:click={() => download('response')}>Respuesta original</button>
			{#if admin}<button class="or-button" on:click={() => download('request')}>Petición original</button>{/if}
			{#if record.chat_id}<a class="or-button" href="/c/{encodeURIComponent(record.chat_id)}">Abrir conversación</a>{/if}
		</div>
		<div class="or-tabs" aria-label="Contenido del intercambio">
			{#each tabs as item}<button class:active={tab === item.id} aria-pressed={tab === item.id} on:click={() => tab = item.id}>{item.label}</button>{/each}
		</div>
		<JsonView value={displayed} label={tabs.find(item => item.id === tab)?.label ?? 'Contenido'} />
		<p class="or-muted or-footnote">El razonamiento mostrado es el que devolvió el proveedor. Los bloques cifrados o los resúmenes conservan su formato original.</p>
		<details class="or-metadata"><summary>Identificadores e integridad</summary><JsonView label="Metadatos" value={{ id: record.id, user_id: record.user_id, chat_id: record.chat_id, message_id: record.message_id, provider_id: record.provider_id, request_sha256: record.request_sha256, response_sha256: record.response_sha256, files: record.files }} /></details>
	{:else}<p class="or-empty">Selecciona un intercambio para revisar su entrada y salida.</p>{/if}
</section>
<style>
	.or-detail { min-width: 0; padding: 1.25rem; }
	.or-metadata { margin-top: 1rem; }
	summary { cursor: pointer; font-size: .8rem; margin-bottom: .8rem; }
</style>
