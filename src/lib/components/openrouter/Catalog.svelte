<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { getCatalog, getEffectivePolicy, type CatalogEntry, type ParameterRule } from '$lib/apis/openrouter';
	export let model = '';
	let mounted = false;
	let entries: CatalogEntry[] = [];
	let rules: Record<string, ParameterRule> = {};
	let search = '';
	let error = '';
	let version = '';
	let controller: AbortController | undefined;
	const labels: Record<string, string> = { editable: 'Editable', read_only: 'Solo lectura', hidden: 'Oculto', server_only: 'Servidor' };
	async function load(id: string) {
		controller?.abort();
		const current = new AbortController(); controller = current;
		error = '';
		try {
			const [catalog, effective] = await Promise.all([getCatalog(id, current.signal), getEffectivePolicy(id, '', current.signal)]);
			if (!current.signal.aborted) { entries = catalog.items; rules = effective.rules; version = catalog.version; }
		} catch (failure) { if (!current.signal.aborted) error = String(failure); }
	}
	$: filtered = entries.filter(item => `${item.path} ${item.category} ${item.description}`.toLowerCase().includes(search.toLowerCase()));
	$: if (mounted) void load(model);
	onMount(() => { mounted = true; });
	onDestroy(() => controller?.abort());
</script>
<section class="or-catalog">
	<div class="or-section-heading"><div><span class="or-eyebrow">CATÁLOGO · {version}</span><h2>Parámetros de entrada</h2></div><input class="or-input" aria-label="Buscar parámetro" bind:value={search} placeholder="Buscar parámetro…" /></div>
	<p class="or-muted">Revisa los campos y tus permisos efectivos. Los parámetros autorizados se editan en los Controles de cada conversación.</p>
	{#if error}<p class="or-error" role="alert">{error}</p>{/if}
	<div class="or-table-wrap"><table><thead><tr><th>Parámetro</th><th>Permiso</th><th>Tipo / límites</th><th>Compatibilidad</th></tr></thead><tbody>
		{#each filtered as item (item.path)}
			<tr><td><code>{item.path}</code><p>{item.description}</p></td><td><span class="or-state">{labels[rules[item.path]?.access ?? 'read_only']}</span></td><td>{item.type}{#if rules[item.path]?.minimum !== undefined || rules[item.path]?.maximum !== undefined}<small>{rules[item.path]?.minimum ?? '−∞'} … {rules[item.path]?.maximum ?? '∞'}</small>{/if}</td><td>{item.supported === null ? 'Sin confirmar' : item.supported ? 'Declarada' : 'No declarada'}</td></tr>
		{/each}
	</tbody></table></div>
	<p class="or-muted or-footnote">La compatibilidad procede de los metadatos del modelo cargado. Los campos adicionales se muestran en el inspector del intercambio y se pueden añadir a las políticas por su ruta JSON. El cuerpo incluye también el modelo y los mensajes o input.</p>
</section>
<style>
	.or-catalog { padding: 1.25rem; }
	.or-section-heading input { max-width: 19rem; }
	small { display: block; margin-top: .3rem; color: var(--or-muted); }
	td p { margin-top: .3rem; font-size: .73rem; color: var(--or-muted); max-width: 38rem; line-height: 1.5; }
</style>
