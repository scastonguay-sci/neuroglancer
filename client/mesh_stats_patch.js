(() => {
  const BASE = location.hostname.endsWith("github.io") ? "/neuroglancer/client" : ".";
  const STATS_BASE = `${BASE}/stats`;
  const BUST = "v4-" + Date.now();

  function toSidString(id) {
    if (typeof id === "string") return id.replace(/^!/, "");
    if (typeof id === "number" || typeof id === "bigint") return String(id);
    const any = id && typeof id === "object" ? id : null;
    if (any) {
      const lo = any.low ?? any.lo ?? any[0];
      const hi = any.high ?? any.hi ?? any[1];
      if (lo !== undefined && hi !== undefined) {
        try {
          const loU32 = BigInt(lo) & 0xffffffffn;
          const hiU32 = BigInt(hi) & 0xffffffffn;
          return ((hiU32 << 32n) | loU32).toString();
        } catch {}
      }
      if (typeof any.toString === "function") {
        return String(any.toString()).replace(/n$/, "");
      }
    }
    return String(id);
  }

  // Cache shard arrays (but still force no-store fetch once per page load)
  const shardCache = new Map();
  async function fetchShardRows(prefix3) {
    const url = `${STATS_BASE}/${prefix3}.json?bust=${BUST}`;
    if (!shardCache.has(url)) {
      shardCache.set(url, (async () => {
        const r = await fetch(url, { cache: "no-store" });
        if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
        const data = await r.json();
        return Array.isArray(data) ? data : [];
      })());
    }
    return shardCache.get(url);
  }

  // Public helper you can test in DevTools
  window.getStatsForSid = async function getStatsForSid(sidInput) {
    const sid = toSidString(sidInput);
    if (!/^\d{3,}$/.test(sid)) return null;
    const rows = await fetchShardRows(sid.slice(0,3));
    return rows.find(r => String(r.sid) === sid) || null;
  };

  // 1) Try to patch the function the built UI panel uses (when present)
  function tryHookFetchRow() {
    const g = window;
    const current = g.fetchRowForSid || (g.mesh_stats_client && g.mesh_stats_client.fetchRowForSid);
    if (!current) return false;

    const patched = async function patchedFetchRowForSid(sidInput) {
      const sid = toSidString(sidInput);
      if (!/^\d{3,}$/.test(sid)) return null;
      try {
        const rows = await fetchShardRows(sid.slice(0,3));
        return rows.find(r => String(r.sid) === sid) || null;
      } catch {
        return null;
      }
    };
    if (g.fetchRowForSid) g.fetchRowForSid = patched;
    if (g.mesh_stats_client && g.mesh_stats_client.fetchRowForSid) {
      g.mesh_stats_client.fetchRowForSid = patched;
    }
    console.log("[MeshStatsPatch] installed fetchRowForSid hook (base:", STATS_BASE, "bust:", BUST + ")");
    return true;
  }

  // 2) Safety net: rewrite any fetches that target /stats/*.json on the page
  //    to add cache busting and no-store. This fixes stale-cache issues even
  //    if we can't find the internal function.
  const origFetch = window.fetch.bind(window);
  window.fetch = async function patchedFetch(input, init = {}) {
    try {
      const url = typeof input === "string" ? input : (input && input.url) || "";
      // match /stats/###.json anywhere (root or /client)
      if (/\b\/stats\/\d{3}\.json(\?.*)?$/.test(url)) {
        const bustUrl = url + (url.includes("?") ? "&" : "?") + "bust=" + BUST;
        const opts = Object.assign({}, init, { cache: "no-store" });
        return origFetch(bustUrl, opts);
      }
    } catch {}
    return origFetch(input, init);
  };

  // Keep trying to hook until the UI loads (or give up after ~60s)
  let attempts = 0;
  const id = setInterval(() => {
    attempts++;
    if (tryHookFetchRow() || attempts > 120) clearInterval(id);
  }, 500);
})();
