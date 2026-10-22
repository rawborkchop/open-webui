<script lang="ts">
	export let value: unknown;
	export let label = 'JSON';
	let copied = false;
	let copyError = '';
	$: content = JSON.stringify(value ?? null, null, 2);
	async function copy() {
		try { await navigator.clipboard.writeText(content); copied = true; }
		catch { copyError = 'No se pudo copiar al portapapeles.'; }
	}
</script>
<div class="or-json">
	<div class="or-json-toolbar"><span>{label}</span><button type="button" on:click={copy}>{copied ? 'Copiado' : 'Copiar JSON'}</button></div>
	{#if copyError}<p role="alert">{copyError}</p>{/if}
	<textarea readonly aria-label={label} value={content} rows="16"></textarea>
</div>
<style>
	.or-json { border: 1px solid var(--or-border, #8883); border-radius: 10px; overflow: hidden; }
	.or-json-toolbar { display: flex; justify-content: space-between; align-items: center; padding: .65rem .85rem; font-size: .75rem; border-bottom: 1px solid var(--or-border, #8883); }
	button { text-decoration: underline; text-underline-offset: 3px; }
	textarea { display: block; width: 100%; resize: vertical; padding: 1rem; overflow: auto; max-height: 65vh; font: .75rem/1.65 ui-monospace, SFMono-Regular, Consolas, monospace; white-space: pre-wrap; overflow-wrap: anywhere; background: #88888806; }
</style>
