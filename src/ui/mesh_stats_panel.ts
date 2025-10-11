// src/ui/mesh_stats_panel.ts
import { SidePanel } from "#src/ui/side_panel.js";
import { fetchRowForSid } from "#src/util/mesh_stats_client.js";

function escapeHtml(s: string) {
  return s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

export class MeshStatsPanel extends SidePanel {
  private body: HTMLDivElement;

  constructor(...args: ConstructorParameters<typeof SidePanel>) {
    super(...args);
    this.element.classList.add("mesh-stats-panel");
    this.addTitleBar({ title: "Mesh Stats" });

    // Use a dedicated body so we don't nuke the title bar/content wrapper.
    this.body = document.createElement("div");
    this.body.style.padding = "8px";
    this.addBody(this.body);

    this.setMessage("No selection");
  }

  /** Replace panel content with a friendly message. */
  setMessage(msg: string) {
    this.body.innerHTML = `<i>${escapeHtml(msg)}</i>`;
  }

  /** Render a stats object. Accepts null/undefined to show "No stats". */
  setStats(stats: any | null) {
    if (!stats) {
      this.setMessage("No stats");
      return;
    }
    // Render a compact summary plus expandable raw JSON.
    const {
      sid,
      n_vertices,
      n_faces,
      surface_area_um2,
      volume_um3,
      sv_ratio,
      anisotropy,
      watertight,
    } = stats as any;

    const fmt = (v: unknown, d = 2) =>
      typeof v === "number" && Number.isFinite(v) ? v.toFixed(d) : "—";

    this.body.innerHTML = `
      <div style="font-weight:600;margin-bottom:6px">SID: <code>${escapeHtml(String(sid ?? "—"))}</code></div>
      <div style="display:flex;flex-wrap:wrap;gap:10px;color:#bbb;font-size:12px">
        <span>Vertices: ${n_vertices ?? "—"}</span>
        <span>Faces: ${n_faces ?? "—"}</span>
        <span>Watertight: ${watertight ? "yes" : "no"}</span>
        <span>Surface: ${fmt(surface_area_um2)} μm²</span>
        <span>Volume: ${fmt(volume_um3)} μm³</span>
        <span>S/V: ${fmt(sv_ratio, 3)}</span>
        <span>Aniso: ${fmt(anisotropy, 3)}</span>
      </div>
      <details style="margin-top:8px">
        <summary style="cursor:pointer">Raw JSON</summary>
        <pre style="white-space:pre-wrap;margin:6px 0 0 0;font-size:11px">${escapeHtml(
          JSON.stringify(stats, null, 2),
        )}</pre>
      </details>
    `;
  }

  /**
   * Fetch stats for a given SID and render them.
   * Leaves a helpful message if not found or on error.
   */
  async showForSid(sid: string) {
    if (!sid) {
      this.setMessage("No SID provided");
      return;
    }
    try {
      this.setMessage(`Loading stats for ${sid}…`);
      const row = await fetchRowForSid(sid);
      if (!row) {
        this.setMessage(`No mesh stats found for ${sid}`);
        return;
      }
      this.setStats(row);
    } catch (err) {
      console.error("[MeshStatsPanel] fetch error for", sid, err);
      this.setMessage(`Error loading mesh stats for ${sid}`);
    }
  }
}

// NOTE: No registerPanelType() in this repo/version.