import random
from collections import Counter

# === GF(256) math (COPIED DIRECTLY from guided_search_all_words.py) ===
# This ensures the math is identical.
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

def _gf256_add(a, b): return a ^ b
def _gf256_sub(a, b): return a ^ b
def _gf256_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return EXP_TABLE[ (LOG_TABLE[a] + LOG_TABLE[b]) % 255 ]
def _gf256_inverse(a):
    if a == 0:
        raise ZeroDivisionError()
    return EXP_TABLE[(-LOG_TABLE[a]) % 255]
def _gf256_div(a, b):
    if b == 0:
        raise ZeroDivisionError()
    if a == 0:
        return 0
    r = _gf256_mul(a, _gf256_inverse(b))
    assert a == _gf256_mul(r, b)
    return r
def _gf256_pow(a, b):
    if b == 0: return 1
    if a == 0: return 0
    c = a
    for i in range(b - 1):
        c = _gf256_mul(c, a)
    return c
# === End of GF(256) math block ===


def generate_gf256_coefficients(iterations):
    """
    Generates coefficients c1 and c2 by simulating the creation
    of random polynomials: f(x) = S0 + c1*x + c2*x^2
    """
    coeff_counter = Counter()
    rand = random.SystemRandom()
    
    for _ in range(iterations):
        # We only care about c1 and c2, as the search script only scores them
        
        # This assumes the original secret's c1 was chosen randomly
        c1 = rand.randint(0, 255) 
        
        # This assumes the original secret's c2 was chosen randomly
        c2 = rand.randint(0, 255)
        
        coeff_counter[c1] += 1
        coeff_counter[c2] += 1
        
    return coeff_counter

def run_fingerprint_analysis(iterations=1000000):
    print(f"🔍 Running GF(256) fingerprint analysis with {iterations} iterations...")
    # Each iteration generates 2 coefficients (c1, c2)
    coeff_map = generate_gf256_coefficients(iterations)
    
    total = sum(coeff_map.values())
    print(f"\n📊 Total coefficients generated: {total}")
    print(f"🧮 Unique coefficients: {len(coeff_map)}")

    # With enough iterations, this should be empty.
    missing = [i for i in range(256) if i not in coeff_map]
    if missing:
        print(f"\n🚫 Coefficients that never appeared (missing):")
        print(f"  {missing}")

    print(f"\n📈 Frequencies (top 20):")
    # A random distribution should be very flat
    for val, freq in coeff_map.most_common(20):
        print(f"  {val}: {freq}")
        
    # Print the full dictionary to copy-paste
    print("\n--- Copy-pastable fingerprint dictionary ---")
    print(dict(coeff_map))


if __name__ == "__main__":
    run_fingerprint_analysis()