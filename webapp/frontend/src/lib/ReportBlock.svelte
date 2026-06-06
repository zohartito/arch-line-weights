<script lang="ts">
  export let title: string;
  export let items: string[] = [];
  export let empty: string;
  export let compact = false;
</script>

<section class={compact ? 'space-y-1' : 'space-y-2'}>
  <h3 class={compact ? 'text-xs font-semibold uppercase tracking-wide text-ink-500' : 'text-sm font-semibold text-ink-900'}>
    {title}
  </h3>
  {#if items.length > 0}
    <ul class={compact ? 'space-y-1 text-xs text-ink-700' : 'space-y-1 text-sm text-ink-700'}>
      {#each items as item}
        <li>{item}</li>
      {/each}
    </ul>
  {:else}
    <p class={compact ? 'text-xs text-ink-500' : 'text-sm text-ink-500'}>{empty}</p>
  {/if}
</section>
