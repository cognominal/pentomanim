<script lang="ts">
  import { onMount } from 'svelte';
  import '../app.css';
  import { injectAnalytics } from '@vercel/analytics/sveltekit';

  let { children } = $props();

  onMount(() => {
    injectAnalytics();
  });
</script>

{@render children()}
