<script lang="ts">
	import { onMount } from 'svelte';
	import { getPolicies, savePolicy, getCatalog, getPolicyHistory, getEffectivePolicy, type Policy, type ParameterRule, type CatalogEntry, type EffectivePolicy } from '$lib/apis/openrouter';
	import JsonView from './JsonView.svelte';
	export let model = '';
	let policies: Policy[] = [];
	let catalog: CatalogEntry[] = [];
	let scope: Policy['scope'] = 'global';
	let target = '*';
	let rules: Record<string, ParameterRule> = {};
	let version = 0;
	let valueText: Record<string, string> = {};
	let enumText: Record<string, string> = {};
	let search = '';
	let customPath = '';
	let error = '';
	let notice = '';
	let busy = false;
	let previewUser = '';
	let preview: EffectivePolicy | null = null;
	let history: Awaited<ReturnType<typeof getPolicyHistory>> = [];
	const accessLabels = { editable: 'Editable', read_only: 'Solo lectura', hidden: 'Oculto', server_only: 'Servidor' };
	function choose() {
		const found = policies.find(policy => policy.scope === scope && policy.target === target);
		rules = structuredClone(found?.rules ?? {}); version = found?.version ?? 0;
		valueText = Object.fromEntries(Object.entries(rules).map(([path, rule]) => [path, 'value' in rule ? JSON.stringify(rule.value) : '']));
		enumText = Object.fromEntries(Object.entries(rules).map(([path, rule]) => [path, rule.enum ? JSON.stringify(rule.enum) : '']));
		history = []; preview = null; notice = ''; error = '';
	}
	function changeScope(value: Policy['scope']) { scope = value; target = value === 'global' ? '*' : value === 'model' ? model : ''; choose(); }
	function access(path: string, value: string) {
		const next = { ...rules };
		if (value === 'inherit') delete next[path];
		else next[path] = { type: catalog.find(item => item.path === path)?.type ?? 'any', ...next[path], access: value as ParameterRule['access'] };
		rules = next;
	}
	function bound(path: string, key: 'minimum' | 'maximum', value: string) {
		const rule = { ...rules[path] };
		if (value === '') delete rule[key]; else rule[key] = Number(value);
		rules = { ...rules, [path]: rule };
	}
	async function save() {
		busy = true; error = ''; notice = '';
		try {
			const next = structuredClone(rules);
			for (const [path, rule] of Object.entries(next)) {
				if (valueText[path]?.trim()) rule.value = JSON.parse(valueText[path]); else delete rule.value;
				if (enumText[path]?.trim()) rule.enum = JSON.parse(enumText[path]); else delete rule.enum;
			}
			const result = await savePolicy({ scope, target, version, rules: next });
			policies = [...policies.filter(policy => !(policy.scope === scope && policy.target === target)), result];
			choose(); notice = `Política guardada · versión ${result.version}`;
		} catch (failure) { error = String(failure); }
		finally { busy = false; }
	}
	async function reload() {
		busy = true; error = '';
		try { const data = await Promise.all([getPolicies(), getCatalog(model)]); policies = data[0]; catalog = data[1].items; choose(); }
		catch (failure) { error = String(failure); }
		finally { busy = false; }
	}
	async function loadHistory() {
		try { history = await getPolicyHistory(scope, target); } catch (failure) { error = String(failure); }
	}
	async function previewPolicy() {
		try { preview = await getEffectivePolicy(model, previewUser); } catch (failure) { error = String(failure); }
	}
	function addPath() {
		if (!/^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$/.test(customPath)) { error = 'Introduce una ruta JSON válida.'; return; }
		rules = { ...rules, [customPath]: { access: 'read_only', type: 'any' } }; customPath = '';
	}
	$: paths = Array.from(new Set([...catalog.map(item => item.path), ...Object.keys(rules)])).filter(path => path.toLowerCase().includes(search.toLowerCase())).sort();
	onMount(() => { void reload(); });
</script>
<section class="or-policy">
	<div class="or-section-heading"><div><span class="or-eyebrow">GOBIERNO DE PARÁMETROS</span><h2>Permisos y valores</h2></div><span class="or-state">Versión {version}</span></div>
	<p class="or-muted">La política global establece el máximo permitido. Modelo, grupo y usuario solo pueden restringirlo. Los cambios se verifican en el servidor.</p>
	<div class="policy-scope">
		<label>Ámbito<select class="or-input" value={scope} on:change={event => changeScope(event.currentTarget.value as Policy['scope'])}><option value="global">Global</option><option value="model">Modelo</option><option value="group">Grupo</option><option value="user">Usuario</option></select></label>
		<label>{scope === 'global' ? 'Toda la instancia' : `ID de ${scope === 'user' ? 'usuario' : scope === 'group' ? 'grupo' : 'modelo'}`}<input class="or-input" bind:value={target} disabled={scope === 'global'} on:change={choose} placeholder={scope === 'model' ? 'proveedor/modelo' : 'Identificador'} list="openrouter-policy-targets" /></label>
		<datalist id="openrouter-policy-targets">{#each policies.filter(policy => policy.scope === scope) as policy}<option value={policy.target}></option>{/each}</datalist>
		<button class="or-button" on:click={choose}>Cargar ámbito</button>
		<button class="or-button" on:click={reload} disabled={busy}>Recargar políticas</button>
	</div>
	<p class="or-notice">Un valor en «Editable» actúa como valor por defecto. En los demás modos se fija en el servidor. Dejarlo vacío conserva la ausencia del parámetro.</p>
	{#if error}<p class="or-error" role="alert">{error}</p>{/if}
	{#if notice}<p class="or-success" role="status">{notice}</p>{/if}
	<div class="or-toolbar"><input class="or-input" aria-label="Buscar regla" bind:value={search} placeholder="Buscar regla…" /><input class="or-input" aria-label="Nueva ruta de parámetro" bind:value={customPath} placeholder="Nueva ruta, p. ej. provider.max_price.prompt" /><button class="or-button" on:click={addPath}>Añadir campo</button></div>
	<div class="or-table-wrap"><table><thead><tr><th>Parámetro</th><th>Acceso</th><th>Tipo y límites</th><th>Valor JSON</th></tr></thead><tbody>
		{#each paths as path (path)}
			<tr>
				<td><code>{path}</code></td>
				<td><select class="or-input" aria-label={`Acceso ${path}`} value={rules[path]?.access ?? 'inherit'} on:change={event => access(path, event.currentTarget.value)}><option value="inherit">{scope === 'global' ? 'Sin permiso' : 'Heredar'}</option>{#each Object.entries(accessLabels) as [value, label]}<option {value}>{label}</option>{/each}</select></td>
				<td>{#if rules[path]}<select class="or-input" aria-label={`Tipo ${path}`} bind:value={rules[path].type}>{#each ['any', 'number', 'integer', 'string', 'boolean', 'object', 'array'] as kind}<option value={kind}>{kind}</option>{/each}</select><details><summary>Límites / opciones</summary><label>Mínimo<input class="or-input" type="number" step="any" value={rules[path].minimum ?? ''} on:change={event => bound(path, 'minimum', event.currentTarget.value)} /></label><label>Máximo<input class="or-input" type="number" step="any" value={rules[path].maximum ?? ''} on:change={event => bound(path, 'maximum', event.currentTarget.value)} /></label><label>Opciones (array JSON)<textarea class="or-input" rows="2" bind:value={enumText[path]} placeholder='["low", "high"]'></textarea></label></details>{:else}<span class="or-muted">Heredado</span>{/if}</td>
				<td><textarea class="or-input rule-value" aria-label={`Valor JSON ${path}`} rows="2" disabled={!rules[path]} bind:value={valueText[path]} placeholder="Sin valor fijado"></textarea></td>
			</tr>
		{/each}
	</tbody></table></div>
	<div class="or-toolbar policy-actions"><button class="or-button or-primary" disabled={busy || !target} on:click={save}>{busy ? 'Guardando…' : 'Guardar política'}</button><button class="or-button" on:click={loadHistory}>Ver historial</button></div>
	{#if history.length}<details open><summary>Historial de cambios</summary>{#each history as revision}<details class="revision"><summary>v{revision.version} · {new Date(revision.created_at).toLocaleString()} · {revision.actor_id}</summary><JsonView value={revision.rules} label={`Reglas v${revision.version}`} /></details>{/each}</details>{/if}
	<div class="policy-preview"><h3>Previsualizar permisos efectivos</h3><p class="or-muted">Se usa el modelo seleccionado arriba y las políticas guardadas.</p><div class="or-toolbar"><input class="or-input" aria-label="ID de usuario para previsualizar" bind:value={previewUser} placeholder="ID de usuario; vacío para tu cuenta" /><button class="or-button" on:click={previewPolicy}>Previsualizar</button></div>{#if preview}<JsonView value={preview} label="Permisos efectivos" />{/if}</div>
</section>
<style>
	.or-policy { padding: 1.25rem; }
	.policy-scope { display: flex; flex-wrap: wrap; align-items: end; gap: .75rem; margin: 1.2rem 0; }
	label { display: grid; gap: .3rem; font-size: .72rem; color: var(--or-muted); }
	.policy-scope label:nth-child(2) { flex: 1; min-width: 12rem; }
	.or-toolbar > input { max-width: 24rem; }
	.rule-value { min-width: 13rem; font-family: ui-monospace, Consolas, monospace; }
	details { margin-top: .6rem; }
	summary { cursor: pointer; font-size: .75rem; margin-bottom: .6rem; }
	td details label { margin-top: .5rem; }
	.policy-actions { position: sticky; bottom: 0; padding: .85rem 0; background: var(--or-background); border-top: 1px solid var(--or-border); }
	.policy-preview { border-top: 1px solid var(--or-border); padding-top: 1.3rem; margin-top: 1.3rem; }
	h3 { font-weight: 500; font-size: .95rem; }
	.revision { padding: .5rem 0; }
</style>
