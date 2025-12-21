# guided_mnemonic_search.py

import os
import math
import json

# === GF(256) math from old_shamir.py ===
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
def _gf256_mul(a, b): return 0 if a == 0 or b == 0 else EXP_TABLE[(LOG_TABLE[a] + LOG_TABLE[b]) % 255]
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
def _interpolation(points, x=0):
    k = len(points)
    if k < 2:
        raise Exception("Minimum 2 points required")
    points = sorted(points, key=lambda z: z[0])
    p_x = 0
    for j in range(k):
        p_j_x = 1
        for m in range(k):
            if m == j: continue
            a = _gf256_sub(x, points[m][0])
            b = _gf256_sub(points[j][0], points[m][0])
            c = _gf256_div(a, b)
            p_j_x = _gf256_mul(p_j_x, c)
        p_j_x = _gf256_mul(points[j][1], p_j_x)
        p_x = _gf256_add(p_x, p_j_x)
    return p_x

def get_coefficients_from_points(points):
    S0 = _interpolation(points, x=0)
    f1 = _interpolation(points, x=1)
    f2 = _interpolation(points, x=2)
    s1 = _gf256_add(f1, S0)
    s2 = _gf256_add(f2, S0)
    c2 = _gf256_div(_gf256_add(s2, _gf256_mul(2, s1)), 6)
    c1 = _gf256_add(s1, c2)
    return S0, c1, c2

# === Sanity check: verify (S0, c1, c2) reconstruction ===
import random
def _f_val(S0, c1, c2, x):
    return _gf256_add(_gf256_add(S0, _gf256_mul(c1, x)), _gf256_mul(c2, _gf256_mul(x, x)))

for _ in range(50):
    S0 = random.randint(0, 255)
    c1 = random.randint(0, 255)
    c2 = random.randint(0, 255)
    xs = [1, 37, 123]
    pts = [(x, _f_val(S0, c1, c2, x)) for x in xs]
    S0r, c1r, c2r = get_coefficients_from_points(pts)
    if (S0r, c1r, c2r) != (S0, c1, c2):
        raise AssertionError("GF(256) interpolation mismatch — check coefficient logic!")
print("✅ GF(256) sanity check passed.")

# === Bitaps decoding (MSB-first) ===
def decode_bitaps_share(mnemonic_phrase, wordlist):
    codes = CODES
    words = mnemonic_phrase.split()
    bits = 0
    for w in words:
        bits = (bits << 11) | codes[w]
    total_bits = len(words) * 11
    chk_bits = total_bits % 32
    entropy = bits >> chk_bits
    x = bits & ((1 << chk_bits) - 1)
    data = entropy.to_bytes(16, byteorder="big")
    return x, data

# === Wordlist and fingerprint ===
def load_bip39_wordlist():
    path = os.path.join(os.path.dirname(__file__), "english.txt")
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()]

def build_loglikelihood(fingerprint, floor=1):
    return [math.log(fingerprint.get(v, floor)) for v in range(256)]

# 0-indexed version (Word 0 to Word 11)
WORD_TO_BYTES = {
    1:  [0, 1],
    2:  [1, 2],
    3:  [2, 3, 4],
    4:  [4, 5],
    5:  [5, 6],
    6:  [6, 7, 8],
    7:  [8, 9],
    8:  [9, 10],
    9:  [11, 12],
    10: [12, 13],
    11: [13, 14, 15],
    12: [15], # Plus 4 bits of checksum
}

from functools import lru_cache

@lru_cache(maxsize=16384)
def decode_cached(phrase):
    return decode_bitaps_share(phrase, wordlist)

# === Beam search ===
def guided_search_all_words(wordlist, fingerprint, shareA, shareB, beam_width=256, filler_word="abandon", verbose=True):
    x1, y1 = decode_bitaps_share(shareA, wordlist)
    x2, y2 = decode_bitaps_share(shareB, wordlist)
    allowed_x = [x for x in range(1, 16) if x not in (x1, x2)]
    index_to_word = list(wordlist)
    word_to_index = {w: i for i, w in enumerate(wordlist)}
    beam = [(tuple(), 0.0, None)]

    for step in range(1, 13):
        targets = WORD_TO_BYTES[step]
        next_beam = []

        if verbose:
            print(f"\n🔍 Step {step}/12 — targeting bytes {targets}")

        for prefix_i, (prefix, cum_score, x3_fixed) in enumerate(beam):
            prefix_words = list(prefix)
            x3_options = [x3_fixed] if x3_fixed is not None else allowed_x

            for w in wordlist:
                best_step_score = None
                best_x3 = None

                for x3_choice in x3_options:
                    if step == 12:
                        w_index = word_to_index[w]
                        if (w_index & 0x0F) != x3_choice:
                            continue

                    words = prefix_words + [w]
                    remaining = 12 - len(words)
                    if step < 12:
                        placeholder = index_to_word[x3_choice]
                        words += [placeholder] * remaining
                    phrase = " ".join(words)

                    try:
                        x3, y3 = decode_cached(phrase)
                        if x3 != x3_choice:
                            continue
                    except Exception:
                        continue

                    step_score = 0.0
                    valid = True
                    for b in targets:
                        try:
                            points = [(x1, y1[b]), (x2, y2[b]), (x3, y3[b])]
                            _, c1, c2 = get_coefficients_from_points(points)
                            # ...
                            try:
                                points = [(x1, y1[b]), (x2, y2[b]), (x3, y3[b])]
                                _, c1, c2 = get_coefficients_from_points(points)
                                
                                # This is the new, 2D logic
                                key = f"{c1},{c2}"
                                if key not in fingerprint:
                                    valid = False
                                    break # This (c1, c2) pair is impossible, discard the guess

                                # The score is the frequency of the pair itself
                                step_score += fingerprint[key]
                            except Exception:
                                valid = False
                                break
                        except Exception:
                            valid = False
                            break

                    if valid and (best_step_score is None or step_score > best_step_score):
                        best_step_score = step_score
                        best_x3 = x3_choice

                if best_step_score is not None:
                    next_beam.append((tuple(prefix_words + [w]), cum_score + best_step_score, best_x3))

        if not next_beam:
            print(f"\n❌ No candidates survived Step {step}.")
            break

        next_beam.sort(key=lambda t: t[1], reverse=True)
        beam = next_beam[:beam_width]

        if verbose:
            top_words = " ".join(beam[0][0])
            print(f"✅ Top prefix: {top_words}  | score={beam[0][1]:.2f}  | beam={len(beam)}")

    return [(list(words), score) for (words, score, _) in beam]

# === Main ===
if __name__ == "__main__":
    wordlist = load_bip39_wordlist()
    CODES = {w: i for i, w in enumerate(wordlist)}
    # --- Load the complete fingerprint map from the file ---
    print("Loading fingerprint map...")
    with open("fingerprint_map.json", "r") as f:
        fingerprint = json.load(f)
    print("✅ Fingerprint map loaded.")
    
    share_A = "session cigar grape merry useful churn fatal thought very any arm unaware" 
    share_B = "clock fresh security field caution effort gorilla speed plastic common tomato echo"

    candidates = guided_search_all_words(
        wordlist=wordlist,
        fingerprint=fingerprint,
        shareA=share_A,
        shareB=share_B,
        beam_width=256,  # You can increase this later
        filler_word="abandon",
        verbose=True
    )

    print("\n🎯 Final top-scoring 12-word paths:")
    for words, score in candidates[:10]:
        print("  " + " ".join(words), f"→ score={score:.2f}")