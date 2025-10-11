

import "#src/ui/selection_details.css";

// Mesh stats helpers (fetch shard + stringify uint64 IDs)
import { fetchRowForSid, toSidString } from "#src/util/mesh_stats_client.js";

import svg_arrowLeft from "ikonate/icons/arrow-left.svg?raw";
import svg_arrowRight from "ikonate/icons/arrow-right.svg?raw";
import type {
  SelectedLayerState,
  TopLevelLayerListSpecification,
  TrackableDataSelectionState,
} from "#src/layer/index.js";
import { getDefaultSelectBindings } from "#src/ui/default_input_event_bindings.js";
import type { SidePanelManager } from "#src/ui/side_panel.js";
import { SidePanel } from "#src/ui/side_panel.js";
import { setClipboard } from "#src/util/clipboard.js";
import type { Borrowed } from "#src/util/disposable.js";
import { MouseEventBinder } from "#src/util/mouse_bindings.js";
import { CheckboxIcon } from "#src/widget/checkbox_icon.js";
import { makeCopyButton } from "#src/widget/copy_button.js";
import { DependentViewWidget } from "#src/widget/dependent_view_widget.js";
import { makeIcon } from "#src/widget/icon.js";
import { makeMoveToButton } from "#src/widget/move_to_button.js";

export function isWithinSelectionPanel(element: HTMLElement) {
  return element.closest(".neuroglancer-selection-details");
}

export class SelectionDetailsPanel extends SidePanel {
  body = document.createElement("div");

  constructor(
    public sidePanelManager: SidePanelManager,
    public state: Borrowed<TrackableDataSelectionState>,
    public manager: Borrowed<TopLevelLayerListSpecification>,
    public selectedLayer: Borrowed<SelectedLayerState>,
  ) {
    super(sidePanelManager, state.location);
    const { element, body } = this;
    element.classList.add("neuroglancer-selection-details");
    this.registerDisposer(
      new MouseEventBinder(this.element, getDefaultSelectBindings()),
    );

    const { titleBar } = this.addTitleBar({ title: "Selection" });
    const backButton = makeIcon({
      svg: svg_arrowLeft,
      title: "Previous selection",
      onClick: () => {
        this.state.goBack();
      },
    });
    const forwardButton = makeIcon({
      svg: svg_arrowRight,
      title: "Next selection",
      onClick: () => {
        this.state.goForward();
      },
    });
    titleBar.appendChild(backButton);
    titleBar.appendChild(forwardButton);
    titleBar.appendChild(
      this.registerDisposer(
        new CheckboxIcon(state.pin, {
          // Note: \ufe0e forces text display; otherwise the pin may render as a color emoji.
          text: "📌\ufe0e",
          enableTitle: "Pin selection",
          disableTitle: "Unpin selection",
        }),
      ).element,
    );
    body.classList.add("neuroglancer-selection-details-body");
    this.addBody(body);
    body.appendChild(
      this.registerDisposer(
        new DependentViewWidget(state, (stateValue, parent, context) => {
          if (!state.location.visible) return;
          backButton.style.visibility = state.canGoBack() ? "visible" : "hidden";
          forwardButton.style.visibility = state.canGoForward() ? "visible" : "hidden";
          if (stateValue === undefined) return;

          // --- Position block (original behavior) ---
          const { position } = stateValue;
          if (position !== undefined) {
            const positionElement = document.createElement("div");
            positionElement.classList.add("neuroglancer-selection-details-position");
            const copyButton = makeCopyButton({
              title: "Copy position",
              onClick: () => {
                setClipboard(position!.map((x) => Math.floor(x)).join(", "));
              },
            });
            positionElement.appendChild(copyButton);
            const {
              coordinateSpace: { rank, names },
              position,
            } = stateValue;
            for (let i = 0; i < rank; ++i) {
              const dimElement = document.createElement("span");
              dimElement.classList.add("neuroglancer-selection-details-position-dimension");
              const nameElement = document.createElement("span");
              nameElement.classList.add("neuroglancer-selection-details-position-dimension-name");
              nameElement.textContent = names[i];
              const coordinateElement = document.createElement("span");
              coordinateElement.classList.add(
                "neuroglancer-selection-details-position-dimension-coordinate",
              );
              coordinateElement.textContent = Math.floor(position![i]).toString();
              dimElement.appendChild(nameElement);
              dimElement.appendChild(coordinateElement);
              positionElement.appendChild(dimElement);
            }
            const moveToButton = makeMoveToButton({
              title: "Move to position",
              onClick: () => {
                this.manager.globalPosition.value = position!;
              },
            });
            positionElement.appendChild(moveToButton);
            parent.appendChild(positionElement);
          }

          // --- Per-layer selection details (original) + Mesh stats addon ---
          for (const layerData of stateValue.layers) {
            const { layer } = layerData;
            parent.appendChild(
              context.registerDisposer(
                new DependentViewWidget(
                  {
                    value: undefined,
                    changed: layer.managedLayer.layerChanged,
                  },
                  async (_, parent, context) => {
                    if (layer.wasDisposed) return;
                    if (!layer.isReady) return;

                    const layerBody = document.createElement("div");
                    layerBody.classList.add("neuroglancer-selection-details-layer-body");

                    // Let the layer render its built-in selection UI first.
                    if (!layer.displaySelectionState(layerData.state, layerBody, context)) {
                      return;
                    }

                    const layerElement = document.createElement("div");
                    parent.appendChild(layerElement);
                    layerElement.classList.add("neuroglancer-selection-details-layer");

                    const layerTitle = document.createElement("div");
                    layerTitle.classList.add("neuroglancer-selection-details-layer-title");
                    layerTitle.textContent = layer.managedLayer.name;
                    layerTitle.addEventListener("click", () => {
                      this.selectedLayer.layer = layer.managedLayer;
                      this.selectedLayer.visible = true;
                    });
                    layerTitle.title = "Click to show layer side panel";

                    layerElement.appendChild(layerTitle);
                    layerElement.appendChild(layerBody);

                    // ---------- Mesh stats inline card ----------
                    try {
                      const st: any = layerData.state;
                      
                      // Debug logging
                      console.log("[MeshStats] Layer name:", layer.managedLayer.name);
                      console.log("[MeshStats] State object:", st);

                      // Try all possible ID sources (including pickedValue for hover)
                      const candidateId =
                        st?.objectId ??
                        st?.segmentSelection?.id ??
                        st?.segmentSelection?.segment ??
                        st?.selectedSegment ??
                        st?.segment ??
                        st?.pickedValue ??
                        st?.value ??
                        undefined;

                      console.log("[MeshStats] Candidate ID found:", candidateId);

                      if (candidateId === undefined) {
                        console.log("[MeshStats] No candidate ID found");
                        return;
                      }

                      const sid = toSidString(candidateId);
                      console.log("[MeshStats] Converted to SID string:", sid);
                      
                      if (!sid || sid === "undefined" || sid === "null") {
                        console.log("[MeshStats] Invalid SID after conversion");
                        return;
                      }

                      console.log("[MeshStats] Fetching stats for SID:", sid);
                      const stats = await fetchRowForSid(sid);
                      console.log("[MeshStats] Fetched stats:", stats);
                      
                      if (!stats) {
                        console.log("[MeshStats] No stats found for SID:", sid);
                        const noStatsBlock = document.createElement("div");
                        noStatsBlock.style.marginTop = "8px";
                        noStatsBlock.style.padding = "8px";
                        noStatsBlock.style.color = "#888";
                        noStatsBlock.style.fontSize = "11px";
                        noStatsBlock.textContent = `No mesh stats found for ID: ${sid}`;
                        layerBody.appendChild(noStatsBlock);
                        return;
                      }

                      console.log("[MeshStats] Creating stats block");
                      const block = document.createElement("div");
                      block.style.marginTop = "8px";
                      block.style.padding = "8px";
                      block.style.border = "1px solid var(--neuroglancer-ui-border-color)";
                      block.style.borderRadius = "6px";
                      block.style.background = "var(--neuroglancer-background)";
                      block.style.fontFamily =
                        "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
                      block.style.fontSize = "11px";
                      block.style.lineHeight = "1.35";

                      const sa = stats.surface_area_um2 != null ? 
                        (typeof stats.surface_area_um2 === 'number' ? stats.surface_area_um2.toFixed(2) : stats.surface_area_um2) : "—";
                      const vol = stats.volume_um3 != null ? 
                        (typeof stats.volume_um3 === 'number' ? stats.volume_um3.toFixed(2) : stats.volume_um3) : "—";
                      const nv = stats.n_vertices ?? "—";
                      const nf = stats.n_faces ?? "—";
                      const wt = stats.watertight ? "yes" : "no";
                      const sv = stats.sv_ratio != null ? 
                        (typeof stats.sv_ratio === 'number' ? stats.sv_ratio.toFixed(4) : stats.sv_ratio) : "—";
                      const an = stats.anisotropy != null ? 
                        (typeof stats.anisotropy === 'number' ? stats.anisotropy.toFixed(4) : stats.anisotropy) : "—";

                      block.innerHTML =
                        `<div style="font-weight:600;margin-bottom:4px">` +
                        `Mesh stats (id: ${escapeHtml(sid)})</div>` +
                        `<div>vertices: ${nv} &nbsp; faces: ${nf} &nbsp; watertight: ${wt}</div>` +
                        `<div>surface area: ${sa} μm² &nbsp; volume: ${vol} μm³</div>` +
                        `<div>S/V: ${sv} &nbsp; anisotropy: ${an}</div>` +
                        `<details style="margin-top:4px"><summary style="cursor:pointer">raw JSON</summary>` +
                        `<pre style="white-space:pre-wrap;margin:4px 0 0 0;font-size:10px">${escapeHtml(
                          JSON.stringify(stats, null, 2),
                        )}</pre></details>`;

                      layerBody.appendChild(block);
                      console.log("[MeshStats] Stats block appended successfully");
                    } catch (error) {
                      console.error("[MeshStats] Error in mesh stats:", error);
                      const errorBlock = document.createElement("div");
                      errorBlock.style.marginTop = "8px";
                      errorBlock.style.padding = "8px";
                      errorBlock.style.color = "#f88";
                      errorBlock.style.fontSize = "11px";
                      errorBlock.textContent = `Error loading mesh stats: ${error}`;
                      layerBody.appendChild(errorBlock);
                    }
                    // -------------------------------------------
                  },
                ),
              ).element,
            );
          }
        }),
      ).element,
    );
  }

  close() {
    super.close();
    this.state.value = undefined;
    this.state.pin.value = true;
  }
}

// Small util used by the inline card
function escapeHtml(s: string) {
  return s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}