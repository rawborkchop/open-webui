<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { getExchanges, type ExchangeSummary } from '$lib/apis/openrouter';
	export let admin = false;
	export let model = '';
	export let chatId = '';
	export let selectedId = '';
	export let onselect: (id: string) => void = () => {};
	let items: ExchangeSummary[] = [];
	let owner = '';
	let state = '';
	let providerId = '';
	let after = '';
	let before = '';
	let offset = 0;
	let total = 0;
	let loading = false;
	let error = '';
	let controller: AbortController | undefined;
	const limit = 20;
	async function load(nextOffset = 0) {
		controller?.abort();
		const current = new AbortController(); controller = current;
		loading = true; error = ''; offset = nextOffset;
		const query = new URLSearchParams({ limit: String(limit), offset: String(offset) });
		for (const [key, value] of Object.entries({ owner: admin ? owner : '', state, model, chat_id: chatId, provider_id: providerId })) if (value) query.set(key, value);
		if (after) query.set('after', String(new Date(after).getTime()));
		if (before) query.set('before', String(new Date(before).getTime()));
		try { const data = await getExchanges(query, current.signal); if (!current.signal.aborted) { items = data.items; total = data.total; } }
		catch (failure) { if (!current.signal.aborted) error = String(failure); }
		finally { if (!current.signal.aborted) loading = false; }
	}
	onMount(() => { void load(); });
	onDestroy(() => controller?.abort());
</script>
<section class="or-exchanges" aria-label="Intercambios guardados">
	<form class="or-filters" on:submit|preventDefault={() => load()}>
		{#if admin}<label>Usuario<input class="or-input" bind:value={owner} placeholder="ID de usuario" /></label>{/if}
		<label>Estado<select class="or-input" bind:value={state}><option value="">Todos</option>{#each ['completed', 'recording', 'incomplete', 'cancelled', 'error'] as value}<option value={value}>{value}</option>{/each}</select></label>
		<label>Generación<input class="or-input" bind:value={providerId} placeholder="ID de OpenRouter" /></label>
		<label>Desde<input class="or-input" type="datetime-local" bind:value={after} /></label>
		<label>Hasta<input class="or-input" type="datetime-local" bind:value={before} /></label>
		<button class="or-button or-primary" disabled={loading} type="submit">{loading ? 'Cargando…' : 'Filtrar / actualizar'}</button>
	</form>
	{#if error}<p class="or-error" role="alert">{error}</p>{/if}
	<p class="or-count" aria-live="polite">{total.toLocaleString()} intercambios · {admin ? 'todos los usuarios' : 'solo tus datos'}</p>
	<div class="or-exchange-items" aria-busy={loading}>
		{#each items as item (item.id)}
			<button class="or-exchange" class:selected={selectedId === item.id} on:click={() => onselect(item.id)}>
				<div><strong>{item.model}</strong><span class="or-state" data-state={item.state}>{item.state}</span></div>
				<p>{new Date(item.created_at).toLocaleString()} · {item.purpose}</p>
				<small>{admin ? `${item.user_id} · ` : ''}{item.byte_count.toLocaleString()} bytes · {item.id.slice(0, 8)}</small>
			</button>
		{:else}<p class="or-empty">{loading ? 'Cargando intercambios…' : 'No hay intercambios para estos filtros. Las nuevas llamadas a OpenRouter aparecerán aquí.'}</p>{/each}
	</div>
	<div class="or-pagination"><button class="or-button" disabled={offset === 0 || loading} on:click={() => load(Math.max(0, offset - limit))}>Anterior</button><span>{total ? offset + 1 : 0}–{Math.min(offset + limit, total)} / {total}</span><button class="or-button" disabled={offset + limit >= total || loading} on:click={() => load(offset + limit)}>Siguiente</button></div>
</section>
<style>
	.or-exchanges { min-width: 0; padding: 1.25rem; }
	.or-filters { display: grid; gap: .6rem; grid-template-columns: repeat(2, minmax(0, 1fr)); }
	label { font-size: .72rem; color: var(--or-muted); display: grid; gap: .3rem; }
	.or-filters button { grid-column: 1 / -1; }
	.or-count { margin: 1.2rem 0 .6rem; font-size: .72rem; color: var(--or-muted); }
	.or-exchange { text-align: left; width: 100%; border-top: 1px solid var(--or-border); padding: .9rem .2rem; }
	.or-exchange:hover, .or-exchange.selected { background: var(--or-hover); }
	.or-exchange.selected { border-left: 3px solid var(--or-accent); padding-left: .6rem; }
	.or-exchange > div { display: flex; align-items: center; justify-content: space-between; gap: .5rem; }
	strong { font-size: .8rem; font-weight: 500; overflow-wrap: anywhere; }
	.or-exchange p, small { font-size: .7rem; color: var(--or-muted); margin-top: .35rem; overflow-wrap: anywhere; }
	.or-pagination { display: flex; align-items: center; justify-content: space-between; gap: .5rem; margin-top: 1rem; font-size: .7rem; }
</style>
