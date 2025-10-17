#!/usr/bin/env python3
# enumerate_mesh_sids_v3.py
# Enumerate *all* segment IDs present in a Neuroglancer sharded mesh directory.

import argparse, json, os, sys, urllib.parse
import tensorstore as ts
import requests


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mesh-dir", required=True,
                    help="Mesh directory URL (gs://.../mesh_mip_1_err_40/ or https://storage.googleapis.com/.../mesh_mip_1_err_40/)")
    ap.add_argument("--out", required=True, help="Output file for decimal SIDs (one per line)")
    return ap.parse_args()


def mesh_info_url(mesh_dir: str) -> str:
    mesh_dir = mesh_dir.rstrip("/") + "/"
    if mesh_dir.startswith("gs://"):
        # Use GCS JSON API via https for the info file to avoid auth issues in requests
        p = urllib.parse.urlparse(mesh_dir)
        bucket = p.netloc
        path = p.path.lstrip("/")
        return f"https://storage.googleapis.com/{bucket}/{path}info"
    else:
        # e.g. https://storage.googleapis.com/.../mesh_mip_1_err_40/
        return mesh_dir + "info"


def build_kv_spec(mesh_dir: str, sharding: dict):
    """
    Build a TensorStore KeyValueStore spec for neuroglancer_sharded.
    """
    mesh_dir = mesh_dir.rstrip("/") + "/"

    # Choose an underlying kvstore that supports range requests:
    if mesh_dir.startswith("gs://"):
        p = urllib.parse.urlparse(mesh_dir)
        kv = {
            "driver": "gcs",
            "bucket": p.netloc,
            "path": p.path.lstrip("/"),
        }
    else:
        # public HTTPS works fine for listing+range
        kv = {
            "driver": "http",
            "base_url": mesh_dir,
        }

    # neuroglancer_sharded expects the sharding members at the top level
    spec = {
        "driver": "neuroglancer_sharded",
        "kvstore": kv,
        # Copy only the fields it expects, to be safe:
        "data_encoding": sharding.get("data_encoding"),
        "hash": sharding.get("hash"),
        "minishard_bits": sharding.get("minishard_bits"),
        "minishard_index_encoding": sharding.get("minishard_index_encoding"),
        "preshift_bits": sharding.get("preshift_bits", 0),
        "shard_bits": sharding.get("shard_bits"),
    }
    return spec


def main():
    args = parse_args()
    info_url = mesh_info_url(args.mesh_dir)
    print("Reading info from:", info_url, file=sys.stderr)

    r = requests.get(info_url)
    r.raise_for_status()
    info = r.json()

    if "sharding" not in info:
        print("ERROR: mesh info missing 'sharding' field; not a sharded mesh dir?", file=sys.stderr)
        sys.exit(2)

    kv_spec = build_kv_spec(args.mesh_dir, info["sharding"])
    # Open the sharded kvstore
    kv = ts.open_kvstore(kv_spec).result()

    # List all keys (each key is a decimal segment-id string for NG mesh stores)
    print("Listing keys… (this can take a while)", file=sys.stderr)
    # list() returns an async range; convert to a concrete list of strings
    keys = list(kv.list().result())

    # Write to output
    out_path = os.path.expanduser(args.out)
    with open(out_path, "w") as f:
        for k in keys:
            # keys are already strings; keep as-is
            f.write(f"{k}\n")

    print(f"Wrote {len(keys):,} SIDs to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
