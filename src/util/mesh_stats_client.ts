// src/util/mesh_stats_client.ts
// Fetch shard + row for a given segment id, and stringify IDs safely.

export function toSidString(id: unknown): string {
  console.log("[toSidString] Input:", id, "Type:", typeof id);
  
  // Handle already-string IDs
  if (typeof id === "string") {
    const cleaned = id.replace(/^!/, ""); // strip NG's "!123…" JSON form
    console.log("[toSidString] String input, cleaned:", cleaned);
    return cleaned;
  }
  
  // Handle number/bigint
  if (typeof id === "number" || typeof id === "bigint") {
    const result = String(id);
    console.log("[toSidString] Number/bigint input, result:", result);
    return result;
  }
  
  // Neuroglancer may give {low,high} or [lo,hi] for uint64
  const asAny = id as any;
  
  // Check for Uint64 object format
  if (asAny && typeof asAny === "object") {
    // Log the object structure
    console.log("[toSidString] Object input keys:", Object.keys(asAny));
    console.log("[toSidString] Object values:", asAny);
    
    // Try various uint64 formats
    const lo = asAny.low ?? asAny.lo ?? asAny[0];
    const hi = asAny.high ?? asAny.hi ?? asAny[1];
    
    if (lo !== undefined && hi !== undefined) {
      try {
        // This is the fix - use unsigned conversion properly
        const loU32 = BigInt(lo) & 0xFFFFFFFFn;
        const hiU32 = BigInt(hi) & 0xFFFFFFFFn;
        const result = ((hiU32 << 32n) | loU32).toString();
        console.log(`[toSidString] Uint64 conversion: lo=${lo}, hi=${hi}, result=${result}`);
        return result;
      } catch (err) {
        console.error("[toSidString] Uint64 conversion error:", err);
      }
    }
    
    // Check if it has a toString method
    if (typeof asAny.toString === "function") {
      const result = asAny.toString();
      console.log("[toSidString] Using object.toString():", result);
      // Remove the 'n' suffix if it's a bigint string
      return result.replace(/n$/, '');
    }
  }
  
  // Fallback
  const result = String(id);
  console.log("[toSidString] Fallback to String():", result);
  return result;
}

function pagesBase(): string {
  // If we're on GitHub Pages, the app lives under /neuroglancer/client/
  // Locally (python/http-server from dist/client) it's just "."
  const isGitHubPages = location.hostname.endsWith("github.io");
  const base = isGitHubPages ? "/neuroglancer/client" : ".";
  console.log(`[pagesBase] hostname: ${location.hostname}, base: ${base}`);
  return base;
}

export async function fetchRowForSid(sid: string): Promise<any | null> {
  const clean = sid.replace(/^!/, "");
  
  // Try truncating to 17 digits if we have 18
  const searchIds = [clean];
  if (clean.length === 18) {
    searchIds.push(clean.slice(0, 17));  // Remove last digit
    searchIds.push(clean.slice(1));      // Remove first digit
  }
  
  const prefix = clean.slice(0, 3);
  if (!prefix || prefix.length < 3) {
    console.error(`[fetchRowForSid] Invalid SID format: "${sid}"`);
    return null;
  }
  
  const url = `${pagesBase()}/stats/${prefix}.json`;
  console.log(`[fetchRowForSid] Searching for IDs:`, searchIds);
  
  try {
    const res = await fetch(url, { cache: "force-cache" });
    if (!res.ok) return null;
    
    const arr = (await res.json()) as any[];
    
    // Try each possible ID format
    for (const searchId of searchIds) {
      const match = arr.find(r => r.sid === searchId);
      if (match) {
        console.log(`[fetchRowForSid] Found match with ${searchId}`);
        return match;
      }
    }
    
    console.log(`[fetchRowForSid] No match found for any variant of ${clean}`);
    return null;
  } catch (err) {
    console.error(`[fetchRowForSid] Error:`, err);
    return null;
  }
}