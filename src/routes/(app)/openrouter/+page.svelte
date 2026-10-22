<script lang="ts">
	import Workbench from '$lib/components/openrouter/Workbench.svelte';
	import { user } from '$lib/stores';
</script>
<Workbench admin={$user?.role === 'admin'} />
