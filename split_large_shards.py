# split_large_shards.py
# Split shards that exceed GitHub's 100MB limit

import json
import os

SHARD_DIR = "stats"
MAX_SIZE_MB = 95  # Keep under 100MB with some buffer
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024

print("Checking for large shard files...")

large_shards = []
for filename in os.listdir(SHARD_DIR):
    if not filename.endswith('.json'):
        continue
    
    filepath = os.path.join(SHARD_DIR, filename)
    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    
    if size_mb > MAX_SIZE_MB:
        large_shards.append((filename, size_mb))
        print(f"  {filename}: {size_mb:.1f} MB - NEEDS SPLITTING")

if not large_shards:
    print("✓ All shards are under 95MB")
    exit(0)

print(f"\nSplitting {len(large_shards)} large shards...")

for filename, size_mb in large_shards:
    filepath = os.path.join(SHARD_DIR, filename)
    prefix = filename.replace('.json', '')
    
    print(f"\nProcessing {filename} ({size_mb:.1f} MB)...")
    
    # Load the data
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    print(f"  Total entries: {len(data):,}")
    
    # Calculate how many parts we need
    estimated_bytes_per_entry = os.path.getsize(filepath) / len(data)
    entries_per_part = int(MAX_SIZE_BYTES / estimated_bytes_per_entry)
    num_parts = (len(data) + entries_per_part - 1) // entries_per_part
    
    print(f"  Splitting into {num_parts} parts (~{entries_per_part:,} entries each)")
    
    # Split into parts
    for part_idx in range(num_parts):
        start_idx = part_idx * entries_per_part
        end_idx = min(start_idx + entries_per_part, len(data))
        part_data = data[start_idx:end_idx]
        
        part_filename = f"{prefix}_part{part_idx + 1}.json"
        part_filepath = os.path.join(SHARD_DIR, part_filename)
        
        with open(part_filepath, 'w') as f:
            json.dump(part_data, f, separators=(',', ':'))
        
        part_size_mb = os.path.getsize(part_filepath) / (1024 * 1024)
        print(f"    Created {part_filename}: {len(part_data):,} entries, {part_size_mb:.1f} MB")
    
    # Remove original large file
    os.remove(filepath)
    print(f"  Removed original {filename}")

print("\n✓ All large shards split successfully")
print("\nNOTE: You'll need to update mesh_stats_client.ts to handle part files")
