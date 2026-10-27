# S6 spike: Naibbe cipher (Greshko 2025)

## Verdict
Yes, port faithfully and validate. The author ships MIT-licensed Python (GitHub, mirrored on Zenodo) with the full substitution tables as a 413-row CSV, so nothing needs re-typing from the paper or Excel. Known-answer test (KAT), two layers:
1. Table/decrypt KAT: ship `references/naibbe_tables.csv` verbatim; for each shipped pair (`encrypted/examples/*`, `respaced_plaintext/*`, `decrypted/examples/*`), our decryptor must recover the shipped pre-encryption respaced plaintext. The ciphertext is deterministic given the deck draws, so this checks tables + unambiguity logic.
2. Encrypt KAT: for any seed, `decrypt(encrypt(p)) == respaced(p)`, plus distribution checks (unigram/bigram ratio near 17/36 split, card weights, no prefix+suffix collision with a unigram word type).
We cannot byte-match Greshko's ciphertexts from an RNG seed: his code uses unseeded global `random` and shuffles the deck, and the exact draw order of respacing and cards is unrecorded. Our own seeded RNG is fine, because the shipped files give the KAT (layer 1).

## Algorithm (from naibbe.py, v2 differences noted; main paper text not read, see Unverified)
- Preprocess: NFD strip diacritics; ae/oe/d/th/l/ss/o digraph mappings; keep alpha only; uppercase; W->UU, J->I, K->C; lowercase. Spaces removed. Table alphabet is 23 letters (no j/k/w).
- Respacing into unigrams/bigrams: at each position, emit a unigram with p = RESPACING/36 (17/36 standard, 18/36 for 50-50), or when at the last letter; else emit the next 2 letters as a bigram. This is the paper's "die" step (die-roll equivalent, not literally dice in code).
- Deck: 52-card deck weights alpha 20, beta1 8, beta2 8, beta3 8, gamma1 4, gamma2 4. The 78-card deck is alpha 28, beta1 14, beta2 11, beta3 11, gamma1 7, gamma2 7. Shuffled, drawn without replacement, reshuffled when exhausted. Each draw selects one of 6 tables.
- Unigram: one card, then token = `unigram[table][letter]`.
- Bigram: two cards. Token = `prefix[table1][L1] + suffix[table2][L2]`. With UNAMBIGUOUS=True (recommended), redraw both cards if the concatenation equals any unigram word type (retries counted). v2 additionally precomputes a catalog of cross-bigram collisions (same string from different prefix/suffix pairs) and has a MAX_BIGRAM_RETRIES fuse; v2 defaults to the 78-card deck.
- Output: EVA-transliterated Voynichese strings from the CSV (`code,glyphs`, code = `{unigram|prefix|suffix}_{table}_{letter}`; tables alpha, beta1-3, gamma1-2; 23 letters each, 18 groups x 23 = 414 rows incl. header). Rare glyphs x and g are included.
- Spacing: each token is one word, space-joined, one output line per input line. Optional post-step drops 3% of spaces at random (SPACE_REMOVAL_RATE) to mimic uncertain VMS spacing.
- Decrypt (`decrypt_naibbe.py`): prefers unigram match, then resolves compound tokens via prefix/suffix; ambiguity is meant to be absent with unambiguous encryption.
- Supplement S2 (Voynichesque, a separate generator) is out of scope.

## Sources
| What | URL | License | Access |
|---|---|---|---|
| Code + tables + examples | https://github.com/greshko/naibbe-cipher (also hermesj fork; dninemfive/gnc "generalized Naibbe", MIT) | LICENSE file: plain MIT. README and file headers: "modified MIT" requiring publications to cite the paper | open, cloned to s6-data/gh |
| Zenodo supplement v (17219445), concept DOI 10.5281/zenodo.16415087 | https://zenodo.org/records/17219445 | CC-BY-4.0, access_right open | open, no login. Files: Naibbe Cipher.xlsx (17 MB), Voynichesque.xlsm, Figures*.xlsx, Asymmetrical Word Pairings.xlsx, .gephi, Supplementary Materials 1-4 PDF |
| Downloaded | s6-data/Naibbe Cipher.xlsx (unzipped to s6-data/x, 11 sheets: home, analysis, encrypter, glyph pair, text dropdown, deck and spacing, manual unigram, unigram_lookup, text links, presuf_lookup, all; not opened with macros, no xlsm fetched), s6-data/Supp.pdf (text at s6-pdf/supp.txt) | CC-BY-4.0 | open |
| Paper | https://doi.org/10.1080/01611194.2025.2566408 | tandfonline returned 403 to curl/WebFetch; forum comment says it became open access Nov 2025 | not confirmed |
| Preprint + 20 reference ciphertexts | voynich.ninja thread 4848 (Dropbox) | unknown | Dropbox URL not extractable (link hidden in fetch output) |

## Licensing for an MIT repo
Tables are data in the MIT/modified-MIT repo; Zenodo files are CC-BY-4.0. Reuse is allowed with attribution; the README adds a citation requirement for publications. Safe course: vendor the CSV with its copyright notice, cite the paper, keep a NOTICE file. The plain-MIT LICENSE vs. modified-MIT README discrepancy is the one thing to flag to the owner (or ask the author).

## Unverified
- Main-paper text (dice details, why 17/36, historical rationale) not read; this note derives from code + supplement. Paper OA status unconfirmed.
- The "20 reference ciphertexts" Dropbox link and their plaintexts not retrieved. The repo's example set is smaller (Gallic War, Natural History book 16, Divina Commedia, endofpaper).
- No dependency check or run done; code needs pandas. KATs not executed. Pandas absent-ness and openpyxl absent locally (xlsx read via unzip only).
- Other GitHub reimplementations only seen via search listing (dninemfive/gnc, hermesj fork); not inspected. An arXiv paper (2608.17096) reportedly reimplemented from the tables; not read.
- Whether the CSV equals the Excel tables (and the paper's printed tables) not diffed.
