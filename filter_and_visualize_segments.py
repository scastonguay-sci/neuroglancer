# filter_and_visualize_segments.py
# Filter segments by anisotropy and S/V ratio, generate Neuroglancer state

import csv
import json

# Filter criteria
ANISOTROPY_MIN = 1.3
ANISOTROPY_MAX = 2.0
SV_RATIO_MIN = 1.7
SV_RATIO_MAX = 2.2

print("="*70)
print("FILTERING MESH STATS FOR VISUALIZATION")
print("="*70)
print(f"Criteria:")
print(f"  Anisotropy: {ANISOTROPY_MIN} - {ANISOTROPY_MAX}")
print(f"  S/V ratio: {SV_RATIO_MIN} - {SV_RATIO_MAX}")
print("="*70)

# Read and filter
matching_ids = []
total_rows = 0
skipped_no_aniso = 0
skipped_no_sv = 0

print("\nReading mesh_volumes.csv...")
with open('mesh_volumes.csv', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        total_rows += 1
        if total_rows % 1000000 == 0:
            print(f"  Processed {total_rows:,} rows, found {len(matching_ids):,} matches...")
        
        sid = row['sid']
        
        # Parse values
        try:
            anisotropy = float(row['anisotropy']) if row.get('anisotropy') and row['anisotropy'].strip() else None
            sv_ratio = float(row['sv_ratio']) if row.get('sv_ratio') and row['sv_ratio'].strip() else None
        except (ValueError, KeyError):
            continue
        
        # Skip if missing required values
        if anisotropy is None:
            skipped_no_aniso += 1
            continue
        if sv_ratio is None:
            skipped_no_sv += 1
            continue
        
        # Check if matches criteria
        if (ANISOTROPY_MIN <= anisotropy <= ANISOTROPY_MAX and 
            SV_RATIO_MIN <= sv_ratio <= SV_RATIO_MAX):
            matching_ids.append({
                'sid': sid,
                'anisotropy': anisotropy,
                'sv_ratio': sv_ratio,
                'surface_area_um2': float(row['surface_area_um2']) if row.get('surface_area_um2') else None,
                'volume_um3': float(row['volume_um3']) if row.get('volume_um3') else None,
                'n_vertices': int(row['n_vertices']) if row.get('n_vertices') else None,
            })

print(f"\n{'='*70}")
print(f"RESULTS")
print(f"{'='*70}")
print(f"Total rows processed: {total_rows:,}")
print(f"Skipped (no anisotropy): {skipped_no_aniso:,}")
print(f"Skipped (no S/V ratio): {skipped_no_sv:,}")
print(f"Matching segments: {len(matching_ids):,}")
print(f"{'='*70}")

if len(matching_ids) == 0:
    print("\n⚠️  No segments match the criteria!")
    exit(0)

# Save list of IDs
output_ids = 'filtered_segment_ids.txt'
with open(output_ids, 'w') as f:
    for item in matching_ids:
        f.write(f"{item['sid']}\n")
print(f"\n✓ Saved segment IDs to: {output_ids}")

# Save detailed stats
output_csv = 'filtered_segments_stats.csv'
with open(output_csv, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['sid', 'anisotropy', 'sv_ratio', 'surface_area_um2', 'volume_um3', 'n_vertices'])
    for item in matching_ids:
        writer.writerow([
            item['sid'],
            f"{item['anisotropy']:.4f}",
            f"{item['sv_ratio']:.4f}",
            f"{item['surface_area_um2']:.2f}" if item['surface_area_um2'] else "",
            f"{item['volume_um3']:.2f}" if item['volume_um3'] else "",
            item['n_vertices'] if item['n_vertices'] else ""
        ])
print(f"✓ Saved detailed stats to: {output_csv}")

# Generate Neuroglancer state JSON
# This will pre-select all matching segments
neuroglancer_state = {
    "title": f"Filtered Segments (Aniso: {ANISOTROPY_MIN}-{ANISOTROPY_MAX}, S/V: {SV_RATIO_MIN}-{SV_RATIO_MAX})",
    "dimensions": {
        "x": [8e-9, "m"],
        "y": [8e-9, "m"],
        "z": [30e-9, "m"]
    },
    "position": [23967.5, 13376.0, 3895.5],
    "crossSectionScale": 4,
    "projectionScale": 8192,
    "layers": [
        {
            "type": "segmentation",
            "source": "precomputed://gs://zetta-katz-sea-slug-seg/ng/seg/whole-pt2-v1-250625",
            "tab": "segments",
            "name": "seg",
            "segments": [str(item['sid']) for item in matching_ids[:1000]],  # Limit to first 1000 to avoid huge state
            "segmentQuery": f"anisotropy:{ANISOTROPY_MIN}~{ANISOTROPY_MAX} sv_ratio:{SV_RATIO_MIN}~{SV_RATIO_MAX}"
        }
    ],
    "layout": "4panel"
}

output_json = 'neuroglancer_state.json'
with open(output_json, 'w') as f:
    json.dump(neuroglancer_state, f, indent=2)
print(f"✓ Saved Neuroglancer state to: {output_json}")

# Generate URL-friendly state (JSON string)
import urllib.parse
state_str = json.dumps(neuroglancer_state, separators=(',', ':'))
encoded_state = urllib.parse.quote(state_str)

# Create shareable URL
base_url = "https://scastonguay-sci.github.io/neuroglancer/client/"
full_url = f"{base_url}#!{encoded_state}"

# Save URL
output_url = 'neuroglancer_url.txt'
with open(output_url, 'w') as f:
    f.write(full_url)

print(f"✓ Saved Neuroglancer URL to: {output_url}")
print(f"\n{'='*70}")
print(f"VISUALIZATION")
print(f"{'='*70}")

if len(matching_ids) > 1000:
    print(f"⚠️  Note: Only first 1000 of {len(matching_ids):,} segments included in state")
    print(f"   (to keep URL manageable)")

print(f"\nOpen this URL to visualize the filtered segments:")
print(f"\n{full_url[:200]}...")
print(f"\nOr manually:")
print(f"  1. Open: {base_url}")
print(f"  2. Load layer: seg")
print(f"  3. Use Mesh Stats Filter panel to apply filters")
print(f"     - Anisotropy: {ANISOTROPY_MIN} - {ANISOTROPY_MAX}")
print(f"     - S/V Ratio: {SV_RATIO_MIN} - {SV_RATIO_MAX}")
print(f"\n{'='*70}")

# Show some statistics
print(f"\nSTATISTICS OF FILTERED SEGMENTS:")
print(f"{'='*70}")
anisotropies = [item['anisotropy'] for item in matching_ids]
sv_ratios = [item['sv_ratio'] for item in matching_ids]
volumes = [item['volume_um3'] for item in matching_ids if item['volume_um3']]

import statistics
print(f"Anisotropy:")
print(f"  Mean: {statistics.mean(anisotropies):.4f}")
print(f"  Median: {statistics.median(anisotropies):.4f}")
print(f"  Std Dev: {statistics.stdev(anisotropies):.4f}")

print(f"\nS/V Ratio:")
print(f"  Mean: {statistics.mean(sv_ratios):.4f}")
print(f"  Median: {statistics.median(sv_ratios):.4f}")
print(f"  Std Dev: {statistics.stdev(sv_ratios):.4f}")

if volumes:
    print(f"\nVolume (μm³):")
    print(f"  Mean: {statistics.mean(volumes):.2f}")
    print(f"  Median: {statistics.median(volumes):.2f}")
    print(f"  Min: {min(volumes):.2f}")
    print(f"  Max: {max(volumes):.2f}")

print(f"{'='*70}")
