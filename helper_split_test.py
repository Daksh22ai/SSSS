import os
from old_shamir import split_secret
from bip_utils import Bip39MnemonicValidator, Bip39MnemonicDecoder, Bip39Languages

# ---------- Config ----------
WORDLIST_FILE = "english.txt"  # must be in the same folder
THRESHOLD = 3
TOTAL_SHARES = 5
INDEX_BITS = 4                  # so x is in 1..15, matching your combined code
NUM_WORDS_PER_SHARE = 12        # 12-word Bitaps-style share
# -----------------------------


def load_bip39_wordlist(path=WORDLIST_FILE):
    here = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(here, path)
    with open(full_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()]


def encode_bitaps_share(x, data, wordlist, num_words=NUM_WORDS_PER_SHARE):
    """
    Inverse of your decode_bitaps_share() for 16-byte shares.

    x: 1..15 (stored in the low 4 bits of the packed data)
    data: 16-byte share payload (bytes)
    wordlist: BIP39 English wordlist (2048 words)
    """
    if len(data) != 16:
        raise ValueError("encode_bitaps_share expects 16 bytes of data")

    entropy = int.from_bytes(data, "big")      # 128 bits
    total_bits = num_words * 11               # 12 * 11 = 132
    chk_bits = total_bits - 128               # 4 checksum bits

    if chk_bits <= 0:
        raise ValueError("num_words too small for 16-byte data")
    if x >= (1 << chk_bits):
        raise ValueError(f"x={x} too large for {chk_bits} checksum bits")

    # Pack entropy and x into one integer (same way decode_bitaps_share unpacks it)
    bits = (entropy << chk_bits) | x

    indexes = []
    for i in range(num_words):
        shift = 11 * (num_words - 1 - i)
        idx = (bits >> shift) & ((1 << 11) - 1)
        indexes.append(idx)

    return " ".join(wordlist[i] for i in indexes)


def main():
    # 1) Ask user for a 12-word BIP39 mnemonic
    print("Enter a valid 12-word BIP39 mnemonic (English):")
    mnemonic = input("> ").strip()

    # 2) Validate mnemonic
    if not Bip39MnemonicValidator().IsValid(mnemonic):
        print("❌ The mnemonic is not a valid BIP39 phrase.")
        return

    # 3) Decode mnemonic to 16-byte entropy
    entropy = Bip39MnemonicDecoder(Bip39Languages.ENGLISH).Decode(mnemonic)
    if len(entropy) != 16:
        print(f"❌ Expected 16-byte entropy for 12-word mnemonic, got {len(entropy)} bytes.")
        return

    print("\n✅ Mnemonic is valid.")
    print(f"Entropy (hex): {entropy.hex()}")

    # 4) Split secret into 3-of-5 shares using the flawed old_shamir logic
    #    Use index_bits=4 so share indices are 1..15 (compatible with combined code)
    shares = split_secret(THRESHOLD, TOTAL_SHARES, entropy, index_bits=INDEX_BITS)

    # 5) Load BIP39 wordlist (must match what your combined code uses)
    wordlist = load_bip39_wordlist()

    # 6) Convert each (x, share_bytes) to a 12-word share mnemonic
    share_mnemonics = {}
    print(f"\nCreated {TOTAL_SHARES} shares (threshold = {THRESHOLD}):\n")
    for x, share_bytes in sorted(shares.items()):
        phrase = encode_bitaps_share(x, share_bytes, wordlist)
        share_mnemonics[x] = phrase
        print(f"Share index x={x:2d}")
        print(f"  Share bytes (hex): {share_bytes.hex()}")
        print(f"  Share mnemonic   : {phrase}\n")

    # 7) Pick two shares to feed into the combined code (e.g., the first two indices)
    sorted_indices = sorted(share_mnemonics.keys())
    shareA_x = sorted_indices[0]
    shareB_x = sorted_indices[1]
    share_A = share_mnemonics[shareA_x]
    share_B = share_mnemonics[shareB_x]

    print("======================================")
    print("Use these two in your combined script:")
    print("======================================\n")
    print(f"share_A (x={shareA_x}):")
    print(share_A)
    print("\nshare_B (x={shareB_x}):")
    print(share_B)
    print("\n(Any of the other 3 share mnemonics could be the true 3rd share.)")


if __name__ == "__main__":
    main()
