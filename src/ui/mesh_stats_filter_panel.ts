// src/ui/mesh_stats_filter_panel.ts
import { SidePanel } from "#src/ui/side_panel.js";

type StatRow = {
  sid: string;
  n_vertices?: number | null;
  n_faces?: number | null;
  surface_area_um2?: number | null;
  volume_um3?: number | null;
  sv_ratio?: number | null;
  anisotropy?: number | null;
  watertight?: boolean | null;
};

type Range = { min: number; max: number };
type Filters = {
  n_vertices: Range;
  n_faces: Range;
  surface_area_um2: Range;
  volume_um3: Range;
  sv_ratio: Range;
  anisotropy: Range;
  watertight: boolean | null;
};

function pagesBase() {
  return location.hostname.endsWith("github.io") ? "/neuroglancer/client" : ".";
}

function coerceNum(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : null;
}
function fmtMaybe(v: unknown, digits = 2) {
  const n = coerceNum(v);
  return n === null ? "—" : n.toFixed(digits);
}

export class MeshStatsFilterPanel extends SidePanel {
  viewer: any | null = null;

  private allStats: StatRow[] = [];
  private filteredStats: StatRow[] = [];
  private filters: Filters = {
    n_vertices: { min: 0, max: Infinity },
    n_faces: { min: 0, max: Infinity },
    surface_area_um2: { min: 0, max: Infinity },
    volume_um3: { min: 0, max: Infinity },
    sv_ratio: { min: 0, max: Infinity },
    anisotropy: { min: 0, max: Infinity },
    watertight: null,
  };

  private ui = {
    container: document.createElement("div"),
    results: document.createElement("div"),
    list: document.createElement("div"),
    loading: document.createElement("div"),
  };

  constructor(...args: ConstructorParameters<typeof SidePanel>) {
    super(...args);
    this.element.classList.add("neuroglancer-mesh-stats-filter");
    this.addTitleBar({ title: "Mesh Stats Filter" });

    this.buildUI();
    this.loadAllStats(); // ✅ no error now
  }

  // ----------------- Data loading -----------------
  private async loadAllStats() {
    const base = pagesBase();
    const prefixes = [
      "720","721","722","723","724","725","726","727","728","729",
      "730","731","732","733","734","735","736","737","738","739",
      "740","741","742","743",
    ];

    const all: StatRow[] = [];
    for (const p of prefixes) {
      try {
        const res = await fetch(`${base}/stats/${p}.json`, { cache: "force-cache" });
        if (res.ok) {
          const arr = (await res.json()) as StatRow[];
          all.push(...arr);
        } else {
          console.warn(`Shard ${p}.json: HTTP ${res.status}`);
        }
      } catch (err) {
        console.warn(`Shard ${p}.json fetch error:`, err);
      }
    }

    this.allStats = all;
    this.filteredStats = [...all];
    this.ui.loading.remove();
    this.updateDisplay();
  }

  // ----------------- UI (build, filters, update) -----------------
  private buildUI() {
    const root = this.ui.container;
    root.style.padding = "10px";
    root.style.fontSize = "11px";

    // … keep your filter inputs / watertight checkbox …
    this.ui.loading.textContent = "Loading mesh stats…";
    this.ui.loading.style.padding = "8px";
    this.element.appendChild(this.ui.loading);

    this.element.appendChild(root);
    root.appendChild(this.ui.results);
    root.appendChild(this.ui.list);
  }

  private applyFilters() {
    const f = this.filters;
    this.filteredStats = this.allStats.filter((row) => {
      const checks: Array<[keyof Filters & string, number | null]> = [
        ["n_vertices", coerceNum(row.n_vertices)],
        ["n_faces", coerceNum(row.n_faces)],
        ["surface_area_um2", coerceNum(row.surface_area_um2)],
        ["volume_um3", coerceNum(row.volume_um3)],
        ["sv_ratio", coerceNum(row.sv_ratio)],
        ["anisotropy", coerceNum(row.anisotropy)],
      ];
      for (const [k, v] of checks) {
        if (v === null) continue;
        const r = f[k] as Range;
        if (v < r.min || v > r.max) return false;
      }
      if (f.watertight !== null && (row.watertight ?? false) !== f.watertight) return false;
      return true;
    });
    this.updateDisplay();
  }

  private updateDisplay() {
    const total = this.allStats.length;
    const shown = this.filteredStats.length;
    this.ui.results.innerHTML =
      `<strong>${shown.toLocaleString()} segments</strong> / ${total.toLocaleString()} total`;
    this.ui.list.innerHTML = "";

    const cap = 100;
    for (const row of this.filteredStats.slice(0, cap)) {
      const item = document.createElement("div");
      item.style.padding = "6px";
      item.innerHTML =
        `<div style="color:#4a9eff;font-family:monospace">${row.sid}</div>` +
        `<div style="color:#aaa;font-size:10px">V:${row.n_vertices ?? "—"} F:${row.n_faces ?? "—"} SA:${fmtMaybe(row.surface_area_um2)} Vol:${fmtMaybe(row.volume_um3)} S/V:${fmtMaybe(row.sv_ratio)} Aniso:${fmtMaybe(row.anisotropy)}</div>`;
      item.onclick = () => this.navigateToSegment(row.sid);
      this.ui.list.appendChild(item);
    }
  }

  private navigateToSegment(sid: string) {
    console.log("[MeshStatsFilter] Navigate to:", sid);
    if (this.viewer) {
      try {
        this.viewer.selectedSegments.add(sid);
        this.viewer.layerList.setSelectedLayerByName("seg");
        this.viewer.navigateToSegment?.(sid);
      } catch (err) {
        console.warn("Viewer navigation failed", err);
      }
    }
  }
}