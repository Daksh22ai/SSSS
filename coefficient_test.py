from mnemonic import Mnemonic
from collections import Counter

# GF(2^8) setup
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
    if a == 0 or b == 0:
        return 0
    return EXP_TABLE[(LOG_TABLE[a] + LOG_TABLE[b]) % 255]

def gf_div(a, b):
    if b == 0:
        raise ZeroDivisionError()
    if a == 0:
        return 0
    return gf_mul(a, EXP_TABLE[(-LOG_TABLE[b]) % 255])

def gf_add(a, b):
    return a ^ b

def interpolate(points, x=0):
    result = 0
    for j in range(len(points)):
        xj, yj = points[j]
        num, den = 1, 1
        for m in range(len(points)):
            if m == j:
                continue
            xm = points[m][0]
            num = gf_mul(num, gf_add(x, xm))
            den = gf_mul(den, gf_add(xj, xm))
        term = gf_mul(yj, gf_div(num, den))
        result = gf_add(result, term)
    return result

# BIP39 wordlist
mnemo = Mnemonic("english")
wordlist = mnemo.wordlist
word_to_index = {word: idx for idx, word in enumerate(wordlist)}

# 🔐 Fixed first two words
fixed_words = ["session", "clock"]
y1 = word_to_index[fixed_words[0]] % 256
y2 = word_to_index[fixed_words[1]] % 256

# 🧮 Track coefficient frequencies
c1_counter = Counter()
c2_counter = Counter()

for third_word in wordlist:
    y3 = word_to_index[third_word] % 256
    points = [(1, y1), (2, y2), (3, y3)]

    # Step 1: S0 = f(0)
    S0 = interpolate(points, x=0)

    # Step 2: f(1) = c1 + S0 → c1 = f(1) + S0
    f1 = interpolate(points, x=1)
    c1 = gf_add(f1, S0)

    # Step 3: f(2) = 4c2 + 2c1 + S0 → c2 = (f(2) + S0 + 2c1) / 4
    f2 = interpolate(points, x=2)
    temp = gf_add(f2, S0)
    temp = gf_add(temp, gf_mul(2, c1))
    c2 = gf_div(temp, 4)

    c1_counter[c1] += 1
    c2_counter[c2] += 1

# ✅ Summary
def print_summary(name, counter):
    total = sum(counter.values())
    count_255 = counter[255]
    count_not_255 = total - count_255
    print(f"\n🔍 {name} Coefficient Analysis")
    print(f"Total tested: {total}")
    print(f"✅ {name} = 255: {count_255} times")
    print(f"❌ {name} ≠ 255: {count_not_255} times")
    print(f"\n📊 {name} Frequencies (descending):")
    for value, freq in counter.most_common():
        print(f"  Value {value}: {freq} times")

print_summary("c1", c1_counter)
print_summary("c2", c2_counter)