<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { getEffectivePolicy, type ParameterRule } from '$lib/apis/openrouter';
	import { readParameter, resetProviderOverrides, updateParameter } from './parameters';
	export let model = '';
	export let params: Record<string, any> = {};
	let mounted = false;
	let error = '';
	let rules: Record<string, ParameterRule> = {};
	let controller: AbortController | undefined;
	let loading = false;
	async function load(id: string) {
		controller?.abort();
		const current = new AbortController(); controller = current;
		loading = true; error = '';
		try { const policy = await getEffectivePolicy(id, '', current.signal); if (!current.signal.aborted) rules = policy.rules; }
		catch (failure) { if (!current.signal.aborted) error = String(failure); }
		finally { if (!current.signal.aborted) loading = false; }
	}
	const format = (value: unknown, rule: ParameterRule) => value === undefined ? '' : rule.type === 'string' ? String(value) : JSON.stringify(value);
	function change(path: string, raw: string, rule: ParameterRule) {
		try { params = updateParameter(params, path, raw, rule); error = ''; }
		catch { error = `${path}: introduce un valor JSON válido.`; }
	}
	$: fields = Object.entries(rules).filter(([path, rule]) => !path.startsWith('stream') && (rule.access === 'editable' || rule.value !== undefined));
	$: if (mounted && model) void load(model);
	onMount(() => { mounted = true; });
	onDestroy(() => controller?.abort());
</script>
<section class="parameter-editor" aria-label="Parámetros autorizados de OpenRouter">
	<div class="heading"><strong>OpenRouter</strong><a href="/openrouter?model={encodeURIComponent(model)}">Inspeccionar</a></div>
	<p>Los cambios se aplican a esta conversación. Un campo vacío omite tu valor.</p>
	{#if error}<p role="alert" class="error">{error}</p>{/if}
	{#if loading}<p role="status">Cargando permisos…</p>{/if}
	{#each fields as [path, rule] (path)}
		<label class="field"><span>{path}{rule.access !== 'editable' ? ' · fijado' : ''}</span>
			{#if rule.access !== 'editable'}<input readonly value={format(rule.value, rule)} aria-label={path} />
			{:else if rule.enum}<select aria-label={path} value={format(readParameter(params, path), rule)} on:change={(event) => change(path, event.currentTarget.value, rule)}><option value="">Sin valor propio</option>{#each rule.enum as value}<option value={format(value, rule)}>{format(value, rule)}</option>{/each}</select>
			{:else if rule.type === 'boolean'}<select aria-label={path} value={format(readParameter(params, path), rule)} on:change={(event) => change(path, event.currentTarget.value, rule)}><option value="">Sin valor propio</option><option value="true">true</option><option value="false">false</option></select>
			{:else if rule.type === 'number' || rule.type === 'integer'}<input aria-label={path} type="number" min={rule.minimum} max={rule.maximum} step={rule.type === 'integer' ? 1 : 'any'} value={format(readParameter(params, path), rule)} placeholder="Sin valor propio" on:change={(event) => change(path, event.currentTarget.value, rule)} />
			{:else}<textarea aria-label={path} rows="2" value={format(readParameter(params, path), rule)} placeholder={rule.type === 'string' ? 'Sin valor propio' : 'JSON; vacío para omitir'} on:change={(event) => change(path, event.currentTarget.value, rule)}></textarea>{/if}
		</label>
	{:else}{#if !loading}<p>El administrador no ha habilitado parámetros editables para este modelo.</p>{/if}{/each}
	<button type="button" class="reset" on:click={() => { params = resetProviderOverrides(params); error = ''; }}>Restablecer mis parámetros</button>
</section>
<style>
	.parameter-editor { margin: .75rem 0; padding: .8rem; border: 1px solid #a5824638; border-radius: 10px; font-size: .75rem; }
	.heading { display: flex; justify-content: space-between; gap: 1rem; }
	strong { font-weight: 500; }
	a, .reset { text-decoration: underline; text-underline-offset: 3px; }
	p { opacity: .65; margin: .6rem 0; line-height: 1.5; }
	.field { display: grid; gap: .3rem; margin: .7rem 0; }
	.field span { font-family: ui-monospace, Consolas, monospace; overflow-wrap: anywhere; font-size: .7rem; }
	input, select, textarea { width: 100%; background: transparent; border: 1px solid #8885; border-radius: 6px; padding: .4rem .5rem; }
	input[readonly] { opacity: .6; }
	.reset { margin-top: .5rem; font-size: .7rem; }
	.error { color: #c24732; opacity: 1; }
</style>
