from mnemonic import Mnemonic
from functools import reduce

# Initialize BIP39 wordlist
mnemo = Mnemonic("english")
wordlist = mnemo.wordlist
word_to_index = {word: idx for idx, word in enumerate(wordlist)}

def words_to_bytes(words):
    """Convert 12 mnemonic words to 15 bytes using 10-bit encoding"""
    indices = [word_to_index[word] for word in words]
    binary = ''.join(f"{i:010b}" for i in indices)
    binary = binary[:120].ljust(120, '0')  # Ensure exactly 120 bits
    return int(binary, 2).to_bytes(15, byteorder='big')

def modinv(a, p):
    """Modular inverse using extended Euclidean algorithm"""
    return pow(a, -1, p)

def lagrange_interpolate(x, x_s, y_s, prime=257):
    """Lagrange interpolation over GF(257) for each byte"""
    def PI(vals): return reduce(lambda a, b: a * b % prime, vals, 1)
    result = []
    for i in range(len(y_s[0])):
        total = 0
        for j in range(len(x_s)):
            xi, yi = x_s[j], y_s[j][i]
            others = [x_s[m] for m in range(len(x_s)) if m != j]
            num = PI([x - xj for xj in others])
            den = PI([xi - xj for xj in others])
            total += yi * num * modinv(den, prime)
        result.append(total % prime)
    return bytes(result)

def restore_mnemonic(shares):
    """Restore original mnemonic from 3-of-5 Bitaps-style shares"""
    x_vals = [i + 1 for i in range(len(shares))]  # Dummy indices
    y_vals = []

    for share in shares:
        words = share.strip().split()
        if len(words) != 12:
            raise ValueError("Each share must have exactly 12 words")
        y_vals.append(list(words_to_bytes(words)))

    # Pad each share to 32 bytes (Bitaps uses 32-byte secret)
    for i in range(len(y_vals)):
        y_vals[i] += [0] * (32 - len(y_vals[i]))

    secret_bytes = lagrange_interpolate(0, x_vals, y_vals)
    return mnemo.to_mnemonic(secret_bytes)

# 🔐 Paste your 3-of-5 shares below
shares = [
    "session cigar grape merry useful churn fatal thought very any arm unaware",
    "clock fresh security field caution effort gorilla speed plastic common tomato echo",
    "clog rice coconut vital clean kit buzz away monitor stadium differ ability"
]

mnemonic = restore_mnemonic(shares)
print("✅ Restored Mnemonic:", mnemonic)