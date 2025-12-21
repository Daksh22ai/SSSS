import json
import full_word_search as g

# ====== CONFIG: paste your 3 known-good shares here ======

# These are the ones from your example:
share_A = "help huge dizzy strategy black glide clever apple fence mind ranch explain"  # x=2
share_B = "toss piece again barrel keen twenty pave laptop balance bachelor pave trade"              # x=4

# Pick ONE true 3rd share to test (e.g. x=8)
true_share_C = "sand tree mirror web okay cousin veteran used daughter popular dog slide"        # x=8
# You can later try the x=13 or x=14 share instead if you want:
# true_share_C = "sweet update gold plug inject camera affair tilt hello solid account worry"   # x=13
# true_share_C = "fence cattle camp glare brave possible monster noble common fat bag episode" # x=14

FINGERPRINT_PATH = "fingerprint_map.json"

# =========================================================

def main():
    # 1) Load wordlist and set up CODES the same way guided_mnemonic_search does
    wordlist = g.load_bip39_wordlist()
    g.CODES = {w: i for i, w in enumerate(wordlist)}

    # 2) Decode the three mnemonics to (x, 16-byte data)
    x1, y1 = g.decode_bitaps_share(share_A, wordlist)
    x2, y2 = g.decode_bitaps_share(share_B, wordlist)
    x3, y3 = g.decode_bitaps_share(true_share_C, wordlist)

    print(f"x1={x1}, x2={x2}, x3={x3}")
    print(f"len(y1)={len(y1)}, len(y2)={len(y2)}, len(y3)={len(y3)}")

    if not (len(y1) == len(y2) == len(y3) == 16):
        print("❌ Unexpected share byte lengths; expected 16 bytes each.")
        return

    # 3) Load fingerprint map
    with open(FINGERPRINT_PATH, "r") as f:
        fingerprint = json.load(f)

    present = 0
    missing = 0

    print("\nPer-byte (c1, c2) and fingerprint lookup:\n")

    for b in range(16):
        points = [(x1, y1[b]), (x2, y2[b]), (x3, y3[b])]
        _, c1, c2 = g.get_coefficients_from_points(points)
        key = f"{c1},{c2}"
        if key in fingerprint:
            freq = fingerprint[key]
            present += 1
            print(f"byte {b:2d}: c1={c1:3d}, c2={c2:3d}  → present, freq={freq}")
        else:
            missing += 1
            print(f"byte {b:2d}: c1={c1:3d}, c2={c2:3d}  → ❌ MISSING in fingerprint")

    print("\nSummary:")
    print(f"  Present in fingerprint: {present} bytes")
    print(f"  Missing in fingerprint: {missing} bytes")


if __name__ == "__main__":
    main()
