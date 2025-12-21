import os
from collections import Counter

# === Phase 1: Fingerprint Map ===
# This is the statistical map of the "loaded dice" flaw.
fingerprint = {
    0: 5523, 85: 2561, 45: 2511, 120: 2486, 170: 2481, 165: 2469, 15: 2466, 90: 2445, 75: 2428, 195: 2426, 210: 2417, 150: 2410, 240: 2409, 30: 2400, 225: 2395, 105: 2393, 135: 2389, 180: 2355, 60: 2349, 102: 1775, 204: 1774, 153: 1759, 51: 1684, 249: 1174, 117: 1160, 21: 1158, 219: 1154, 78: 1144, 123: 1139, 27: 1130, 246: 1127, 222: 1126, 24: 1125, 174: 1118, 108: 1114, 18: 1112, 201: 1112, 231: 1111, 111: 1108, 72: 1107, 162: 1106, 141: 1105, 138: 1105, 147: 1102, 228: 1102, 54: 1102, 114: 1101, 126: 1100, 66: 1098, 48: 1095, 183: 1094, 9: 1090, 96: 1088, 198: 1086, 129: 1086, 234: 1085, 42: 1083, 57: 1082, 237: 1082, 216: 1081, 171: 1073, 159: 1071, 69: 1071, 192: 1070, 144: 1070, 81: 1068, 168: 1067, 189: 1067, 87: 1066, 252: 1066, 3: 1062, 39: 1060, 33: 1060, 213: 1057, 12: 1052, 177: 1052, 243: 1049, 156: 1048, 63: 1045, 132: 1044, 93: 1042, 84: 1036, 36: 1036, 99: 1027, 6: 1023, 186: 1015, 207: 977, 185: 813, 145: 812, 155: 789, 125: 785, 205: 780, 175: 779, 5: 779, 250: 775, 230: 775, 80: 763, 25: 759, 115: 759, 65: 753, 130: 753, 235: 753, 220: 752, 20: 750, 110: 749, 40: 748, 70: 746, 55: 741, 95: 739, 140: 737, 245: 735, 160: 734, 100: 733, 35: 723, 10: 723, 215: 720, 200: 713, 190: 701, 50: 683, 238: 502, 34: 480, 221: 475, 136: 468, 68: 460, 119: 447, 17: 444, 187: 443, 107: 408, 146: 397, 64: 395, 83: 395, 122: 395, 181: 394, 218: 392, 163: 392, 178: 392, 59: 390, 208: 389, 241: 388, 247: 388, 97: 388, 31: 387, 166: 385, 184: 385, 191: 384, 103: 382, 88: 381, 58: 380, 124: 380, 16: 379, 92: 377, 26: 377, 206: 376, 254: 375, 193: 375, 22: 375, 152: 375, 38: 374, 199: 374, 154: 374, 23: 373, 196: 373, 131: 373, 236: 373, 223: 373, 73: 373, 121: 373, 112: 372, 89: 372, 79: 372, 239: 372, 11: 372, 173: 371, 116: 370, 244: 370, 86: 369, 179: 369, 2: 369, 13: 368, 233: 367, 167: 367, 142: 366, 172: 366, 127: 365, 37: 365, 209: 364, 217: 363, 67: 363, 194: 363, 43: 362, 77: 362, 188: 361, 242: 361, 226: 360, 109: 360, 4: 360, 137: 360, 61: 360, 29: 360, 134: 359, 32: 359, 128: 359, 224: 359, 143: 359, 101: 358, 52: 358, 203: 358, 71: 357, 8: 357, 202: 356, 182: 356, 118: 354, 211: 354, 113: 354, 232: 354, 151: 353, 56: 353, 74: 353, 14: 353, 46: 352, 197: 352, 98: 352, 104: 351, 1: 351, 106: 351, 229: 351, 139: 350, 164: 350, 44: 348, 28: 348, 158: 347, 47: 346, 251: 346, 62: 345, 169: 345, 41: 345, 227: 345, 19: 345, 91: 345, 161: 344, 76: 343, 133: 341, 149: 340, 82: 340, 176: 339, 214: 338, 157: 338, 7: 337, 148: 337, 253: 331, 94: 331, 248: 330, 212: 329, 49: 322, 53: 318
}

def score(c1, c2):
    """Calculates the combined score of two coefficients based on the fingerprint map."""
    return fingerprint.get(c1, 0) + fingerprint.get(c2, 0)

# === Phase 2: Core Logic (Math and Data Conversion) ===

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
    """Correctly decodes a custom Bitaps share into its index and data bytes."""
    codes = {w: c for c, w in enumerate(wordlist)}
    words = mnemonic_phrase.split()
    entropy_int = sum(codes[w] << (11 * (len(words) - 1 - i)) for i, w in enumerate(words))
    
    chk_sum_bit_len = len(words) * 11 % 32
    share_index = entropy_int & ((1 << chk_sum_bit_len) - 1)
    
    entropy_int_for_data = entropy_int >> chk_sum_bit_len
    share_data_bytes = entropy_int_for_data.to_bytes(16, byteorder="big")
    
    return share_index, share_data_bytes

def load_bip39_wordlist():
    """Loads the BIP39 wordlist from a local file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    wordlist_path = os.path.join(script_dir, "english.txt")
    with open(wordlist_path, "r") as f:
        return [line.strip() for line in f.readlines()]

# === Phase 3: The Attack Script ===

def run_second_word_search():
    """Finds the highest-scoring second word for each first-word candidate."""
    wordlist = load_bip39_wordlist()

    share_A_mnemonic = "session cigar grape merry useful churn fatal thought very any arm unaware"
    share_B_mnemonic = "clock fresh security field caution effort gorilla speed plastic common tomato echo"

    # Correctly decode the shares once at the beginning
    x1, y1_bytes = decode_bitaps_share(share_A_mnemonic, wordlist)
    x2, y2_bytes = decode_bitaps_share(share_B_mnemonic, wordlist)
    y1_byte2 = y1_bytes[1] # Target the second byte
    y2_byte2 = y2_bytes[1]

    first_word_candidates = [
        "enrich", "enroll", "ensure", "enter", "entire", "entry", "envelope", "episode", "seek", "segment", "select", "sell", "seminar", "senior", "sense", "sentence", "animal", "ankle", "announce", "annual", "another", "answer", "antenna", "antique", "cactus", "cage", "cake", "call", "calm", "camera", "camp", "can", "evoke", "evolve", "exact", "example", "excess", "exchange", "excite", "exclude", "mention", "menu", "mercy", "merge", "merit", "merry", "mesh", "message", "narrow", "nasty", "nation", "nature", "near", "neck", "need", "negative", "safe", "sail", "salad", "salmon", "salon", "salt", "salute", "same", "trend", "trial", "tribe", "trick", "trigger", "trim", "trip", "trophy", "vessel", "veteran", "viable", "vibrant", "vicious", "victory", "video", "view"
    ]

    print("🔍 Starting second-word search...\n")
    two_word_paths = []

    for first_word in first_word_candidates:
        best_score = 0
        best_second_word = None

        for second_word in wordlist:
            # Create the full 12-word guess to correctly calculate the second byte
            guess_mnemonic = f"{first_word} {second_word} " + "abandon " * 10
            
            try:
                x3, guess_bytes = decode_bitaps_share(guess_mnemonic.strip(), wordlist)
                y3_byte2 = guess_bytes[1] # Target the second byte of the guess
            except (KeyError, ValueError):
                continue

            points = [(x1, y1_byte2), (x2, y2_byte2), (x3, y3_byte2)]

            try:
                S0, c1, c2 = get_coefficients_from_points(points)
            except ZeroDivisionError:
                continue

            # The "Loaded Dice" Filter
            if c1 == 255 or c2 == 255:
                continue

            # Score the path based on the fingerprint
            path_score = score(c1, c2)
            if path_score > best_score:
                best_score = path_score
                best_second_word = second_word
        
        if best_second_word:
            two_word_paths.append(((first_word, best_second_word), best_score))

    # Sort the final paths by score to find the most probable one
    two_word_paths.sort(key=lambda item: item[1], reverse=True)

    print("\n🎯 Phase 2 complete. Top 5 highest-scoring paths:")
    for path, path_score in two_word_paths:
        print(f"  Path: {' '.join(path)} → score={path_score}")

if __name__ == "__main__":
    run_second_word_search()