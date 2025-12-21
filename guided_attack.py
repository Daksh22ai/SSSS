import os
from collections import Counter

# Load fingerprint map from Phase 1
fingerprint = {
    0: 4896, 180: 2522, 195: 2503, 60: 2493, 240: 2478, 45: 2468, 225: 2463, 120: 2456, 105: 2449, 15: 2444, 210: 2427, 75: 2422, 150: 2419, 135: 2414, 90: 2396, 165: 2381, 30: 2381, 170: 2256, 85: 2191, 204: 1675, 51: 1643, 102: 1633, 153: 1606, 132: 1070, 99: 1064, 96: 1059, 252: 1053, 126: 1052, 9: 1050, 162: 1050, 129: 1045, 237: 1039, 222: 1032, 183: 1032, 21: 1029, 84: 1028, 48: 1024, 198: 1023, 147: 1023, 141: 1023, 138: 1020, 231: 1019, 18: 1019, 171: 1017, 201: 1014, 24: 1014, 159: 1013, 114: 1012, 87: 1012, 117: 1012, 168: 1010, 57: 1009, 123: 1009, 63: 1009, 156: 1007, 207: 1007, 228: 1005, 234: 1005, 192: 1003, 36: 1001, 108: 997, 213: 997, 144: 996, 39: 996, 186: 994, 42: 992, 12: 991, 249: 990, 93: 989, 243: 989, 174: 988, 189: 986, 27: 986, 111: 984, 219: 982, 66: 982, 81: 978, 6: 977, 3: 970, 177: 970, 246: 964, 72: 959, 33: 953, 78: 948, 216: 939, 140: 931, 69: 927, 155: 927, 54: 913, 5: 908, 250: 908, 130: 905, 245: 904, 65: 901, 95: 900, 20: 897, 185: 891, 160: 890, 230: 888, 235: 888, 55: 884, 220: 879, 205: 876, 25: 874, 70: 874, 115: 871, 10: 869, 200: 869, 190: 867, 175: 864, 100: 862, 80: 861, 35: 860, 40: 857, 119: 842, 187: 833, 215: 829, 221: 828, 136: 827, 125: 825, 110: 821, 68: 819, 50: 815, 238: 814, 145: 813, 17: 811, 34: 783, 32: 414, 116: 403, 212: 401, 1: 399, 79: 398, 206: 393, 52: 391, 178: 390, 152: 388, 91: 388, 151: 387, 229: 387, 197: 385, 211: 384, 209: 384, 241: 382, 193: 382, 203: 381, 167: 380, 61: 379, 169: 379, 86: 379, 184: 378, 67: 377, 92: 377, 173: 376, 191: 376, 236: 375, 122: 374, 82: 374, 176: 373, 26: 373, 106: 373, 29: 372, 242: 372, 143: 371, 101: 371, 4: 370, 94: 370, 83: 369, 112: 369, 128: 369, 124: 368, 202: 368, 107: 368, 161: 367, 43: 367, 28: 367, 89: 367, 154: 366, 181: 366, 58: 366, 218: 366, 163: 364, 37: 364, 182: 364, 53: 363, 97: 362, 47: 361, 8: 361, 137: 361, 22: 361, 41: 360, 199: 360, 223: 360, 157: 360, 142: 359, 188: 359, 158: 359, 73: 359, 244: 359, 224: 358, 113: 358, 16: 357, 139: 357, 104: 357, 56: 357, 247: 357, 44: 357, 71: 357, 214: 356, 11: 356, 64: 355, 253: 354, 98: 353, 149: 352, 133: 352, 254: 350, 103: 349, 232: 348, 23: 348, 49: 347, 59: 346, 88: 346, 46: 346, 226: 345, 194: 345, 146: 344, 14: 344, 74: 344, 179: 344, 121: 343, 148: 343, 2: 343, 31: 343, 251: 343, 109: 342, 118: 342, 19: 342, 164: 342, 77: 340, 127: 340, 227: 339, 233: 339, 166: 339, 196: 337, 62: 335, 131: 334, 13: 333, 208: 333, 134: 332, 217: 332, 76: 331, 7: 330, 239: 330, 172: 327, 248: 326, 38: 325
}

# Tier classification
tier1 = {k for k, v in fingerprint.items() if v > 2000}
tier2 = {k for k, v in fingerprint.items() if 1000 < v <= 2000}
tier3 = {k for k, v in fingerprint.items() if 400 < v <= 1000}
tier4 = {k for k, v in fingerprint.items() if v <= 400}

# --- GF(2^8) Lookup Tables ---
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

def get_coefficients_from_points(points):
    """Extracts S0, c1, c2 from three GF(2^8) points using interpolation."""

    def _gf256_mul(a, b):
        if a == 0 or b == 0:
            return 0
        return EXP_TABLE[ (LOG_TABLE[a] + LOG_TABLE[b]) % 255 ]

    def _gf256_pow(a, b):
        if b == 0:
            return 1
        if a == 0:
            return 0
        c = a
        for i in range(b - 1):
            c = _gf256_mul(c,a)
        return c

    def _gf256_add(a, b):
        return a ^ b

    def _gf256_sub(a, b):
        return a ^ b

    def _gf256_inverse(a):
        if a == 0:
            raise ZeroDivisionError()
        return EXP_TABLE[ (-LOG_TABLE[a]) % 255 ]

    def _gf256_div(a, b):
        if b == 0:
            raise ZeroDivisionError()
        if a == 0:
            return 0
        r = _gf256_mul(a, _gf256_inverse(b))
        assert a == _gf256_mul(r, b)
        return r


    def _fn(x, q):
        r = 0
        for i, a in enumerate(q):
            r = _gf256_add(r, _gf256_mul(a,_gf256_pow(x,i)))
        return r

    def _interpolation(points, x=0):
        k = len(points)
        if k < 2:
            raise Exception("Minimum 2 points required")

        points = sorted(points, key=lambda z: z[0])

        p_x = 0
        for j in range(k):
            p_j_x  = 1
            for m in range(k):

                if m == j:
                    continue
                a =  _gf256_sub(x, points[m][0])
                b =  _gf256_sub(points[j][0], points[m][0])
                c = _gf256_div(a, b)
                p_j_x = _gf256_mul(p_j_x, c)

            p_j_x = _gf256_mul( points[j][1], p_j_x)
            p_x  = _gf256_add(p_x , p_j_x)


        return p_x

    x1, y1 = points[0]
    x2, y2 = points[1]
    x3, y3 = points[2]

    S0 = _interpolation(points, x=0)
    f1 = _interpolation(points, x=1)
    c1 = _gf256_add(f1, S0)
    f2 = _interpolation(points, x=2)
    temp = _gf256_add(f2, S0)
    temp = _gf256_add(temp, _gf256_mul(2, c1))
    c2 = _gf256_div(temp, 4)

    return S0, c1, c2

def decode_bitaps_share(mnemonic_phrase, wordlist):
    """
    Correctly decodes a custom Bitaps mnemonic share.
    Returns a tuple: (share_index, share_data_bytes)
    """
    # Logic from mnemonic_to_entropy to get the share data (y-value)
    codes = {w: c for c, w in enumerate(wordlist)}
    words = mnemonic_phrase.split()
    entropy_int = 0
    for w in words:
        entropy_int = (entropy_int << 11) | codes[w]
    
    chk_sum_bit_len = len(words) * 11 % 32
    entropy_int_for_data = entropy_int >> chk_sum_bit_len
    share_data_bytes = entropy_int_for_data.to_bytes(16, byteorder="big")

    # Logic from get_mnemonic_checksum_data to get the share index (x-value)
    share_index = entropy_int & (2 ** chk_sum_bit_len - 1)
    
    return share_index, share_data_bytes

# Load BIP39 wordlist
def load_bip39_wordlist():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    wordlist_path = os.path.join(script_dir, "english.txt")
    with open(wordlist_path, "r") as f:
        return [line.strip() for line in f.readlines()]

# Fixed shares
share_A = "jar absorb outer nothing tortoise hair smooth warrior favorite suggest proof coral"
share_B = "antenna eternal velvet ski ethics acquire sustain wide begin claim abstract make"

# Extract y-values
wordlist = load_bip39_wordlist()
x1, y1_bytes = decode_bitaps_share(share_A, wordlist)
x2, y2_bytes = decode_bitaps_share(share_B, wordlist)

# We are attacking the first byte of data
y1 = y1_bytes[0]
y2 = y2_bytes[0]

print("🚀 Starting guided brute-force attack...\n")
tier1_matches = []
tier2_matches = []

for word in wordlist:
    guess_mnemonic = word + " " + "abandon " * 11
    try:
        # --- FIX: Correctly extract X and Y from the guess ---
        x3, guess_bytes = decode_bitaps_share(guess_mnemonic.strip(), wordlist)
        y3 = guess_bytes[0]
    except (KeyError, ValueError):
        continue

    points = [(x1, y1), (x2, y2), (x3, y3)]
    
    try:
        S0, c1, c2 = get_coefficients_from_points(points)
    except ZeroDivisionError:
        continue

    if c1 == 255 or c2 == 255:
        continue

    if c1 in tier1 and c2 in tier1:
        tier1_matches.append(word)
    elif c1 in tier2 and c2 in tier2:
        tier2_matches.append(word)

print("\n--- ✅ Attack Complete ---")
if tier1_matches:
    print("🔥 Tier 1 matches found:")
    print("   " + ", ".join([f'"{w}"' for w in tier1_matches]))
if tier2_matches:
    print("⚡ Tier 2 matches found:")
    print("   " + ", ".join([f'"{w}"' for w in tier2_matches]))

if not tier1_matches and not tier2_matches:
    print("No high-probability matches found in Tier 1 or Tier 2.")