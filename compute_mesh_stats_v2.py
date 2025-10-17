#!/usr/bin/env python3
"""
compute_mesh_stats_v2.py

Computes per-SID mesh stats (surface area, volume, S/V ratio, anisotropy)
for all SIDs that have a mesh, and writes results as NDJSON.

Usage example:
  python3 compute_mesh_stats_v2.py \
      --mesh-dir https://storage.googleapis.com/zetta-katz-sea-slug-seg/ng/seg/whole-pt2-v1-250625/mesh_mip_1_err_40/ \
      --sids ~/labels_all/sids_with_mesh_v2.txt \
      --out ~/labels_all/stats_combined_v2.ndjson \
      --resume
"""

import os, sys, json, time, math, argparse, random
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import numpy as np
from cloudvolume import CloudVolume

try:
    import trimesh  # optional, for volume and watertight check
except Exception:
    trimesh = None


# ---------- Geometry helpers ----------

def tri_area(v0, v1, v2):
    return 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1)

def surface_area(vertices: np.ndarray, faces: np.ndarray) -> float:
    v0, v1, v2 = vertices[faces[:,0]], vertices[faces[:,1]], vertices[faces[:,2]]
    return float(np.sum(tri_area(v0, v1, v2)))

def anisotropy_from_vertices(vertices: np.ndarray) -> Optional[float]:
    if vertices.shape[0] < 3:
        return None
    X = vertices - vertices.mean(axis=0, keepdims=True)
    cov = (X.T @ X) / max(1, X.shape[0]-1)
    w, _ = np.linalg.eigh(cov)
    w = np.maximum(w, 1e-12)
    return float(math.sqrt(w[-1] / w[0]))

def volume_and_watertight(vertices: np.ndarray, faces: np.ndarray) -> Tuple[Optional[float], Optional[bool]]:
    if trimesh is None:
        return None, None
    try:
        m = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        return (float(m.volume) if m.is_watertight else None), bool(m.is_watertight)
    except Exception:
        return None, None

def compute_stats_for_mesh(verts: np.ndarray, faces: np.ndarray) -> Dict[str, Any]:
    n_vertices = int(verts.shape[0])
    n_faces    = int(faces.shape[0])
    sa         = surface_area(verts, faces)
    aniso      = anisotropy_from_vertices(verts)
    vol, tight = volume_and_watertight(verts, faces)

    return {
        "n_vertices": n_vertices,
        "n_faces": n_faces,
        "surface_area_um2": sa,
        "volume_um3": vol,
        "sv_ratio": (sa/vol if (vol and vol > 0) else None),
        "anisotropy": aniso,
        "watertight": tight,
    }

def load_mesh(cv: CloudVolume, sid: int):
    got = cv.mesh.get([sid])
    m = got.get(sid) or got.get(int(sid))
    if m is None:
        return None
    verts = np.asarray(m.vertices, dtype=np.float32)
    faces = np.asarray(m.faces, dtype=np.int64)
    if verts.size == 0 or faces.size == 0:
        return None
    return verts, faces


# ---------- Main ----------

def parse_args():
    p = argparse.ArgumentParser(description="Compute mesh stats v2")
    p.add_argument("--mesh-dir", required=True, help="Precomputed mesh directory (mesh_mip_1_err_40)")
    p.add_argument("--sids", default=str(Path.home()/ "labels_all" / "sids_with_mesh_v2.txt"))
    p.add_argument("--out", default=str(Path.home()/ "labels_all" / "stats_combined_v2.ndjson"))
    p.add_argument("--resume", action="store_true", help="Resume from existing output")
    p.add_argument("--shuffle", action="store_true", help="Randomize SID order")
    p.add_argument("--limit", type=int, default=0, help="Limit to N SIDs for testing")
    p.add_argument("--https", action="store_true", help="Force HTTPS for CloudVolume")
    return p.parse_args()

def read_done_sids(out_path: str) -> set:
    done = set()
    if not os.path.exists(out_path):
        return done
    with open(out_path, "r") as f:
        for line in f:
            try:
                row = json.loads(line)
                if "sid" in row:
                    done.add(str(row["sid"]))
            except Exception:
                pass
    return done

def main():
    args = parse_args()
    cv = CloudVolume(f"precomputed://{args.mesh_dir}", use_https=args.https)

    with open(args.sids, "r") as f:
        sids = [line.strip() for line in f if line.strip()]
    if args.shuffle:
        random.shuffle(sids)
    if args.limit > 0:
        sids = sids[:args.limit]

    done = read_done_sids(args.out) if args.resume else set()

    print(f"Total SIDs: {len(sids)} | Already done: {len(done)} | Remaining: {len(sids)-len(done)}")
    out = open(args.out, "a", buffering=1)

    t0 = time.time()
    ok = fail = 0

    for i, sid_str in enumerate(sids, 1):
        if sid_str in done:
            continue
        try:
            sid_int = int(sid_str)
        except Exception:
            print(f"[WARN] invalid SID: {sid_str}")
            fail += 1
            continue

        try:
            pair = load_mesh(cv, sid_int)
            if pair is None:
                row = { "sid": sid_str,
                        "n_vertices": None, "n_faces": None,
                        "surface_area_um2": None, "volume_um3": None,
                        "sv_ratio": None, "anisotropy": None, "watertight": None }
            else:
                verts, faces = pair
                stats = compute_stats_for_mesh(verts, faces)
                row = { "sid": sid_str, **stats }

            out.write(json.dumps(row) + "\n")
            ok += 1

        except KeyboardInterrupt:
            print("\nInterrupted — saving progress.")
            break
        except Exception as e:
            print(f"[ERROR] SID {sid_str}: {e}")
            fail += 1

        if i % 50 == 0:
            elapsed = time.time() - t0
            print(f"[{i}/{len(sids)}] processed; {ok} ok, {fail} failed, {elapsed/60:.1f} min elapsed")

    out.close()
    print(f"\nDone. Success {ok}, failed {fail}. Wrote {args.out}")
    print(f"Total time: {(time.time()-t0)/60:.1f} minutes")

if __name__ == "__main__":
    main()
