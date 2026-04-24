# My Journey Into Shamir's Secret Sharing: A Research Narrative

**A personal account of 1.5 years spent attempting to break a real-world cryptographic challenge, from first principles to final conclusions.**

---

## Preface

I am writing this document because I believe the journey matters as much as the destination. Over the course of roughly one and a half years, I attempted to break a real cryptographic challenge that offered 1 BTC as a reward. I did not win the reward. But I learned more about applied cryptography, implementation security, and the limits of statistical attacks than I could have learned from any textbook. This document is the honest, complete account of everything I thought, tried, discovered, got wrong, corrected, and ultimately concluded. I am writing it in the hope that someone else can build on what I found, or at least avoid the roads I spent months on before realizing they were dead ends.

---

## Chapter 1: How It Started

I am not a cryptographer by training. I have an intermediate understanding of Python and a curiosity about security. When I first came across the Bitaps mnemonic challenge at `https://btc.bitaps.com/mnemonic/challenge`, my reaction was not "I will definitely solve this." My reaction was closer to "this looks like something worth understanding."

The challenge was simple to describe: a 12-word Bitcoin seed phrase had been split into 5 shares using Shamir's Secret Sharing Scheme. The threshold was 3 shares required to recover the original secret. Two of those five shares were posted publicly on the challenge page. The Bitcoin address holding 1 BTC was also published. The invitation was open: if you could find the vulnerability in their implementation and recover the original seed phrase, the funds were yours.

What drew me in was not just the money. It was the explicit acknowledgment from Bitaps that their implementation had a bug. They were not claiming their code was perfect. The entire premise of the challenge was that their specific implementation of Shamir's Secret Sharing had a flaw, and the challenge was to find and exploit it. That made it feel less like hacking and more like a puzzle with an explicitly published invitation.

Before I could do anything useful, I needed to actually understand two things: how Bitcoin seed phrases work, and how Shamir's Secret Sharing works. I had a vague sense of both, but vague is not good enough when you are trying to exploit a cryptographic implementation.

---

## Chapter 2: Understanding the Foundation

### BIP39 Seed Phrases

A 12-word seed phrase is not magic. It is a human-readable encoding of a random number.

The process works like this. A system generates 128 bits of entropy, which is just a random 128-bit number. It then computes a checksum by taking the SHA-256 hash of those 128 bits and keeping the first 4 bits of the result. Those 4 checksum bits are appended to the 128 entropy bits, giving a total of 132 bits. That 132-bit string is then divided into 12 groups of 11 bits each. Each 11-bit number indexes into a standardized list of 2048 words. The result is 12 words.

This means the total number of valid 12-word seed phrases is exactly 2^128, because the checksum is derived from the entropy, not chosen independently. Each unique 128-bit number maps to one unique valid phrase.

The number 2^128 deserves to be written out at least once: 340,282,366,920,938,463,463,374,607,431,768,211,456. That is roughly the estimated number of atoms in the observable universe. Brute-forcing the space of valid seed phrases directly is not a computation that any hardware combination on Earth could complete in any reasonable time. This was my first important calibration: direct brute force is not a strategy.

### Shamir's Secret Sharing

Shamir's Secret Sharing is based on a beautiful piece of mathematics. The core insight is polynomial interpolation: it takes exactly k points to uniquely define a polynomial of degree k-1.

A line is a degree-1 polynomial. It takes exactly 2 points to define a unique line. A parabola is a degree-2 polynomial. It takes exactly 3 points to define a unique parabola. If you have only 2 points, an infinite number of parabolas pass through them, so you have no information about which one is the correct one.

The scheme works by encoding the secret as the y-intercept of a polynomial, that is, as the value of the polynomial at x=0. For a (3, 5) scheme with threshold 3 and 5 total shares, you construct a degree-2 polynomial where the constant term (the value at x=0) equals the secret. The two other coefficients of the polynomial are chosen randomly. You then evaluate this polynomial at 5 different x-values and give each result to a different person. Each (x, f(x)) pair is one share.

To recover the secret, any 3 shareholders bring their points together. With 3 points, Lagrange interpolation recovely the unique degree-2 polynomial that passes through all three. Evaluating that polynomial at x=0 gives back the original secret.

The security guarantee is information-theoretic: with fewer than 3 points, an adversary learns nothing about the secret. Every possible secret is equally consistent with any 2 points, because infinitely many parabolas pass through any 2 given points.

This matters deeply: Shamir's Secret Sharing is not computationally secure; it is information-theoretically secure. No amount of computing power helps you if you have fewer than threshold shares. The only way to break the scheme is to find a flaw in the implementation, not in the mathematics.

### Connecting the Two

The bridge between a seed phrase and Shamir's scheme is straightforward. The 128-bit entropy that underlies the seed phrase is treated as 16 bytes of raw binary data. Those 16 bytes are the secret that gets fed into Shamir's split function. Each share produced by the split function is also 16 bytes of raw data. To make shares user-friendly for backup purposes, those 16 bytes are encoded back into a 12-word mnemonic phrase using the same BIP39 encoding process. The result is that every share looks exactly like a valid seed phrase to the naked eye, even though it does not contain the original secret.

Once I understood this clearly, I understood the structure of the attack. The challenge had published two 12-word phrases. These are not halves of the original secret. They are two evaluated points on a degree-2 polynomial. I needed to find the third point. With the third point and the two public points, I could run Lagrange interpolation at x=0 and recover the original seed.

The question was: how do you find the third point when there are 2^128 possible secrets, and therefore 2^128 possible polynomials, and therefore astronomically many possible third points?

The answer, I hoped, was somewhere in the bug.

---

## Chapter 3: Finding the Vulnerability

### The Wrong Paths First

My initial attempts at understanding what was exploitable were not efficient. Before I understood the technical details, I tried various approaches that turned out to be completely irrelevant. I looked for patterns in the words of the two public shares themselves, comparing them character by character, looking for Caesar ciphers, letter frequencies, and other simple ciphers. This produced nothing, because the shares are not simple transformations of the secret. They are outputs of Galois field arithmetic applied to a random polynomial.

I also considered whether the x-indices themselves might encode useful information. In a standard Shamir implementation, share indices are just random integers in a valid range. I did not yet know that Bitaps had a custom way of encoding these indices into the mnemonic, so this line of thinking stalled quickly.

The correct path came from reading the challenge page more carefully and following its links, specifically the link to GitHub Issue #23 in the pybtc repository.

### GitHub Issue #23: The Smoking Gun

Issue #23 in the pybtc repository, titled something to the effect of "generation of polynomial coefficients in Shamir's secret sharing is not truly random," described exactly the kind of vulnerability the challenge was hinting at. A security researcher had identified that the old version of the `split_secret` function generated polynomial coefficients using a fundamentally broken formula.

Here is the code from the old version, which I will call `old_shamir.py`:

```python
for b in secret:
    q = [b]
    for i in range(threshold - 1):
        a = random.SystemRandom().randint(0, 255)
        i = int((time.time() % 0.0001) * 1000000) + 1
        q.append((a * i) % 255)
```

Notice that inside the inner loop, the variable `i` is being overwritten. The loop counter `i` that was supposed to iterate over `range(threshold - 1)` is replaced by a time-derived value. So the loop counter is destroyed, but more importantly, the coefficient is computed as `(a * i) % 255` where `i` comes from the system clock.

Let me explain what `i` actually is. `time.time()` returns seconds since the Unix epoch as a float. `time.time() % 0.0001` keeps only the fractional part within a 100-microsecond window, giving a value in the range [0, 0.0001). Multiplying by 1,000,000 scales this to [0, 100), and `int()` truncates to an integer in {0, 1, ..., 99}. Adding 1 gives `i` a value in {1, 2, ..., 100}.

So `i_val` is always an integer between 1 and 100. This is the crux of the flaw.

The coefficient is then computed as `(a * i_val) % 255`. Here `a` is a random integer in {0, ..., 255}. But because the modulus is 255 (not 256), and because `a` can be 0, and because `(a * i_val)` is ordinary integer multiplication before the modulus, the result `coeff = (a * i_val) % 255` can never equal 255.

Why? For any value of `a` and `i_val`, `(a * i_val)` can be congruent to 0 mod 255 (which gives coeff=0), or to any value from 1 to 254, but 255 itself would require `a * i_val = 255k` for some integer k, and `(255k) % 255 = 0`. So the only way to get `coeff = 255` would be if `a * i_val` were 255 more than a multiple of 255, but since 255 is the modulus, that wraps back to 0. The value 255 is structurally impossible.

This is the first weapon: any candidate third share that, when combined with the two known shares, produces a coefficient of 255 anywhere in the reconstruction can be instantly discarded. It is impossible. The original code could never have generated it.

But there is a second, subtler problem. For many values of `i_val`, the map `a -> (a * i_val) % 255` does not produce a uniform distribution over {0, 1, ..., 254}. Specifically, the number of distinct values this map can produce is 255 / gcd(i_val, 255). Since 255 = 3 * 5 * 17, any `i_val` divisible by 3 reduces the output space by a factor of 3, any `i_val` divisible by 5 by a factor of 5, and any `i_val` divisible by 17 by a factor of 17.

More concretely, some coefficient values are generated much more often than others. Values that are multiples of 15 (the product of 3 and 5) tend to be heavily over-represented, because many values of `i_val` in the range 1-100 map many different values of `a` to these outputs. Value 0 is by far the most common because `a=0` always gives `coeff=0` regardless of `i_val`.

This distribution bias is the second weapon: a candidate third share that produces "rare" coefficient values is less likely to be correct than one that produces "common" values.

### Confirming the Challenge Was Generated with the Flawed Code

Before investing significant effort in exploiting this flaw, I needed to confirm that the challenge shares were actually generated with the vulnerable code. The bug was found and fixed in July 2021. If Bitaps had regenerated the challenge shares after the fix, the vulnerability would be irrelevant.

The confirmation came from the Bitcoin blockchain. The wallet address given in the challenge (`bc1qyjwa0tf0en4x09magpuwmt2smpsrlaxwn85lh6`) has a single transaction depositing 1 BTC, and that transaction occurred in June 2020. This is more than a year before the bug fix.

I also verified using the Wayback Machine that the two public shares published on the challenge page in 2020 are identical to the ones published today. The challenge has not been regenerated. The vulnerable code was used.

This gave me high confidence that the attack was in principle viable.

---

## Chapter 4: Understanding the Custom Encoding

Before writing any attack code, I had to understand something that was not obvious: how does Bitaps encode its shares as 12-word mnemonic phrases? This turned out to be different from standard BIP39.

In standard BIP39, a 12-word phrase encodes 128 bits of entropy plus a 4-bit checksum. The checksum is the first 4 bits of the SHA-256 hash of the entropy. It is purely a verification mechanism.

Bitaps repurposes those 4 checksum bits. Instead of using them as a checksum in the traditional sense, they use them to store the share's x-index. The x-index is the "share number," the value at which the polynomial was evaluated to generate this share's data.

This is what the cryptographic community calls "security through obscurity," a design where security depends on an attacker not knowing the format. It is not considered good practice, but it is what was done here. Once I reverse-engineered it from the `bip39_mnemonic.py` file in the pybtc library, I could decode any share into its two components: the x-value (the share index) and the y-values (the 16 data bytes representing the polynomial evaluated at that index).

The decoding function works as follows:

```python
def decode_bitaps_share(mnemonic_phrase, wordlist):
    codes = {w: c for c, w in enumerate(wordlist)}
    words = mnemonic_phrase.split()
    bits = 0
    for w in words:
        bits = (bits << 11) | codes[w]
    total_bits = len(words) * 11   # 132 bits for 12 words
    chk_bits = total_bits % 32     # 132 % 32 = 4 bits
    entropy = bits >> chk_bits     # first 128 bits: the share data
    x = bits & ((1 << chk_bits) - 1)  # last 4 bits: the share index
    data = entropy.to_bytes(16, byteorder="big")
    return x, data
```

When I applied this to the two public shares, I got their x-values. This told me what x-values were already "taken" and constrained the possible values for the hidden third share: it must have an x-value in {1, ..., 15} that is different from the x-values of the two known shares.

I also built the inverse function, `encode_bitaps_share`, which packs an (x, 16-byte-data) pair back into a 12-word mnemonic:

```python
def encode_bitaps_share(x, data, wordlist):
    entropy = int.from_bytes(data, "big")
    bits = (entropy << 4) | x
    indexes = []
    for i in range(12):
        shift = 11 * (11 - i)
        idx = (bits >> shift) & 0x7FF
        indexes.append(idx)
    return " ".join(wordlist[i] for i in indexes)
```

With these two functions working correctly, I could convert freely between the mnemonic representation and the raw (x, bytes) mathematical representation that Shamir's arithmetic operates on.

---

## Chapter 5: The Bit-Level Mapping

Because my attack strategy was to search for the third share one word at a time, I needed to understand precisely which bytes of the 16-byte share data are influenced by which words of the 12-word mnemonic. This is dictated by how BIP39 packs 11-bit word indices into bytes.

The 12 words contribute 12 x 11 = 132 bits. The first 128 bits form the 16 data bytes, and the last 4 bits are the x-index. The packing is MSB-first (most significant bit first). Here is the complete mapping:

Word 1 contributes to Byte 0 (all 8 bits from the word's b10..b3) and Byte 1 (top 3 bits from the word's b2..b0).

Word 2 contributes to Byte 1 (5 bits, b10..b6 of the word) and Byte 2 (6 bits, b5..b0 of the word).

Word 3 contributes to Byte 2 (2 bits), Byte 3 (8 bits), and Byte 4 (1 bit).

Word 4 contributes to Byte 4 (7 bits) and Byte 5 (4 bits).

Word 5 contributes to Byte 5 (4 bits) and Byte 6 (7 bits).

Word 6 contributes to Byte 6 (1 bit), Byte 7 (8 bits), and Byte 8 (2 bits).

Word 7 contributes to Byte 8 (6 bits) and Byte 9 (5 bits).

Word 8 contributes to Byte 9 (3 bits) and Byte 10 (8 bits), with 2 more bits into Byte 11.

Word 9 contributes to Byte 11 (6 bits) and Byte 12 (5 bits).

Word 10 contributes to Byte 12 (3 bits, wait, specifically: 5 bits from b10..b6) and Byte 13 (6 bits from b5..b0).

Word 11 contributes to Byte 13 (2 bits), Byte 14 (8 bits), and Byte 15 (1 bit).

Word 12 contributes to Byte 15 (7 bits, b10..b4), and the last 4 bits (b3..b0) become the x-index, not a data byte.

I verified this mapping carefully using a worked example: the phrase "movie dress dance habit nominee device cage mountain mail volcano super pioneer" decodes to entropy `90E854DD34195E79480C84863EB766D2` in hexadecimal, and I traced each byte back to its constituent word bits to confirm.

This mapping is critical to the search strategy. When I am trying to find Word 1, only Byte 0 is completely determined by Word 1. Byte 1 is jointly determined by Words 1 and 2. This means I should only score Byte 0 when searching for Word 1, because Byte 1's value depends on the unknown Word 2, and using a contaminated byte in the scoring would give wrong results.

The rule I developed is to use only bytes that are fully determined by the words fixed so far. I called this the "prefix-safe" mapping:

```python
WORD_TO_BYTES = {
    1: [0],
    2: [1],
    3: [2, 3],
    4: [4],
    5: [5],
    6: [6, 7],
    7: [8],
    8: [9, 10],
    9: [11],
    10: [12],
    11: [13, 14],
    12: [15],
}
```

This was one of the most consequential corrections I made. Early versions of the search used bytes that were partially determined by future words, which introduced noise into the scoring and corrupted the results.

---

## Chapter 6: Building the Statistical Fingerprint

The fingerprint is the empirical measurement of the flawed RNG's behavior. The idea is to run the flawed coefficient generation code millions of times and record how often each (c1, c2) pair appears. Coefficient pairs that appear frequently were likely to have been generated by the original code. Pairs that never appear are impossible under the flaw and can be used to immediately reject candidates.

My fingerprint generator replicated the exact flawed logic from `old_shamir.py`:

```python
def run_fingerprint_analysis(threshold=3, iterations=100000):
    for _ in range(iterations):
        random_secret = os.urandom(16)
        for b in random_secret:
            coeffs = []
            for _ in range(threshold - 1):
                a = random.SystemRandom().randint(0, 255)
                i_val = int((time.time() % 0.0001) * 1000000) + 1
                coeff = (a * i_val) % 255
                coeffs.append(coeff)
            if len(coeffs) == 2:
                COEFFICIENT_LOG.append(tuple(coeffs))
```

After running this for 100,000 iterations (generating 1,600,000 coefficient pairs), I observed the following:

The value 255 appeared zero times. This confirmed the structural impossibility.

The most common values were multiples of 15 and multiples of 45, reflecting the fact that 255 = 3 x 5 x 17 and many values of `i_val` cause `(a * i_val) % 255` to cluster around these multiples.

The distribution was strongly non-uniform, with the most common individual value (0) appearing roughly 15 times more often than the rarest non-zero values.

I stored the results as a JSON file mapping "(c1,c2)" string keys to their frequency counts. This file grew to about 640KB and contained frequencies for all observed pairs. The total number of distinct pairs observed was far less than the theoretical maximum of 255 x 255 = 65,025, which itself gave me useful information about the structure of the flaw.

I also experimented with an alternative approach: instead of sampling randomly, enumerate all possible combinations deterministically. For each `i_val` in 1..100, and for each `a` in 0..255, compute `c = (a * i_val) % 255`. Count how many times each value of `c` appears across all these combinations. This gives the "universal fingerprint," a purely mathematical characterization of the bias that does not depend on timing or randomness. I built this as `universal_fingerprint.py` and used it as a cross-check against the empirical fingerprint.

---

## Chapter 7: Designing the Attack

With the fingerprint built, the GF(256) math understood, and the encoding format decoded, I had all the pieces. The attack design flowed naturally from these components.

### The Core Scoring Logic

Given two known shares (x1, y1) and (x2, y2) in the form of 16 data bytes each, and a candidate third share (x3, y3), I can reconstruct the polynomial coefficients for each of the 16 bytes. For a degree-2 polynomial over GF(256):

```
f(x) = S0 + c1*x + c2*x^2   (all operations in GF(256))
```

Given three points (x1, y1[b]), (x2, y2[b]), (x3, y3[b]) for byte index b, Lagrange interpolation gives S0 = f(0). From there:

```
s1 = f(1) XOR S0    (equals c1 XOR c2 in GF(256))
s2 = f(2) XOR S0    (equals 2*c1 XOR 4*c2 in GF(256))
c2 = (s2 XOR 2*s1) / 6   (all in GF(256))
c1 = s1 XOR c2
```

This is a formula I debugged carefully. An earlier, incorrect version used `c2 = (f(2) XOR S0 XOR 2*c1) / 4`, which is wrong in GF(256) arithmetic because it effectively computes `c2 * (6/4)` instead of `c2`. The correct derivation solves the 2x2 linear system in GF(256) properly.

I added a sanity check that runs 50 random polynomials before each search run:

```python
for _ in range(50):
    S0 = random.randint(0, 255)
    c1 = random.randint(0, 255)
    c2 = random.randint(0, 255)
    xs = [1, 37, 123]
    pts = [(x, f_val(S0, c1, c2, x)) for x in xs]
    S0r, c1r, c2r = get_coefficients_from_points(pts)
    assert (S0r, c1r, c2r) == (S0, c1, c2)
```

Once this passed reliably, I knew the coefficient recovery math was correct.

### The Beam Search

I chose a beam search over a greedy search for two reasons. A greedy search commits to the single best candidate at each word position, which means that if the correct word is ranked second at any step, the search permanently goes down the wrong path. A beam search maintains a set of the top-W candidates at each step, where W is the beam width. Increasing W increases the chance of keeping the correct path, at the cost of more computation.

The search proceeds word by word, from Word 1 to Word 12. At each step, I try all 2048 BIP39 words as the next candidate, fill in the remaining positions with a placeholder word, decode the resulting phrase to get the candidate's (x3, y3) data, score each target byte using the fingerprint, and add the candidate to the next beam.

The key rules:

At Step 1, I try all x3 values in `allowed_x = {1..15} - {x1, x2}`. This is because the third share's x-value must be in 1..15 (since `index_bits=4` is used for the 4-bit checksum slot) and cannot collide with the two known shares.

From Step 2 onward, x3 is fixed. The x3 value chosen at Step 1 is carried in the beam state as a tuple, and only that value is used for subsequent steps. A real share has one fixed x-value throughout all 16 bytes. Allowing x3 to change between steps would be searching an incoherent space.

The placeholder for unfilled word positions must have a specific property: its lowest 4 bits must equal x3, so that the decoded phrase has the correct x-index. I achieved this by using `index_to_word[x3]` as the placeholder, which is the word at position x3 in the BIP39 list. Its index is x3, so its lowest 4 bits are x3.

At Step 12, the filtering is stricter: the candidate word must satisfy `(word_to_index[w] & 0x0F) == x3`, because the last word's low 4 bits will become the final x-index, and it must match the x3 that has been fixed throughout the search.

The scoring uses log-likelihood:

```python
def build_loglikelihood(fingerprint, floor=1):
    return [math.log(fingerprint.get(v, floor)) for v in range(256)]
```

For each byte and each candidate, `step_score += ll[c1] + ll[c2]`. Cumulative scores are summed across all steps. Any candidate producing c1=255 or c2=255 is immediately rejected.

---

## Chapter 8: The Bugs I Fixed Along the Way

The path from the concept to a working implementation was not straight. Here are the significant mistakes I made and corrected.

### Mistake 1: Hardwired x3 to Zero

In the first version of my multi-word search, I constructed the 12-word guess by filling positions beyond the current prefix with the word "abandon." The word "abandon" has index 0 in the BIP39 list. Its lowest 4 bits are 0. So every candidate phrase I tested had x3=0.

The problem is x3=0 is not a valid share index. The old_shamir.py code uses `random.SystemRandom().randint(1, index_max)`, which never produces 0. So I was computing coefficients using an impossible x3 value and getting garbage scores.

The fix was to explicitly try all valid x3 values at Step 1 and fix x3 throughout the search, as described above.

### Mistake 2: Scoring Bytes Contaminated by Future Words

My first byte mapping included bytes that were partially determined by words not yet fixed. For example, I was scoring Byte 2 at Step 2, but Byte 2 contains bits from both Word 2 and Word 3. When Word 3 was a placeholder, the y3 value for Byte 2 was wrong, and the computed coefficients were meaningless.

The fix was the prefix-safe mapping. At each step, I only scored bytes whose entire content was determined by the words fixed so far.

### Mistake 3: Wrong Coefficient Recovery Formula

My original formula for computing c2 was algebraically incorrect in GF(256). I was computing:
```
c2 = (f(2) XOR S0 XOR 2*c1) / 4
```

But the correct derivation gives:
```
s1 = f(1) XOR S0  
s2 = f(2) XOR S0  
c2 = (s2 XOR (2*s1)) / 6  
c1 = s1 XOR c2  
```

These two formulas give different results in GF(256). The incorrect formula was silently producing wrong c1 and c2 values, which meant the fingerprint-based scoring was comparing garbage against the fingerprint.

### Mistake 4: `_gf256_inverse` Returning an Exception Object Instead of Raising

In one version of my code, the inverse function read:

```python
def _gf256_inverse(a):
    return EXP_TABLE[(-LOG_TABLE[a]) % 255] if a != 0 else ZeroDivisionError()
```

This returned the ZeroDivisionError exception as an object rather than raising it. The division function then operated on this object as if it were a number, causing silent corruption. The fix was:

```python
def _gf256_inverse(a):
    if a == 0:
        raise ZeroDivisionError()
    return EXP_TABLE[(-LOG_TABLE[a]) % 255]
```

### Mistake 5: Rebuilding the Word-to-Index Map on Every Decode Call

The decode function was recomputing `codes = {w: c for c, w in enumerate(wordlist)}` every time it was called. In the inner loop of the beam search, this function is called millions of times. Precomputing `CODES` once at the start of the run and reusing it gave a meaningful speedup. I also added LRU caching for the phrase decoding function to avoid redundant work on repeated phrase evaluations.

---

## Chapter 9: Running the Search

After fixing all these bugs, the beam search ran cleanly and completed all 12 steps. A typical output looked like this:

```
Step 1/12: targeting bytes [0]
Top prefix: seek | score=15.64 | beam=256

Step 2/12: targeting bytes [1]
Top prefix: seek copy | score=31.80 | beam=256

...

Step 12/12: targeting bytes [15]
Top prefix: [word1] [word2] ... [word12] | score=402.20 | beam=256
```

The scores accumulated monotonically and the beam search appeared to be working. Candidates were being pruned, the impossible-255 filter was activating, and the scores were separating.

But something troubled me immediately when I looked at the final output. The top 10 candidates at Step 12 all had identical scores. And the 12th word was just incrementally varying through the vocabulary. This meant that the search had converged on a fixed prefix for words 1-11, but at word 12, all options produced the same score because Byte 15 was carrying very little discriminating information at that point.

More seriously: when I tested the top candidates by entering them into the Bitaps offline tool along with the two public shares, none of the recovered mnemonics produced the target address.

---

## Chapter 10: The Critical Experiment

I was not yet sure whether the search was failing because the correct answer was just outside the beam (a beam-width problem) or because the scoring was not actually preferring the correct answer over wrong ones (a model problem). These two possibilities have very different remedies.

To find out which was the case, I designed a controlled synthetic experiment. I chose a random valid BIP39 seed phrase, used the flawed `old_shamir.py` code to split it into a 3-of-5 scheme with `index_bits=4`, converted two of the five shares to Bitaps-style 12-word mnemonics, and ran my beam search on those two shares. Since I had generated the data myself, I knew all five shares, including the three that were "hidden."

The result was clear and discouraging. The beam search did not find any of the three hidden true shares in its top candidates, even with a beam width of 256. The words the search was proposing were entirely different from the actual correct words.

This was not a "close but missed" result. It was a complete miss. The search was finding shares that score highly according to the fingerprint, but those shares were not the correct ones.

### The Diagnostic

I built a smaller diagnostic script to investigate directly. Given the two known shares and a true third share (from my synthetic test where I knew the ground truth), I computed the (c1, c2) coefficient pairs for all 16 bytes and looked them up in the fingerprint.

The result: all 16 bytes were present in the fingerprint, with frequencies ranging from about 8 to 545. No bytes produced impossible (missing) coefficient pairs.

This was the most important single result of the entire project. It meant:

The fingerprint is not rejecting the true share. The true coefficients are all plausible under the flawed RNG.

But the search is still not finding the true share.

Therefore the problem is not that the fingerprint is wrong. The problem is that the fingerprint is not discriminating enough. The true share "looks" plausible to the fingerprint, but so does a huge number of wrong shares. The fingerprint cannot tell them apart.

---

## Chapter 11: Understanding Why the Attack Fails

After this diagnostic, I spent time thinking carefully about the mathematics. Here is what I concluded.

For any one secret byte `b` and any two known share data values `y1 = f(x1)` and `y2 = f(x2)`, the following holds: for every possible value of b in {0, ..., 255}, there is exactly one (c1, c2) pair in GF(256) that is consistent with the two known equations. The two equations are:

```
b + c1*x1 + c2*x1^2 = y1   (mod GF(256))
b + c1*x2 + c2*x2^2 = y2   (mod GF(256))
```

This is a 2x2 linear system in the unknowns c1 and c2, given a fixed b. It has a unique solution in GF(256) as long as x1 != x2. So knowing y1 and y2 tells you, for every possible secret byte b, exactly which (c1, c2) would have been needed to produce those y values.

The RNG bias then tells you the probability that the original code would have generated that particular (c1, c2). A common pair is more likely; a rare pair is less likely; a pair involving 255 is impossible.

But here is the critical problem: the posterior distribution over b, conditioned on y1 and y2 and the RNG bias, is barely concentrated. The bias affects which (c1, c2) values are common, but the mapping from b to (c1, c2) is essentially random from the attacker's perspective. The most probable b value might be, say, 2x more likely than the least probable, but not 1000x more likely. So the search space for a single byte is barely reduced. Over 16 bytes, the joint entropy of the secret is reduced by perhaps 10-11 bits in total. The search space goes from 2^128 to approximately 2^117. That is still an astronomically large number.

What this means practically is that the guided search will always converge on shares whose coefficients look "globally typical" under the RNG model, but these globally typical coefficients are not uniquely determined by the specific secret in the challenge. Many different secrets and many different wrong shares can produce equally typical-looking coefficient distributions.

The attack correctly models the bias. The bias is real. But the bias is simply not large enough to solve a 128-bit search problem from two data points.

---

## Chapter 12: Other Paths I Considered and Investigated

### The JavaScript Implementation

The challenge was created using the JavaScript-based tool at `bitaps.com/mnemonic`. I examined the JavaScript source code and noticed a subtle difference in the interpolation function. The Python version computes `a = _gf256_sub(x, points[m][0])` in the Lagrange formula, which for `x=0` gives `a = 0 XOR points[m][0] = points[m][0]`. The JavaScript version directly uses `let a = points[m][0]` without the subtraction. Since `0 XOR v = v`, these are equivalent for restoration at x=0. So this particular difference is not exploitable. I did not complete a full audit of every line of the JavaScript tool, which remains an open investigation if one wanted to continue.

### The Time Correlation Between c1 and c2

For each secret byte, the flawed code generates c1 and c2 in back-to-back iterations of the inner loop. These two coefficient computations happen within microseconds of each other. If they happen to use the same `i_val` (that is, if they both land within the same 100-microsecond window), then c1 and c2 are not independent: they are both computed as `(a_1 * i) % 255` and `(a_2 * i) % 255` with the same `i`. This creates a specific kind of correlation.

I attempted to capture this by building a "universal fingerprint" that enumerates all combinations:

```python
for i in range(1, 101):
    for a1 in range(256):
        c1 = (a1 * i) % 255
        for a2 in range(256):
            c2 = (a2 * i) % 255
            pair_counter[f"{c1},{c2}"] += 1
```

This characterizes the distribution of (c1, c2) pairs under the assumption that they share the same `i_val`. The beam search using this fingerprint still failed on the synthetic test, suggesting that even with this correlation modeled, the signal is insufficient.

### The "Word Leakage" Hypothesis

At one point, I ran a test comparing the words in generated shares against the words in the original secret. Over 10,000 trials of splitting random 12-word phrases with the updated (not the flawed) shamir.py code, about 30% of trials showed at least one word from the original secret appearing somewhere in the five generated shares.

I initially thought this might indicate a new bug: the shares leaking the secret's words. After calculation, I realized this is just combinatorics. A 12-word secret and 60 share words (5 shares x 12 words each) drawn from a 2048-word list produce an expected overlap probability of approximately `1 - (1 - 12/2048)^60 = 30%`. This is normal random collision, not a security flaw. The hypothesis was dropped.

### The "Reused Entropy" Hypothesis

In the updated shamir.py (the version fixed after Issue #23), the coefficient generation looks like:

```python
e = generate_entropy(hex=False)
e_i = 0
for b in secret:
    q = [b]
    for i in range(threshold - 1):
        if e_i < len(e):
            a = e[e_i]
            e_i += 1
        else:
            e = generate_entropy(hex=False)
            a = e[0]
            e_i = 1
        q.append(a)
```

The entropy block `e` is generated once and consumed linearly. For a 16-byte secret with threshold 3, the code needs 16 x 2 = 32 coefficient bytes. The `generate_entropy` function returns 32 random bytes. So the block is consumed exactly once without repetition. There is no reuse of the same entropy between different bytes. This is a correct implementation. I investigated this concern and concluded it is not a vulnerability in the post-fix code.

---

## Chapter 13: The Bug Report Angle

Alongside the main challenge, Bitaps offered smaller rewards for discovering genuine bugs in their implementation:

0.1 BTC for bugs that could cause loss of access (inability to recover the secret even with enough shares).

From 0.05 BTC for other significant implementation bugs.

I investigated several potential issues:

The non-standard GF(256) field. The code uses the generator `poly = (poly << 1) ^ poly` which multiplies by `(x + 1)` in GF(256) rather than the standard `poly = poly << 1` which multiplies by `x`. This means the exp/log tables are different from those used by other GF(256) implementations, including the AES S-box tables. A user who tried to recover their secret using a different tool (like the Unix `ssss` command or any other Shamir implementation) would get the wrong answer, because the field arithmetic would be using incompatible tables. This is a genuine interoperability and usability concern. Whether it qualifies as "any bug that can lead to loss of access" depends on interpretation. If the Bitaps software itself is lost, recovery with any other tool would fail.

The coefficient-255 structural impossibility. Any system that generates coefficients with this code can never produce a coefficient of 255. This reduces the effective entropy of the coefficients from 8 bits to slightly less than 8 bits, but more significantly it creates a detectable fingerprint as described throughout this document.

The x-index encoding in checksum bits. The checksum bits, as per BIP39, are supposed to be a derived value for verification. Repurposing them for share index storage means that a share mnemonic will fail standard BIP39 checksum validation. Any tool that validates BIP39 checksums will reject the share mnemonics as invalid. This is also a potential usability and recovery concern.

I did not formally submit any of these as bug reports, partly because Issue #23 already covered the coefficient distribution flaw, and partly because the other issues are design choices rather than clear implementation errors.

---

## Chapter 14: What the Research Produced

Even though I did not recover the secret, the research produced concrete technical artifacts:

A fully functional decoder and encoder for Bitaps' custom share mnemonic format, which was not publicly documented in plain terms anywhere I could find.

A complete GF(256) arithmetic implementation that was independently verified against random test polynomials.

A fingerprint generator that produces the empirical distribution of coefficients from the flawed RNG, stored as a 640KB JSON file.

A beam search engine that cleanly implements the 12-step guided search with proper x3 persistence, prefix-safe byte scoring, and the impossible-value rejection filter.

A Selenium-based automation pipeline that tests candidate shares against the Bitaps offline HTML tool, derives the BIP84 address at `m/84'/0'/0'/0/0`, and compares against the target address.

A synthetic ground-truth testing framework that allows the attack to be evaluated with known correct answers, which was the source of the most important negative result.

A diagnostic tool that directly measures whether a known true share's coefficient pairs appear in the fingerprint.

---

## Chapter 15: The Honest Conclusion

The coefficient bias in the flawed `old_shamir.py` is real. The value 255 is structurally impossible. The distribution of the remaining 255 possible coefficient values is genuinely non-uniform. All of this is correct.

But the size of the bias is not large enough to recover a 128-bit secret from two 128-bit known data points. The information provided by the bias is approximately 10-11 bits distributed across 32 coefficients. The search space for the remaining secret is approximately 2^117. The guided beam search, even when implemented correctly, finds shares that look globally plausible under the biased RNG model, but "globally plausible" is not the same as "the specific plausible share that was generated from this specific secret." Many wrong shares are equally plausible.

The diagnostic experiment confirmed this. The true share's coefficients were all present in the fingerprint with normal frequencies. The fingerprint accepted the true share as plausible. But it also accepted countless wrong shares as equally plausible. The fingerprint cannot discriminate between them.

Shamir's Secret Sharing with threshold 3 and 2 known shares remains information-theoretically secure against this attack. The implementation had a real flaw. The flaw is detectable and measurable. But the flaw does not provide enough information to cross the threshold from "2 shares" to "effectively 3 shares" in terms of reconstructing the secret.

This is, in one sense, a testament to the resilience of Shamir's original scheme. Even when the randomness used to generate the polynomial coefficients is biased and partially predictable, the scheme's information-theoretic security properties are robust enough to withstand this particular level of flaw when only 2 of 3 required shares are known.

---

## Chapter 16: What Could Still Be Tried

I am concluding my work on the coefficient fingerprint path. But I want to be transparent about what I did not fully explore.

The JavaScript implementation used to generate the challenge shares was not fully audited. I examined parts of it and found one apparent difference in the interpolation function that turned out to be equivalent. There may be other differences. The encoding of the x-index, the handling of edge cases, the generation of x-values themselves, and the specific behavior of the JavaScript timing functions versus Python's timing functions could all differ from what I modeled.

The timing model is approximate. I generated fingerprints on modern hardware running Python in 2024-2025. The challenge was generated on Bitaps' server in 2020 running whatever version of software they were using. The distribution of `i_val` values depends on the resolution and behavior of the system clock, which varies across operating systems, Python versions, and hardware. A fingerprint generated in a different environment might have different peak frequencies, which could shift which candidates the beam search prefers.

Any additional structural flaw in the JavaScript tool that was not present in the Python code, and that was not already reported by other researchers, would change the picture entirely.

---

## Closing Thoughts

I started this project with the question: can a real-world cryptographic implementation flaw be practically exploited to break a system that is mathematically secure in principle? After 1.5 years of work, I have a nuanced answer.

The flaw is real and it is exploitable in the sense that it is detectable, measurable, and produces a statistically significant signal. In a different threat model, for example if the threshold were different, or if the attacker had access to additional oracle information, or if the bias were stronger, it would likely be sufficient for an attack.

But for this specific challenge with this specific flaw level and these specific parameters, the bias is not strong enough. The system proved more resilient than I expected.

In cryptography, sometimes you break the system. Sometimes the system is stronger than expected. Both outcomes produce knowledge. I know more now about applied Shamir implementations, GF(256) arithmetic, mnemonic encoding formats, statistical fingerprinting of biased RNGs, and beam search over cryptographic spaces than I would have learned from any other project of equivalent length.

The Bitcoin is still there. The challenge is still open. And the correct answer is still hiding in a parabola that passes through two publicly known points.

---

## Appendix A: The Two Public Challenge Shares

**Share A (x-index embedded in last 4 bits of mnemonic encoding):**
`session cigar grape merry useful churn fatal thought very any arm unaware`

**Share B:**
`clock fresh security field caution effort gorilla speed plastic common tomato echo`

**Target Bitcoin address:** `bc1qyjwa0tf0en4x09magpuwmt2smpsrlaxwn85lh6`

**Derivation path:** `m/84'/0'/0'/0/0` (BIP84 native SegWit, confirmed in challenge description)

---

## Appendix B: The Flawed Coefficient Formula

```python
# From old_shamir.py: the vulnerable coefficient generation
a = random.SystemRandom().randint(0, 255)
i = int((time.time() % 0.0001) * 1000000) + 1  # always in {1,...,100}
coeff = (a * i) % 255                            # never equals 255
```

Properties:
- `coeff` is always in {0, 1, ..., 254}: the value 255 is impossible
- For `i` divisible by d where d divides 255, only `255/d` distinct values appear
- The distribution over {0,...,254} is strongly non-uniform, with multiples of 15, 45, and 85 over-represented
- Both `c1` and `c2` for a given byte are generated in the same 100-microsecond time window, creating potential correlation

---

## Appendix C: The Corrected GF(256) Coefficient Recovery

Given three points (x1,y1), (x2,y2), (x3,y3) on a degree-2 polynomial `f(x) = S0 + c1*x + c2*x^2` over GF(256):

```python
def get_coefficients_from_points(points):
    S0 = interpolate(points, x=0)         # Lagrange interpolation at x=0
    f1 = interpolate(points, x=1)         # evaluate polynomial at x=1
    f2 = interpolate(points, x=2)         # evaluate polynomial at x=2
    s1 = gf_add(f1, S0)                   # = c1 XOR c2
    s2 = gf_add(f2, S0)                   # = (2*c1) XOR (4*c2) in GF(256)
    c2 = gf_div(gf_add(s2, gf_mul(2, s1)), 6)  # solve the 2x2 system
    c1 = gf_add(s1, c2)
    return S0, c1, c2
```

Verified by sanity check: for 50 random (S0, c1, c2) triples, the recovered values match the original inputs exactly.

---

## Appendix D: Key Files in the Project

| File | Purpose |
|------|---------|
| `old_shamir.py` | The original flawed Shamir implementation from pybtc |
| `shamir.py` | The post-fix version using `generate_entropy` |
| `fingerprint.py` | Generates empirical (c1,c2) frequency distribution |
| `fingerprint_map.json` | The 640KB JSON fingerprint map |
| `universal_fingerprint.py` | Mathematical fingerprint by full enumeration |
| `full_word_search.py` | The complete 12-step beam search |
| `combined_word_selenium.py` | Beam search integrated with Selenium testing |
| `check_true_shares_against_fingerprint.py` | Diagnostic: verifies true shares are in fingerprint |
| `helper_split_test.py` | Synthetic data generator for ground-truth testing |
| `test_leakage.py` | The ~30% word collision test (result: normal statistics) |
| `challenge.py` | Early coefficient test with original shares |
| `restore_secret_from_shares.py` | Share restoration using Lagrange interpolation |

---

*This document represents the complete honest account of this research effort. The work is published openly so that others can build on it, correct it, or use it as a documented example of applied cryptanalysis methodology, including its limitations.*
