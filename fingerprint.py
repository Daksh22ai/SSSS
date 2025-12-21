import time
import random
import os
from collections import Counter

# --- Part 1: All GF(2^8) Math from old_shamir.py ---
# This is a perfect copy of the flawed, original math

def _precompute_gf256_exp_log():
    exp = [0 for i in range(255)]
    log = [0 for i in range(256)]
    poly = 1
    for i in range(255):
        exp[i] = poly
        log[poly] = i
        poly = (poly << 1) ^ poly
        if poly & 0x100:
            poly ^= 0x11B
    return exp, log

EXP_TABLE, LOG_TABLE = _precompute_gf256_exp_log()

def _gf256_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return EXP_TABLE[(LOG_TABLE[a] + LOG_TABLE[b]) % 255]

def _gf256_pow(a, b):
    if b == 0: return 1
    if a == 0: return 0
    c = a
    for i in range(b - 1):
        c = _gf256_mul(c, a)
    return c

def _gf256_add(a, b): return a ^ b
def _gf256_sub(a, b): return a ^ b
def _gf256_inverse(a):
    if a == 0: raise ZeroDivisionError()
    return EXP_TABLE[(-LOG_TABLE[a]) % 255]
def _gf256_div(a, b):
    if b == 0: raise ZeroDivisionError()
    if a == 0: return 0
    r = _gf256_mul(a, _gf256_inverse(b))
    assert a == _gf256_mul(r, b)
    return r

def _fn(x, q):
    r = 0
    for i, a in enumerate(q):
        r = _gf256_add(r, _gf256_mul(a, _gf256_pow(x, i)))
    return r

# --- Part 2: The Flawed split_secret (Modified for Logging) ---

# CRITICAL CHANGE 1: Global list to log the pairs
COEFFICIENT_LOG = []

def split_secret(threshold, total, secret, index_bits=8):
    """
    This is the flawed split_secret from old_shamir.py,
    modified to log the (c1, c2) coefficient pairs.
    """
    if not isinstance(secret, bytes):
        raise TypeError("Secret as byte string required")
    # ... (other checks from the original file) ...

    shares = dict()
    shares_indexes = []
    index_max = 2 ** index_bits - 1

    while len(shares) != total:
        q = random.SystemRandom().randint(1, index_max)
        if q in shares:
            continue
        shares_indexes.append(q)
        shares[q] = b""

    # This loop runs for each byte of the secret (e.g., 16 times)
    for b in secret:
        q = [b]
        
        # CRITICAL CHANGE 2: Log the (c1, c2) pair
        coeffs_for_this_byte = []
        
        # This loop runs (threshold - 1) times (e.g., 2 times for 3-of-5)
        for i in range(threshold - 1):
            a = random.SystemRandom().randint(0, 255)
            i_val = int((time.time() % 0.0001) * 1000000) + 1
            coeff = (a * i_val) % 255
            q.append(coeff)
            coeffs_for_this_byte.append(coeff) # Store the generated coeff
        
        # After the inner loop, if we have a pair, log it
        if len(coeffs_for_this_byte) == 2:
            COEFFICIENT_LOG.append(tuple(coeffs_for_this_byte))

        for z in shares_indexes:
            shares[z] += bytes([_fn(z, q)])
            
    return shares

# --- Part 3: The Fingerprint Runner ---

def run_fingerprint_analysis(threshold=3, iterations=10000):
    """
    Runs the flawed split_secret to generate and log coefficient pairs.
    """
    print(f"🔍 Running fingerprint analysis...")
    print(f"   Simulating {iterations} secret splits to generate {iterations * 16} coefficient pairs.")
    
    # Run the simulation
    for _ in range(iterations):
        random_secret = os.urandom(16) # 16 bytes for a 12-word phrase
        split_secret(threshold, 5, random_secret)

    # Count the logged pairs
    pair_counter = Counter(COEFFICIENT_LOG)
    total_pairs = sum(pair_counter.values())
    unique_pairs = len(pair_counter)

    print(f"\n📊 Total pairs generated: {total_pairs}")
    print(f"🧮 Unique pairs found: {unique_pairs} (out of 65,536 possible)")

    print(f"\n🚫 Coefficients that never appeared (missing):")
    missing_c1 = {i for i in range(256) if i not in {p[0] for p in pair_counter}}
    missing_c2 = {i for i in range(256) if i not in {p[1] for p in pair_counter}}
    print(f"   c1 never generated: {missing_c1}")
    print(f"   c2 never generated: {missing_c2}")

    print(f"\n📈 Top 50 most common (c1, c2) pairs:")
    for pair, freq in pair_counter.most_common(50):
        print(f"   {pair}: {freq} times")
        
# --- Add this code to the end of your fingerprint script ---

    print("\n💾 Saving full fingerprint map to fingerprint_map.json...")
    
    # Convert tuple keys (e.g., (85, 170)) to string keys (e.g., "85,170")
    # This is required for JSON format
    string_key_map = {f"{pair[0]},{pair[1]}": freq for pair, freq in pair_counter.items()}
    
    import json
    with open("fingerprint_map.json", "w") as f:
        json.dump(string_key_map, f)
        
    print("✅ Map saved successfully.")

if __name__ == "__main__":
    run_fingerprint_analysis(threshold=3, iterations=10000)
    
    