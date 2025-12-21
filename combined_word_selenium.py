import os
import math
import json
import random
import time
from functools import lru_cache

# Selenium imports
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# bip_utils imports
from bip_utils import (
    Bip39SeedGenerator, Bip39MnemonicValidator,
    Bip84, Bip84Coins, Bip44Changes
)

# ==========================
# === PART 1: GF(256) MATH
# ==========================

def _precompute_gf256_exp_log():
    exp = [0 for _ in range(255)]
    log = [0 for _ in range(256)]
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
    return 0 if a == 0 or b == 0 else EXP_TABLE[(LOG_TABLE[a] + LOG_TABLE[b]) % 255]

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
    if b == 0:
        return 1
    if a == 0:
        return 0
    c = a
    for _ in range(b - 1):
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
            if m == j:
                continue
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
def _f_val(S0, c1, c2, x):
    return _gf256_add(
        _gf256_add(S0, _gf256_mul(c1, x)),
        _gf256_mul(c2, _gf256_mul(x, x))
    )

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

# ==============================
# === PART 2: BITAPS DECODING
# ==============================

# Globals set later
wordlist = None
CODES = None

def decode_bitaps_share(mnemonic_phrase, wordlist_unused):
    """Decode Bitaps-like share (MSB-first). Uses global CODES table."""
    global CODES
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

# ============================
# === Wordlist & utilities ===
# ============================

def load_bip39_wordlist():
    path = os.path.join(os.path.dirname(__file__), "english.txt")
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()]

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

@lru_cache(maxsize=16384)
def decode_cached(phrase):
    global wordlist
    return decode_bitaps_share(phrase, wordlist)

# ========================
# === Beam Search Logic ==
# ========================

def guided_search_all_words(wordlist_, fingerprint, shareA, shareB,
                            beam_width=256, filler_word="abandon", verbose=True):
    global wordlist, CODES
    wordlist = wordlist_
    CODES = {w: i for i, w in enumerate(wordlist)}

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

                            key = f"{c1},{c2}"
                            if key not in fingerprint:
                                valid = False
                                break

                            step_score += fingerprint[key]
                        except Exception:
                            valid = False
                            break

                    if valid and (best_step_score is None or step_score > best_step_score):
                        best_step_score = step_score
                        best_x3 = x3_choice

                if best_step_score is not None:
                    next_beam.append(
                        (tuple(prefix_words + [w]), cum_score + best_step_score, best_x3)
                    )

        if not next_beam:
            print(f"\n❌ No candidates survived Step {step}.")
            break

        next_beam.sort(key=lambda t: t[1], reverse=True)
        beam = next_beam[:beam_width]

        if verbose:
            top_words = " ".join(beam[0][0])
            print(f"✅ Top prefix: {top_words}  | score={beam[0][1]:.2f}  | beam={len(beam)}")

    # Return full list of candidates (up to beam_width)
    return [(list(words), score) for (words, score, _) in beam]

# ==========================================================
# === Helper: get ALL candidate 3rd shares (not just best) ==
# ==========================================================

def find_candidate_shares(share_A, share_B,
                          fingerprint_path="fingerprint_map.json",
                          beam_width=256,
                          verbose=True):
    """Return list of (candidate_share_phrase, score), sorted by score desc."""
    print("Loading BIP39 wordlist...")
    wl = load_bip39_wordlist()
    print("Loading fingerprint map...")
    with open(fingerprint_path, "r") as f:
        fingerprint = json.load(f)
    print("✅ Fingerprint map loaded.")

    candidates = guided_search_all_words(
        wordlist_=wl,
        fingerprint=fingerprint,
        shareA=share_A,
        shareB=share_B,
        beam_width=beam_width,
        filler_word="abandon",
        verbose=verbose
    )

    if not candidates:
        raise RuntimeError("No candidates found for third share.")

    phrases_scores = [(" ".join(words), score) for (words, score) in candidates]

    print("\n🎯 Candidate 3rd shares (top to bottom):")
    for i, (ph, sc) in enumerate(phrases_scores[:10], start=1):
        print(f"  #{i:3d}: {ph}  → score={sc:.2f}")
    if len(phrases_scores) > 10:
        print(f"  ... and {len(phrases_scores) - 10} more up to beam width {beam_width}.")
    return phrases_scores

# ==================================================
# === PART 3: Selenium Restore + BIP84 Derivation ==
# ==================================================

def try_restore_and_derive(driver, wait, html_file_path,
                           share_A, share_B, share_C,
                           target_address):
    """Use Selenium to restore secret using A,B,C and derive BIP84 address.
       Returns (restored_mnemonic, derived_address, is_match).
    """
    restored_mnemonic = ""
    derived_address = None
    is_match = False

    # Load / reload the HTML page each attempt to reset UI
    driver.get("file:///" + html_file_path)
    print(f"Loaded HTML tool for shares: [A, B, C]")

    shares_to_restore = [share_A, share_B, share_C]

    try:
        for i, share in enumerate(shares_to_restore):
            share_number = i + 1
            print(f"  - Processing share {share_number}...")

            if share_number > 2:
                print("    -> Clicking '+add share' button...")
                add_button = wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//button[@onclick="add_share();"]'))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", add_button)
                add_button.click()
                print("    -> Button clicked successfully.")

            input_box_id = f"share-input-{share_number}"
            share_input_box = wait.until(
                EC.visibility_of_element_located((By.ID, input_box_id))
            )
            # Clear just in case
            share_input_box.clear()
            share_input_box.send_keys(share)
            print(f"    -> Entered share into box #{share_number}.")

        print("  - Clicking 'Restore' button...")
        restore_button = wait.until(
            EC.presence_of_element_located((By.ID, "restore-btn"))
        )
        driver.execute_script("arguments[0].click();", restore_button)
        print("  - Restore button clicked.")

        print("  - Waiting for restoration result...")
        restored_mnemonic_element = wait.until(
            EC.visibility_of_element_located((By.ID, "restored-result"))
        )
        wait.until(lambda d: restored_mnemonic_element.get_attribute("value") != "")
        restored_mnemonic = restored_mnemonic_element.get_attribute("value")

    except Exception as e:
        print(f"  ❌ Error during restoration with this share: {e}")
        return restored_mnemonic, derived_address, is_match

    print("  ✅ Got restored mnemonic.")
    print(f"  Restored Mnemonic: {restored_mnemonic}")

    # ====== Derive address from restored mnemonic ======
    try:
        if not Bip39MnemonicValidator().IsValid(restored_mnemonic):
            raise ValueError("Restored mnemonic phrase is not valid.")

        print("  - Generating seed from mnemonic...")
        seed_bytes = Bip39SeedGenerator(restored_mnemonic).Generate()

        print("  - Deriving BIP84 wallet...")
        bip84_wallet = Bip84.FromSeed(seed_bytes, Bip84Coins.BITCOIN)

        print("  - Deriving address at m/84'/0'/0'/0/0...")
        derived_address = (
            bip84_wallet
            .Purpose()
            .Coin()
            .Account(0)
            .Change(Bip44Changes.CHAIN_EXT)
            .AddressIndex(0)
            .PublicKey()
            .ToAddress()
        )

        print(f"  → Derived address: {derived_address}")

        if target_address:
            if derived_address.strip().lower() == target_address.strip().lower():
                print("  ✅ Address MATCHES target!")
                is_match = True
            else:
                print(f"  ❌ Address does not match target ({target_address}).")
        else:
            print("  (No target address configured; skipping comparison.)")

    except Exception as e:
        print(f"  ❌ Error during address derivation: {e}")

    return restored_mnemonic, derived_address, is_match

# =========================
# === MAIN ENTRY POINT ====
# =========================

if __name__ == "__main__":
    # --- CONFIGURATION ---

    # First two shares (fixed)
    share_A = "rocket ankle party unusual exercise humble surround expect train helmet away marriage"
    share_B = "mass sock lemon degree enact awful glad valve toilet shadow upset tunnel"

    html_file_path = r"C:\Users\tulsi\Downloads\Bitcoin mnemonic code tools.html"
    driver_executable_path = r"C:\Daksh\SSSS\msedgedriver.exe"
    target_address = "bc1qyjwa0tf0en4x09magpuwmt2smpsrlaxwn85lh6"

    fingerprint_path = "fingerprint_map.json"  # adjust if needed
    beam_width = 10                           # up to 256 candidate 3rd shares

    # --- STAGE 0: Compute ALL candidate 3rd shares with guided search ---
    try:
        candidate_shares = find_candidate_shares(
            share_A,
            share_B,
            fingerprint_path=fingerprint_path,
            beam_width=beam_width,
            verbose=True
        )
    except Exception as e:
        print(f"\n❌ Failed to compute candidate 3rd shares: {e}")
        raise SystemExit(1)

    print(f"\nTotal candidate 3rd shares to test: {len(candidate_shares)}")

    # --- STAGE 1+2: For EACH candidate, restore + derive + compare ---
    service = EdgeService(executable_path=driver_executable_path)
    driver = webdriver.Edge(service=service)
    wait = WebDriverWait(driver, 10)

    print("\nBrowser opened successfully.\n")

    match_found = False
    matching_share = None
    matching_address = None

    try:
        for idx, (share_C, score) in enumerate(candidate_shares, start=1):
            print("\n" + "=" * 70)
            print(f"Testing candidate #{idx}/{len(candidate_shares)}")
            print(f"Share C (score={score:.2f}): {share_C}")
            print("=" * 70)

            restored_mnemonic, derived_address, is_match = try_restore_and_derive(
                driver=driver,
                wait=wait,
                html_file_path=html_file_path,
                share_A=share_A,
                share_B=share_B,
                share_C=share_C,
                target_address=target_address,
            )

            if is_match:
                match_found = True
                matching_share = share_C
                matching_address = derived_address
                print("\n🎉 MATCH FOUND!")
                print(f"  -> 3rd share: {matching_share}")
                print(f"  -> Address:  {matching_address}")
                break
            else:
                print("No match with this candidate. Moving to next...\n")

    finally:
        print("\nClosing the browser.")
        driver.quit()

    print("\n" + "=" * 40)
    if match_found:
        print("✅ FINAL RESULT: Matching address found!")
        print(f"3rd Share: {matching_share}")
        print(f"Address : {matching_address}")
    else:
        print("❌ No candidate 3rd share produced the target address.")
    print("=" * 40)
