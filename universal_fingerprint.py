import json
from collections import Counter

def generate_universal_fingerprint():
    print("🔍 Generating Universal Mathematical Fingerprint...")
    
    pair_counter = Counter()
    
    # The flawed code logic:
    # a = 0..255
    # i = 1..100 (derived from time.time() % 0.0001)
    # coeff = (a * i) % 255
    
    # We simulate 'iterations' of the loop. 
    # In the real code, 'a' is random every time. 'i' depends on time.
    # But 'c1' and 'c2' are generated back-to-back.
    # The correlation is that 'i2' is likely equal to 'i1' (or i1 + small_delta).
    
    # Assumption: On a fast server, i1 and i2 are likely the SAME or very close.
    # Let's generate pairs assuming i1 and i2 are close.
    
    range_a = range(256)
    range_i = range(1, 101) # The range 1 to 100 derived from the math
    
    # We weight the generation to simulate "random a" and "random i"
    # Since we want a probability map, we can iterate all combinations.
    
    for i in range_i:
        # For a given moment in time 'i', 'a' can be anything.
        # c1 and c2 are generated in the same loop, so they share the same 'i' 
        # (or extremely close). Let's assume they share 'i'.
        
        for a1 in range_a:
            c1 = (a1 * i) % 255
            
            for a2 in range_a:
                c2 = (a2 * i) % 255
                
                # This pair (c1, c2) is possible for this time slice 'i'
                pair_counter[f"{c1},{c2}"] += 1

    print(f"✅ Generated {len(pair_counter)} unique pairs.")
    
    print("💾 Saving to fingerprint_map.json...")
    with open("fingerprint_map.json", "w") as f:
        json.dump(pair_counter, f)
    print("DONE.")

if __name__ == "__main__":
    generate_universal_fingerprint()