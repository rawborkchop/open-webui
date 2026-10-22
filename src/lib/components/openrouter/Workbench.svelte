<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { models } from '$lib/stores';
	import Catalog from './Catalog.svelte';
	import PolicyEditor from './PolicyEditor.svelte';
	import ExchangeList from './ExchangeList.svelte';
	import ExchangeDetail from './ExchangeDetail.svelte';
	export let admin = false;
	let model = '';
	let modelDraft = '';
	let tab = 'exchanges';
	let selectedId = '';
	let chatId = '';
	onMount(() => {
		model = $page.url.searchParams.get('model') ?? '';
		modelDraft = model;
		chatId = $page.url.searchParams.get('chat_id') ?? '';
		selectedId = $page.url.searchParams.get('exchange_id') ?? '';
	});
</script>
<div class="or-workbench">
	<header class="or-header"><div><div class="or-eyebrow"><span class="or-dot"></span> OPENROUTER / {admin ? 'ADMINISTRACIÓN' : 'MI ACTIVIDAD'}</div><h1>{admin ? 'Control de inferencia' : 'Tus intercambios'}</h1><p>{admin ? 'Políticas, entradas y respuestas de todos los usuarios.' : 'Revisa tus conversaciones y los parámetros que puedes modificar.'}</p></div><a class="or-button" href="/">Volver al chat ↗</a></header>
	<div class="or-context"><form on:submit|preventDefault={() => { model = modelDraft; }}><label for="or-model">Modelo</label><input id="or-model" class="or-input" bind:value={modelDraft} list="or-models" placeholder="Todos los modelos / ID de modelo" /><datalist id="or-models">{#each $models as item}<option value={item.id}></option>{/each}</datalist><button class="or-button" type="submit">Aplicar</button></form>{#if chatId}<span class="or-muted">Conversación {chatId}<button class="or-button" on:click={() => chatId = ''}>Quitar filtro</button></span>{/if}</div>
	<nav class="or-tabs or-main-tabs" aria-label="Secciones de OpenRouter">
		<button class:active={tab === 'exchanges'} aria-pressed={tab === 'exchanges'} on:click={() => tab = 'exchanges'}><span>01</span> Intercambios</button>
		<button class:active={tab === 'catalog'} aria-pressed={tab === 'catalog'} on:click={() => tab = 'catalog'}><span>02</span> Parámetros</button>
		{#if admin}<button class:active={tab === 'policies'} aria-pressed={tab === 'policies'} on:click={() => tab = 'policies'}><span>03</span> Políticas y permisos</button>{/if}
	</nav>
	<div class="or-content">
		{#if tab === 'exchanges'}<div class="or-exchange-layout"><div class="or-list-pane">{#key `${model}:${chatId}`}<ExchangeList {admin} {model} {chatId} {selectedId} onselect={(id) => selectedId = id} />{/key}</div><ExchangeDetail exchangeId={selectedId} {admin} /></div>
		{:else if tab === 'catalog'}<Catalog {model} />
		{:else if admin}<PolicyEditor {model} />{/if}
	</div>
</div>
<style>
	.or-workbench { --or-background: #fff; --or-border: #e5e5e2; --or-muted: #73736d; --or-accent: #aa772c; --or-hover: #a77b3610; color: inherit; background: var(--or-background); max-width: 1600px; margin: 0 auto; padding: 1.5rem 1.4rem 3rem; min-height: 100%; }
	:global(.dark) .or-workbench { --or-background: #171717; --or-border: #ffffff17; --or-muted: #a3a39a; --or-accent: #e0b66e; --or-hover: #b28d4411; }
	.or-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: .5rem 0 1.75rem; }
	h1 { font-size: clamp(1.5rem, 2.6vw, 2.3rem); font-weight: 500; letter-spacing: -.045em; margin: .65rem 0 .5rem; }
	.or-header p { font-size: .85rem; color: var(--or-muted); line-height: 1.6; }
	.or-dot { display: inline-block; width: .45rem; height: .45rem; border-radius: 50%; background: var(--or-accent); margin-right: .4rem; }
	.or-context { border-top: 1px solid var(--or-border); padding: 1rem 0; display: flex; flex-wrap: wrap; justify-content: space-between; gap: .7rem; }
	form { display: flex; align-items: center; gap: .7rem; flex: 1; }
	form label { font-size: .75rem; color: var(--or-muted); }
	form input { max-width: 27rem; }
	.or-content { border: 1px solid var(--or-border); border-radius: 0 0 12px 12px; }
	.or-exchange-layout { display: grid; grid-template-columns: minmax(280px, 34%) minmax(0, 1fr); min-height: 30rem; }
	.or-list-pane { border-right: 1px solid var(--or-border); }
	:global(.or-workbench .or-eyebrow) { font: .65rem/1.4 ui-monospace, SFMono-Regular, Consolas, monospace; color: var(--or-muted); letter-spacing: .1em; }
	:global(.or-workbench .or-section-heading) { display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin-bottom: .65rem; flex-wrap: wrap; }
	:global(.or-workbench h2) { font-size: 1.1rem; letter-spacing: -.02em; font-weight: 500; margin-top: .3rem; overflow-wrap: anywhere; }
	:global(.or-workbench .or-muted) { color: var(--or-muted); font-size: .77rem; line-height: 1.6; }
	:global(.or-workbench .or-button) { display: inline-flex; align-items: center; justify-content: center; gap: .4rem; border: 1px solid var(--or-border); border-radius: 7px; padding: .48rem .75rem; font-size: .73rem; cursor: pointer; white-space: nowrap; }
	:global(.or-workbench .or-button:hover) { background: var(--or-hover); }
	:global(.or-workbench .or-button:disabled) { cursor: default; opacity: .4; }
	:global(.or-workbench .or-primary) { background: var(--or-accent); color: #17130c; border-color: transparent; }
	:global(.or-workbench .or-input) { width: 100%; min-width: 0; padding: .5rem .65rem; border: 1px solid var(--or-border); border-radius: 6px; background: transparent; font-size: .75rem; }
	:global(.or-workbench .or-input:focus) { outline: 2px solid var(--or-accent); outline-offset: 2px; }
	:global(.or-workbench .or-state) { font: .64rem/1.4 ui-monospace, Consolas, monospace; border: 1px solid var(--or-border); border-radius: 4px; padding: .2rem .4rem; white-space: nowrap; }
	:global(.or-workbench .or-state[data-state='completed']) { color: #51826c; }
	:global(.or-workbench .or-state[data-state='error']), :global(.or-workbench .or-state[data-state='incomplete']) { color: #c57f52; }
	:global(.or-workbench .or-toolbar) { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem; margin: .9rem 0; }
	:global(.or-workbench .or-tabs) { display: flex; flex-wrap: wrap; gap: .2rem; margin: 1rem 0 .85rem; }
	:global(.or-workbench .or-tabs button) { padding: .65rem .85rem; border-bottom: 2px solid transparent; color: var(--or-muted); font-size: .78rem; }
	:global(.or-workbench .or-tabs button.active) { border-color: var(--or-accent); color: inherit; }
	:global(.or-workbench .or-tabs span) { font: .65rem ui-monospace, Consolas, monospace; margin-right: .4rem; opacity: .65; }
	.or-main-tabs { margin-bottom: 0 !important; }
	:global(.or-workbench .or-empty) { padding: 2rem .5rem; color: var(--or-muted); font-size: .8rem; line-height: 1.7; }
	:global(.or-workbench .or-error) { color: #c5523a; font-size: .8rem; padding: .75rem 0; overflow-wrap: anywhere; }
	:global(.or-workbench .or-success) { color: #51826c; font-size: .8rem; padding: .75rem 0; }
	:global(.or-workbench .or-notice) { background: var(--or-hover); border-left: 2px solid var(--or-accent); padding: .7rem .9rem; font-size: .75rem; line-height: 1.65; margin: .9rem 0; }
	:global(.or-workbench .or-footnote) { margin-top: 1rem; font-size: .7rem; }
	:global(.or-workbench .or-table-wrap) { overflow-x: auto; margin-top: 1.2rem; }
	:global(.or-workbench table) { width: 100%; text-align: left; border-collapse: collapse; font-size: .78rem; }
	:global(.or-workbench th) { font-weight: 400; color: var(--or-muted); font-size: .68rem; padding: .7rem .65rem; border-bottom: 1px solid var(--or-border); }
	:global(.or-workbench td) { vertical-align: top; padding: .9rem .65rem; border-bottom: 1px solid var(--or-border); }
	:global(.or-workbench code) { font: .73rem ui-monospace, Consolas, monospace; }
	@media (max-width: 900px) { .or-exchange-layout { grid-template-columns: minmax(0, 1fr); } .or-list-pane { border-right: 0; border-bottom: 1px solid var(--or-border); } }
	@media (max-width: 600px) { .or-workbench { padding: 1rem .6rem 2rem; } .or-header { align-items: start; flex-direction: column; } form { flex-wrap: wrap; } }
</style>
