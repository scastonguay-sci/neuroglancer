# filter_and_visualize_segments_v2.py
# Filter segments by surface area, volume, and S/V ratio, generate Neuroglancer state

import csv
import json
import urllib.parse
from pathlib import Path

# Filter criteria
SURFACE_AREA_MIN = 70    # μm²
SURFACE_AREA_MAX = 520   # μm²
VOLUME_MIN = 30          # μm³
VOLUME_MAX = 250         # μm³
SV_RATIO_MIN = 1.3
SV_RATIO_MAX = 2.5

print("="*70)
print("FILTERING MESH STATS FOR VISUALIZATION")
print("="*70)
print(f"Criteria:")
print(f"  Surface Area: {SURFACE_AREA_MIN} - {SURFACE_AREA_MAX} μm²")
print(f"  Volume: {VOLUME_MIN} - {VOLUME_MAX} μm³")
print(f"  S/V ratio: {SV_RATIO_MIN} - {SV_RATIO_MAX}")
print("="*70)

# Read and filter
matching_ids = []
total_rows = 0
skipped_no_sa = 0
skipped_no_vol = 0
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
            surface_area = float(row['surface_area_um2']) if row.get('surface_area_um2') and row['surface_area_um2'].strip() else None
            volume = float(row['volume_um3']) if row.get('volume_um3') and row['volume_um3'].strip() else None
            sv_ratio = float(row['sv_ratio']) if row.get('sv_ratio') and row['sv_ratio'].strip() else None
        except (ValueError, KeyError):
            continue
        
        # Skip if missing required values
        if surface_area is None:
            skipped_no_sa += 1
            continue
        if volume is None:
            skipped_no_vol += 1
            continue
        if sv_ratio is None:
            skipped_no_sv += 1
            continue
        
        # Check if matches criteria
        if (SURFACE_AREA_MIN <= surface_area <= SURFACE_AREA_MAX and 
            VOLUME_MIN <= volume <= VOLUME_MAX and
            SV_RATIO_MIN <= sv_ratio <= SV_RATIO_MAX):
            matching_ids.append({
                'sid': sid,
                'surface_area_um2': surface_area,
                'volume_um3': volume,
                'sv_ratio': sv_ratio,
                'anisotropy': float(row['anisotropy']) if row.get('anisotropy') and row['anisotropy'].strip() else None,
                'n_vertices': int(row['n_vertices']) if row.get('n_vertices') else None,
            })

print(f"\n{'='*70}")
print(f"RESULTS")
print(f"{'='*70}")
print(f"Total rows processed: {total_rows:,}")
print(f"Skipped (no surface area): {skipped_no_sa:,}")
print(f"Skipped (no volume): {skipped_no_vol:,}")
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
    writer.writerow(['sid', 'surface_area_um2', 'volume_um3', 'sv_ratio', 'anisotropy', 'n_vertices'])
    for item in matching_ids:
        writer.writerow([
            item['sid'],
            f"{item['surface_area_um2']:.2f}",
            f"{item['volume_um3']:.2f}",
            f"{item['sv_ratio']:.4f}",
            f"{item['anisotropy']:.4f}" if item['anisotropy'] else "",
            item['n_vertices'] if item['n_vertices'] else ""
        ])
print(f"✓ Saved detailed stats to: {output_csv}")

# Generate Neuroglancer state JSON
# Limit to first 1000 segments to keep URL manageable
segments_to_show = matching_ids[:min(1000, len(matching_ids))]

neuroglancer_state = {
    "title": f"Filtered: SA {SURFACE_AREA_MIN}-{SURFACE_AREA_MAX}, Vol {VOLUME_MIN}-{VOLUME_MAX}, S/V {SV_RATIO_MIN}-{SV_RATIO_MAX}",
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
            "source": "precomputed://gs://zetta-katz-sea-slug-seg/ng/seg/whole-pt1-v1-250512",
            "tab": "segments",
            "name": "seg",
            "segments": [item['sid'] for item in segments_to_show],
        }
    ],
    "layout": "4panel"
}

output_json = 'neuroglancer_state.json'
with open(output_json, 'w') as f:
    json.dump(neuroglancer_state, f, indent=2)
print(f"✓ Saved Neuroglancer state to: {output_json}")

# Generate URL-friendly state (JSON string)
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
    print(f"⚠️  Note: Only first 1,000 of {len(matching_ids):,} segments included in state")
    print(f"   (to keep URL manageable)")

print(f"\nOpen this URL to visualize the filtered segments:")
if len(full_url) < 200:
    print(f"\n{full_url}")
else:
    print(f"\n{full_url[:200]}...")
    
print(f"\nOr manually:")
print(f"  1. Open: {base_url}")
print(f"  2. Use Mesh Stats Filter panel")
print(f"  3. Apply filters:")
print(f"     - Surface Area: {SURFACE_AREA_MIN} - {SURFACE_AREA_MAX}")
print(f"     - Volume: {VOLUME_MIN} - {VOLUME_MAX}")
print(f"     - S/V Ratio: {SV_RATIO_MIN} - {SV_RATIO_MAX}")
print(f"\n{'='*70}")

# Show some statistics
if len(matching_ids) > 0:
    print(f"\nSTATISTICS OF FILTERED SEGMENTS:")
    print(f"{'='*70}")
    
    import statistics
    
    surface_areas = [item['surface_area_um2'] for item in matching_ids]
    volumes = [item['volume_um3'] for item in matching_ids]
    sv_ratios = [item['sv_ratio'] for item in matching_ids]
    anisotropies = [item['anisotropy'] for item in matching_ids if item['anisotropy']]
    
    print(f"Surface Area (μm²):")
    print(f"  Mean: {statistics.mean(surface_areas):.2f}")
    print(f"  Median: {statistics.median(surface_areas):.2f}")
    print(f"  Min: {min(surface_areas):.2f}")
    print(f"  Max: {max(surface_areas):.2f}")
    
    print(f"\nVolume (μm³):")
    print(f"  Mean: {statistics.mean(volumes):.2f}")
    print(f"  Median: {statistics.median(volumes):.2f}")
    print(f"  Min: {min(volumes):.2f}")
    print(f"  Max: {max(volumes):.2f}")
    
    print(f"\nS/V Ratio:")
    print(f"  Mean: {statistics.mean(sv_ratios):.4f}")
    print(f"  Median: {statistics.median(sv_ratios):.4f}")
    print(f"  Std Dev: {statistics.stdev(sv_ratios):.4f}")
    
    if anisotropies:
        print(f"\nAnisotropy:")
        print(f"  Mean: {statistics.mean(anisotropies):.4f}")
        print(f"  Median: {statistics.median(anisotropies):.4f}")
        print(f"  Std Dev: {statistics.stdev(anisotropies):.4f}")
    
    print(f"{'='*70}")
