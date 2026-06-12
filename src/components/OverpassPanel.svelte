<script lang="ts">
  import type { OverpassElement, OverpassSnapshot } from "../types";

  let {
    title,
    query,
    emptyText,
    firstTag,
    sampleLimit = 100,
    endpoint = "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
  }: {
    title: string;
    query: string;
    emptyText: string;
    firstTag?: string;
    sampleLimit?: number;
    endpoint?: string;
  } = $props();

  let snapshot = $state<OverpassSnapshot | null>(null);
  let loading = $state(false);
  let sampleIsCapped = $derived(
    Boolean(snapshot && snapshot.elements.length >= sampleLimit),
  );
  let countText = $derived.by(() => {
    if (!snapshot) return "[done]";
    if (snapshot.error || snapshot.remark) return "[error]";
    const suffix = sampleIsCapped ? "+" : "";
    return `[${snapshot.elements.length.toLocaleString()}${suffix}]`;
  });
  let renderedElements = $derived(
    snapshot?.elements.slice(0, sampleLimit) ?? [],
  );

  function osmUrl(e: OverpassElement): string {
    return `https://www.openstreetmap.org/${e.type}/${e.id}`;
  }
  function idUrl(e: OverpassElement): string {
    return `https://www.openstreetmap.org/edit?editor=id&${e.type}=${e.id}`;
  }
  function latLon(e: OverpassElement): string {
    const lat = e.lat ?? e.center?.lat;
    const lon = e.lon ?? e.center?.lon;
    if (lat === undefined || lon === undefined) return "no center returned";
    return `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
  }
  function fmtTags(t: Record<string, string> | undefined): string {
    if (!t) return "no tags";
    const entries = Object.entries(t);
    const first = firstTag ? entries.find(([k]) => k === firstTag) : undefined;
    const ordered = first
      ? [first, ...entries.filter(([k]) => k !== firstTag)]
      : entries;
    return ordered
      .slice(0, 6)
      .map(([k, v]) => `${k}=${v}`)
      .join(" · ");
  }

  async function run() {
    loading = true;
    const ctrl = new AbortController();
    const tid = window.setTimeout(() => ctrl.abort(), 420_000);
    try {
      const r = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        },
        body: `data=${encodeURIComponent(query)}`,
        signal: ctrl.signal,
      });
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      const data = (await r.json()) as {
        elements?: OverpassElement[];
        remark?: string;
      };
      snapshot = {
        elements: data.elements ?? [],
        fetchedAt: new Date().toLocaleString(),
        remark: data.remark,
      };
    } catch (e) {
      snapshot = {
        elements: [],
        fetchedAt: new Date().toLocaleString(),
        error: e instanceof Error ? e.message : String(e),
      };
    } finally {
      window.clearTimeout(tid);
      loading = false;
    }
  }
</script>

<div class="panel">
  <div class="bar">
    <span class="dim">└─</span> <strong>{title}</strong>
    {#if snapshot}
      <span class="count">{countText}</span>
    {:else}
      <button onclick={run} disabled={loading}
        >{loading ? "..." : "[run]"}</button
      >
    {/if}
  </div>
  {#if snapshot?.error}
    <div class="err">✕ {snapshot.error}</div>
  {:else if snapshot?.remark}
    <div class="err">✕ {snapshot.remark}</div>
  {:else if snapshot && !snapshot.elements.length}
    <div class="dim empty">{emptyText}</div>
  {:else if snapshot}
    <div class="list">
      {#each renderedElements as e (`${e.type}/${e.id}`)}
        <div class="row">
          <a href={osmUrl(e)} target="_blank" rel="noreferrer" class="id"
            ><strong>{e.type[0]}/{e.id}</strong></a
          >
          <a href={idUrl(e)} target="_blank" rel="noreferrer" class="act">iD</a>
          <span class="tags">{fmtTags(e.tags)}</span>
          <span class="loc">{latLon(e)}</span>
        </div>
      {/each}
      {#if sampleIsCapped}
        <div class="truncated">
          Showing first {renderedElements.length.toLocaleString()} matching results; more may exist.
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .panel {
    margin-top: 6px;
    padding: 6px 0;
    min-width: 0;
  }
  .bar {
    display: flex;
    gap: 6px;
    align-items: center;
    font-size: 12px;
    margin-bottom: 4px;
  }
  .bar button {
    padding: 0;
    border: 0;
    background: transparent;
    color: var(--fg-muted);
    font-size: 11px;
    cursor: pointer;
  }
  .bar button:hover {
    color: var(--fg);
  }
  .bar button:disabled {
    opacity: 0.5;
  }
  .count {
    color: var(--fg-muted);
    font-size: 11px;
  }
  .err {
    color: var(--red);
    font-size: 11px;
    margin-bottom: 2px;
  }
  .empty {
    font-size: 11px;
    padding: 4px 0;
  }
  .list {
    max-width: 100%;
    max-height: 300px;
    overflow: auto;
    border: 1px solid var(--border);
    border-radius: 4px;
    font-size: 11px;
  }
  .row {
    display: flex;
    gap: 8px;
    align-items: baseline;
    min-width: 0;
    padding: 3px 8px;
    border-bottom: 1px solid var(--border);
  }
  .row:last-child {
    border-bottom: 0;
  }
  .row:hover {
    background: var(--bg-hover);
  }
  .truncated {
    color: var(--fg-muted);
    padding: 5px 8px;
  }
  .id {
    color: var(--blue);
    white-space: nowrap;
    min-width: 65px;
    flex-shrink: 0;
  }
  .tags {
    color: var(--fg);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    min-width: 0;
  }
  .loc {
    color: var(--fg-dim);
    white-space: nowrap;
    font-size: 10px;
    flex-shrink: 0;
  }
  .act {
    color: var(--fg-muted);
    font-size: 10px;
    flex-shrink: 0;
  }
  .dim {
    color: var(--fg-dim);
  }
</style>
