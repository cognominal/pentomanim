<script lang="ts">
  import { goto } from '$app/navigation';
  import App from '../../App.svelte';

  type Pane = 'rectangle' | 'triplication' | 'cuboid';

  type Props = {
    pane: Pane;
  };

  const pathByPane: Record<Pane, string> = {
    rectangle: '/',
    triplication: '/triplication-solver',
    cuboid: '/cuboid-solver',
  };

  let { pane }: Props = $props();

  function onpanechange(nextPane: Pane): void {
    void goto(pathByPane[nextPane]);
  }
</script>

<App initialPane={pane} {onpanechange} />
