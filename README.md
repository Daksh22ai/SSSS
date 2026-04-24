# Shamir Secret Sharing Scheme (SSSS)

I had uploaded my complete work while trying to complete the "1 BTC challenge" attempting to break an implementation of the Shamir Secret Sharing Scheme.

I spent more than 1.5 years on this. At this point, my conclusion is:

Even with the historical flaws in the implementation, the scheme remains cryptographically strong enough that recovering the secret without a third share is not feasible in practice.

This repository is not a solution it is a complete research attempt explaining why the attack does not work.

---

## 📘 Read the Full Journey

I’ve documented everything in detail — all the ideas, mistakes, experiments, and conclusions:

👉 **Start here:** [Read the full research journey](SSSS_Research_Journey.md)

If you really want to understand what was done (and what doesn’t work), read that file.

---

## What I achieved during this research

* Reverse-engineered a flawed Shamir implementation
* Built a matching simulation environment
* Created synthetic test cases and verified them
* Built a fingerprint model
* Integrated decoding, scoring, interpolation, mnemonic mapping, and automation
* Benchmark-tested the recovery logic
* Found that the flaw doesn't leak enough entropy for a 2-share recovery
* Confirmed that empirically with real-world examples

---

## Final thought

In cryptography research, sometimes you break the system.
Sometimes the system proves stronger than expected.

Both outcomes are valuable because both produce knowledge.

---

This is not the end of my work on Shamir Secret Sharing Schemes. I intend to continue exploring and learning.

If you are working on this challenge or related research, I wish you the best of luck and I hope you achieve what you are working toward.
