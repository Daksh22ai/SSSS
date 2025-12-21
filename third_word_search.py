# === third_word_search.py ===
import ast

# === Paste your fingerprint dictionary here ===
fingerprint = {
    0: 4896, 180: 2522, 195: 2503, 60: 2493, 240: 2478, 45: 2468, 225: 2463, 120: 2456, 105: 2449, 15: 2444, 210: 2427, 75: 2422, 150: 2419, 135: 2414, 90: 2396, 165: 2381, 30: 2381, 170: 2256, 85: 2191, 204: 1675, 51: 1643, 102: 1633, 153: 1606, 132: 1070, 99: 1064, 96: 1059, 252: 1053, 126: 1052, 9: 1050, 162: 1050, 129: 1045, 237: 1039, 222: 1032, 183: 1032, 21: 1029, 84: 1028, 48: 1024, 198: 1023, 147: 1023, 141: 1023, 138: 1020, 231: 1019, 18: 1019, 171: 1017, 201: 1014, 24: 1014, 159: 1013, 114: 1012, 87: 1012, 117: 1012, 168: 1010, 57: 1009, 123: 1009, 63: 1009, 156: 1007, 207: 1007, 228: 1005, 234: 1005, 192: 1003, 36: 1001, 108: 997, 213: 997, 144: 996, 39: 996, 186: 994, 42: 992, 12: 991, 249: 990, 93: 989, 243: 989, 174: 988, 189: 986, 27: 986, 111: 984, 219: 982, 66: 982, 81: 978, 6: 977, 3: 970, 177: 970, 246: 964, 72: 959, 33: 953, 78: 948, 216: 939, 140: 931, 69: 927, 155: 927, 54: 913, 5: 908, 250: 908, 130: 905, 245: 904, 65: 901, 95: 900, 20: 897, 185: 891, 160: 890, 230: 888, 235: 888, 55: 884, 220: 879, 205: 876, 25: 874, 70: 874, 115: 871, 10: 869, 200: 869, 190: 867, 175: 864, 100: 862, 80: 861, 35: 860, 40: 857, 119: 842, 187: 833, 215: 829, 221: 828, 136: 827, 125: 825, 110: 821, 68: 819, 50: 815, 238: 814, 145: 813, 17: 811, 34: 783, 32: 414, 116: 403, 212: 401, 1: 399, 79: 398, 206: 393, 52: 391, 178: 390, 152: 388, 91: 388, 151: 387, 229: 387, 197: 385, 211: 384, 209: 384, 241: 382, 193: 382, 203: 381, 167: 380, 61: 379, 169: 379, 86: 379, 184: 378, 67: 377, 92: 377, 173: 376, 191: 376, 236: 375, 122: 374, 82: 374, 176: 373, 26: 373, 106: 373, 29: 372, 242: 372, 143: 371, 101: 371, 4: 370, 94: 370, 83: 369, 112: 369, 128: 369, 124: 368, 202: 368, 107: 368, 161: 367, 43: 367, 28: 367, 89: 367, 154: 366, 181: 366, 58: 366, 218: 366, 163: 364, 37: 364, 182: 364, 53: 363, 97: 362, 47: 361, 8: 361, 137: 361, 22: 361, 41: 360, 199: 360, 223: 360, 157: 360, 142: 359, 188: 359, 158: 359, 73: 359, 244: 359, 224: 358, 113: 358, 16: 357, 139: 357, 104: 357, 56: 357, 247: 357, 44: 357, 71: 357, 214: 356, 11: 356, 64: 355, 253: 354, 98: 353, 149: 352, 133: 352, 254: 350, 103: 349, 232: 348, 23: 348, 49: 347, 59: 346, 88: 346, 46: 346, 226: 345, 194: 345, 146: 344, 14: 344, 74: 344, 179: 344, 121: 343, 148: 343, 2: 343, 31: 343, 251: 343, 109: 342, 118: 342, 19: 342, 164: 342, 77: 340, 127: 340, 227: 339, 233: 339, 166: 339, 196: 337, 62: 335, 131: 334, 13: 333, 208: 333, 134: 332, 217: 332, 76: 331, 7: 330, 239: 330, 172: 327, 248: 326, 38: 325      
}

def score(c1, c2):
    return fingerprint.get(c1, 0) + fingerprint.get(c2, 0)

# === GF(2^8) setup ===
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

def gf_add(a, b): return a ^ b
def gf_mul(a, b): return 0 if a == 0 or b == 0 else EXP_TABLE[(LOG_TABLE[a] + LOG_TABLE[b]) % 255]
def gf_div(a, b): return 0 if a == 0 else EXP_TABLE[(LOG_TABLE[a] - LOG_TABLE[b]) % 255]

def interpolate(points, x=0):
    result = 0
    for j in range(len(points)):
        xj, yj = points[j]
        num, den = 1, 1
        for m in range(len(points)):
            if m == j: continue
            xm = points[m][0]
            num = gf_mul(num, gf_add(x, xm))
            den = gf_mul(den, gf_add(xj, xm))
        term = gf_mul(yj, gf_div(num, den))
        result = gf_add(result, term)
    return result

def get_coefficients_from_points(points):
    S0 = interpolate(points, x=0)
    f1 = interpolate(points, x=1)
    c1 = gf_add(f1, S0)
    f2 = interpolate(points, x=2)
    temp = gf_add(f2, S0)
    temp = gf_add(temp, gf_mul(2, c1))
    c2 = gf_div(temp, 4)
    return S0, c1, c2

def words_to_bytes(mnemonic_str, wordlist):
    word_to_index = {word: idx for idx, word in enumerate(wordlist)}
    words = mnemonic_str.strip().split()
    binary_chunks = [format(word_to_index[word], '011b') for word in words]
    full_binary_str = "".join(binary_chunks)
    data_binary_str = full_binary_str[:128]
    return int(data_binary_str, 2).to_bytes(16, 'big')

def load_bip39_wordlist():
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, "english.txt")
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()]

# === Fixed shares ===
share_A = "session cigar grape merry useful churn fatal thought very any arm unaware"
share_B = "clock fresh security field caution effort gorilla speed plastic common tomato echo"
x1, x2, x3 = 1, 2, 3

# === Load wordlist and byte 3 ===
wordlist = load_bip39_wordlist()
y1_byte3 = words_to_bytes(share_A, wordlist)[2]
y2_byte3 = words_to_bytes(share_B, wordlist)[2]

# === Paste your two-word pairs here ===
two_word_pairs = [
  ('audit', 'quote'), ('august', 'marine'), ('aunt', 'mosquito'), ('author', 'marine'), ('auto', 'useless'), ('autumn', 'avoid'), ('average', 'source'), ('avocado', 'mosquito'), ('elite', 'quote'), ('else', 'marine'), ('embark', 'mosquito'), ('embody', 'marine'), ('embrace', 'useless'), ('emerge', 'avoid'), ('emotion', 'source'), ('employ', 'mosquito'), ('length', 'quote'), ('lens', 'marine'), ('leopard', 'mosquito'), ('lesson', 'marine'), ('letter', 'useless'), ('level', 'avoid'), ('liar', 'source'), ('liberty', 'mosquito'), ('orchard', 'quote'), ('order', 'marine'), ('ordinary', 'mosquito'), ('organ', 'marine'), ('orient', 'useless'), ('original', 'avoid'), ('orphan', 'source'), ('ostrich', 'mosquito'), ('reduce', 'quote'), ('reflect', 'marine'), ('reform', 'mosquito'), ('refuse', 'marine'), ('region', 'useless'), ('regret', 'avoid'), ('regular', 'source'), ('reject', 'mosquito'), ('slot', 'quote'), ('slow', 'marine'), ('slush', 'mosquito'), ('small', 'marine'), ('smart', 'useless'), ('smile', 'avoid'), ('smoke', 'source'), ('smooth', 'mosquito'), ('unfair', 'quote'), ('unfold', 'marine'), ('unhappy', 'mosquito'), ('uniform', 'marine'), ('unique', 'useless'), ('unit', 'avoid'), ('universe', 'source'), ('unknown', 'mosquito'), ('vital', 'quote'), ('vivid', 'marine'), ('vocal', 'mosquito'), ('voice', 'marine'), ('void', 'useless'), ('volcano', 'avoid'), ('volume', 'source'), ('vote', 'mosquito')
]

print("🔍 Starting third-word search...\n")
three_word_paths = []

for first, second in two_word_pairs:
    best_score = 0
    best_third = None

    for third in wordlist:
        guess_mnemonic = f"{first} {second} {third} " + "abandon " * 9
        try:
            guess_bytes = words_to_bytes(guess_mnemonic.strip(), wordlist)
        except KeyError:
            continue

        # --- New Cumulative Score Logic ---
        total_path_score = 0
        is_path_valid = True

        # Check each byte position from 1 to 3
        for byte_index in range(3):
            # Get the correct byte from each share
            y1_byte = words_to_bytes(share_A, wordlist)[byte_index]
            y2_byte = words_to_bytes(share_B, wordlist)[byte_index]
            y3_byte = guess_bytes[byte_index]
            
            points = [(x1, y1_byte), (x2, y2_byte), (x3, y3_byte)]
            
            try:
                S0, c1, c2 = get_coefficients_from_points(points)
            except ZeroDivisionError:
                is_path_valid = False
                break # This path is mathematically impossible for this byte

            # The flaw check for the current byte
            if c1 == 255 or c2 == 255:
                is_path_valid = False
                break # This path is invalid, exit the byte check loop

            # Add the score for the current byte to the total
            total_path_score += score(c1, c2)

        # Only proceed if all three bytes were valid
        if not is_path_valid:
            continue # Move to the next `third` word guess

        # This is the old `path_score` variable, now it's the total
        path_score = total_path_score
        # --- End of New Logic ---

        if path_score > best_score:
            best_score = path_score
            best_third = third

    if best_third:
        # Store the path and its total score as a tuple
        path_info = (best_score, (first, second, best_third))
        three_word_paths.append(path_info)
if three_word_paths:
    # Sort the list by score in descending order
    ranked_paths = sorted(three_word_paths, key=lambda item: item[0], reverse=True)

    print("✅ Top 5 highest-scoring three-word paths found:")
    for path_score, path_words in ranked_paths:
        print(f"  Path: {' '.join(path_words)} → score={path_score}")

print("\n🎯 Phase 3 complete. Review valid three-word paths above.")