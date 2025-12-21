from collections import Counter

# --- Part 1: Galois Field GF(2^8) Math ---
def _precompute_gf256_exp_log():
    exp = [0] * 255
    log = [0] * 256
    poly = 1
    for i in range(255):
        exp[i] = poly
        log[poly] = i
        poly = (poly << 1) ^ poly
        if poly & 0x100:
            poly ^= 0x11B
    return exp, log

EXP_TABLE, LOG_TABLE = _precompute_gf256_exp_log()

def gf_mul(a, b):
    if a == 0 or b == 0: return 0
    return EXP_TABLE[(LOG_TABLE[a] + LOG_TABLE[b]) % 255]

def gf_div(a, b):
    if b == 0: raise ZeroDivisionError()
    if a == 0: return 0
    return EXP_TABLE[(LOG_TABLE[a] - LOG_TABLE[b]) % 255]

def gf_add(a, b):
    return a ^ b

def get_coefficients_from_points(points):
    x1, y1 = points[0]
    x2, y2 = points[1]
    x3, y3 = points[2]

    S0_num = gf_add(gf_mul(y1, gf_mul(x2, x3)),
                    gf_add(gf_mul(y2, gf_mul(x1, x3)),
                           gf_mul(y3, gf_mul(x1, x2))))
    S0_den = gf_add(gf_mul(gf_add(x1, x2), gf_add(x1, x3)),
                    gf_add(gf_mul(gf_add(x2, x1), gf_add(x2, x3)),
                           gf_mul(gf_add(x3, x1), gf_add(x3, x2))))
    S0 = gf_div(S0_num, S0_den)

    c1_num = gf_add(gf_mul(y1, gf_add(x2, x3)),
                    gf_add(gf_mul(y2, gf_add(x1, x3)),
                           gf_mul(y3, gf_add(x1, x2))))
    c1 = gf_div(c1_num, S0_den)

    c2_num = gf_add(y1, gf_add(y2, y3))
    c2 = gf_div(c2_num, S0_den)

    return S0, c1, c2

# --- Part 2: Mnemonic Decoding ---
import os

def load_bip39_wordlist():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    wordlist_path = os.path.join(script_dir, "english.txt")
    with open(wordlist_path, "r") as f:
        return [line.strip() for line in f.readlines()]

def manual_words_to_bytes(mnemonic_str, wordlist):
    word_to_index = {word: idx for idx, word in enumerate(wordlist)}
    words = mnemonic_str.strip().split()
    binary_chunks = [format(word_to_index[word], '011b') for word in words]
    full_binary_str = "".join(binary_chunks)
    data_binary_str = full_binary_str[:128]
    return int(data_binary_str, 2).to_bytes(16, 'big')

# --- Part 3: Coefficient Test ---
def run_coefficient_test():
    wordlist = load_bip39_wordlist()

    share_A = "session cigar grape merry useful churn fatal thought very any arm unaware"
    share_B = "salute hope cheap crash arrest joke reform room cause notable loan feed"

    x1, x2 = 1, 2
    y1 = manual_words_to_bytes(share_A, wordlist)[0]
    y2 = manual_words_to_bytes(share_B, wordlist)[0]

    c1_counter = Counter()
    c2_counter = Counter()
    invalid_guesses = 0
    valid_guesses = 0

    print("--- Running Coefficient Test ---")
    for word in wordlist:
        fake_mnemonic = word + " " + "abandon " * 11
        try:
            y3 = manual_words_to_bytes(fake_mnemonic.strip(), wordlist)[0]
        except KeyError:
            continue
        x3 = 3
        points = [(x1, y1), (x2, y2), (x3, y3)]
        try:
            S0, c1, c2 = get_coefficients_from_points(points)
        except ZeroDivisionError:
            continue
        c1_counter[c1] += 1
        c2_counter[c2] += 1
        if c1 == 255 or c2 == 255:
            invalid_guesses += 1
        else:
            valid_guesses += 1

    total = invalid_guesses + valid_guesses
    print("\n--- ✅ Test Complete ---")
    print(f"Total guesses: {total}")
    print(f"Invalid guesses (coeff = 255): {invalid_guesses}")
    print(f"Valid guesses (coeff ≠ 255): {valid_guesses}")
    print(f"Reduction potential: {(invalid_guesses / total) * 100:.2f}%")

    print("\n📊 c1 Frequencies:")
    for val, freq in c1_counter.most_common():
        print(f"  {val}: {freq} times")

    print("\n📊 c2 Frequencies:")
    for val, freq in c2_counter.most_common():
        print(f"  {val}: {freq} times")

if __name__ == "__main__":
    print("⚠️ Make sure 'english.txt' contains the full BIP39 wordlist.")
    run_coefficient_test()