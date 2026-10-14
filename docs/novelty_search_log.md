# Novelty search log

Entries below were performed during the 2026-10-08 audit session. **The search is INCOMPLETE.** Rows marked TODO remain to be done.

| Date | Database | Exact query | Relevant results | Notes |
|---|---|---|---|---|
| 2026-10-08 | Semantic Scholar API | `deterministic LPN Bernstein-Vazirani` | Cid–Elkouss–Goulão 2026 (source); Shukla & Vedula 2023 (generalised BV, probabilistic oracle, QIP); Li & Yang 2014 (quantum algorithm for Boolean influences, QIP) | Shukla & Vedula and Li & Yang: researcher to read abstracts for overlap |
| 2026-10-08 | Semantic Scholar API | `relative phase oracle superposition attack` | Mossayebi & Schack 2016 (security against superposition access) | Low overlap |
| 2026-10-08 | Semantic Scholar API | `Walsh spectrum Bernstein-Vazirani noisy oracle` | Zhou et al. 2026, *Grover-meets-BV Q1 attacks on permutation-based PRFs* (QIP) | Q1, not Q2; researcher to check |
| 2026-10-08 | Semantic Scholar API | `deterministic noise authentication quantum` | None relevant (QKD and physical-noise authentication papers) | — |
| 2026-10-08 | Semantic Scholar API | `deterministic LPN superposition attack`, `quantum chosen message attack LPN authentication`, `superposition attack HB protocol`, `quantum LPN learning parity with noise quantum algorithm`, `Q2 model superposition queries LPN`, `unbalanced weak pseudorandom function deterministic LPN` | **Not completed**: HTTP 429 rate limit | TODO: rerun |
| 2026-10-08 | Web search (eprint.iacr.org, cic.iacr.org, Springer, arXiv) | `deterministic LPN superposition attack quantum` | CEG 2026 (source; ePrint 2025/1506); CEG ePrint 2026/2258; Damgård et al. 2011/421 *Superposition attacks on cryptographic protocols*; Bonnetain et al. 2021/1239 *Quantum linearization attacks*; arXiv 2007.00677 *Dispelling myths on superposition attacks* | 2026/2258 read (see literature file). Others: researcher to check for deterministic-noise discussion |
| 2026-10-08 | Web search | `HB protocol superposition attack quantum chosen message deterministic noise` | Only CEG 2026 is directly relevant | — |
| 2026-10-08 | Web search | `Bernstein-Vazirani noisy oracle Walsh spectrum learning parity quantum Goldreich-Levin` | Li & Yang arXiv:2001.00014; arXiv:2305.19745 (*Effects of noise on BV*) | Spectral learning overlap: must be read |
| 2026-10-08 | Web search | `"Q2" superposition queries LPN authentication Lapin quantum attack` | CEG 2026; Lapin (Heyse et al.); Bonnetain et al. *Offline Simon* (2019/614) | No deterministic-LPN Q2 analysis found |
| 2026-10-08 | ePrint mirror (eprint.iacr.asia) search page | `deterministic LPN`, `superposition attack`, `Bernstein-Vazirani`, `quantum chosen message` | Search page not parsed (0 results returned by script) | TODO: search manually |
| TODO | IACR ePrint (web UI) | all planned query combinations | — | Bot check requires a human |
| TODO | Google Scholar | all query combinations; also "cited by" for CEG 2026 and ACNS 2026 | — | Manual |
| TODO | CRYPTO / EUROCRYPT / ASIACRYPT / TCC proceedings 2024–2026 | `superposition`, `Q2`, `deterministic LPN` | — | dblp or Springer |
| TODO | QCrypt 2024–2026 programmes | `superposition attack`, `LPN` | — | Manual |
| TODO | ACNS / PQCrypto 2024–2026 | `deterministic LPN`, `superposition` | — | Manual |

**Interim conclusion (not final):** no located work analyses deterministic-LPN HB authentication under Q2 via the Walsh spectrum. The closest are CEG 2026 (§8 open remark), CEG ePrint 2026/2258 §8.2 (Dilithium heuristic), and quantum Goldreich–Levin and spectral-learning work. **This does not justify "novel" until the TODO rows are done.**
