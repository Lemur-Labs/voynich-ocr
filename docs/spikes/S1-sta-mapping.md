# S1: native transliterations -> STA -> STA-AAA

## Verdict
- Deterministic mapping from all five sources to STA: **YES** (published, machine-readable; Zandbergen asserts lossless at "level 0" via round-trip; I did not re-run it). Caveat: the header code is `STA1` (`#=IVTFF STA1 2.0 M 5`), not "IS16" (16 was the pre-2023 draft).
- STA -> STA-AAA: **YES, forward only** (one STA code -> one aaa string, no duplicate keys); many-to-one, so irreversible by design.
- Lossless caveat: native->STA is lossless only at level 0. Level 1/2 and STA->aaa deliberately merge distinctions.

## Evidence (read = R, inferred = I)
- R: Method and tooling: https://voynich.nu/extra/sta.html. Native->STA was done with the C tool `bitrans` and bidirectional "rules files". Zandbergen says the round-trip back to the original file was the lossless test.
- R: Per-alphabet rules files, STA <-> native, in https://www.voynich.nu/software/bitrans/ (dir listing readable, dated 2025-12-05): `STA-Eva_def.bit` (242 rules), `STA-v101_def.bit` (192), `STA-Curr_def.bit` (45), `STA-FSG_def.bit` (39), `STA-EvaT_def.bit` (59). Each header is `##BIT  STA1 <alphabet>`.
- R: Also in that dir: `STA-Eva_Bint.bit` and `STA-Eva_Eint.bit` (302 rules each, one-way, STA -> Eva, "nearest" basic/extended); `STA_L0-1.bit` (5 rules), `STA_L0-2.bit` (16 rules), `STA1R.bit` (107), `STA-aaa.bit` (302), `STAR-aaa.bit` (197), `Bitrans_manual.pdf`, `bitrans.c`, `bitfiles.zip`.
- R: Rule direction: `##BIT` is bidirectional (lossless); `##BIT1` is one-way (the manual lists `##BIT1` as ambiguous/one-direction). The bidirectional/one-way reading is mine (I), from the manual's syntax examples.
- R: Where the Eva (including `@nnn;`), v101, Currier and FSG mappings are tabulated for humans: https://www.voynich.nu/data/sta/STA1_def.pdf (26 pp). It has per-STA-code columns Eva, v101, "Combi", reduced-set flag R, and counts for ZL/GC/RF. https://www.voynich.nu/data/sta/STA1-basic.pdf is a 1-page FSG/Currier/Eva/STA table for the basic characters. https://www.voynich.nu/data/sta/STA1-families.pdf is a 2-page family definition.
- R: Already-published STA files. https://www.voynich.nu/data/sta/ has no listing (it returns a 753-byte "Oops" page), but the files are linked from sta.html:
  - `CD2a_0.txt`, `CD2a_1.txt`
  - `FG2a.txt`
  - `IT2a.txt`
  - `ZL3b.txt`
  - `GC2a_0.txt`, `GC2a_1.txt`
  - plus `VT0e.txt` and `RF1b.txt`, which are not among the five
  - File names have no "-n". The only change from the IVTFF originals is that full-line and inline comments were removed.
  - https://www.voynich.nu/data/beta/ holds no STA data (LSI_ivtff_0d.txt, RF.zip, pliny_*, images). Its README is irrelevant to STA.
- R: https://voynich.nu/extra/sta-aaa.html says full STA -> aaa is `STA-aaa.bit` and reduced STA -> aaa is `STAR-aaa.bit`, both irreversible. Native text must go to STA first. The aaa grammar is `[a-z][0-9]` for a stroke, `:` for a connected pair, and `~` in some rules. The "full aaa definition" page is still marked "link to be added".
- Check I ran on the downloaded files: `STA-aaa.bit` has 302 two-character keys, 0 duplicate keys and 120 duplicate values, so it is a function but not injective. Every 2-char token (see Unverified for the tokenizer) in all nine published STA files is a key in `STA-aaa.bit` (298 distinct codes in the union, 0 missing).

## Facts the plan needs
- STA is synthetic and ligature-based. A code is one capital letter (the family) plus a digit or lowercase letter (the member), always 2 ASCII characters. STA1 defines 299 characters (sta.html); 197 of them are in "reduced STA" (sta-aaa.html). Rule counts: 302 keys in `STA-aaa.bit` and the `STA-Eva_*int.bit` files, 107 in `STA1R.bit`, 197 in `STAR-aaa.bit`.
- Distinct STA codes actually used in the published files (my count, tokenised in pairs): ZL3b 221, GC2a_0 193, GC2a_1 190, IT2a 50, CD2a_0 41, CD2a_1 36, FG2a 35. The union is 298, so the tables cover everything used. Totals: ZL about 157.3k, GC about 157.1k, IT about 155.4k, FG about 135.6k, CD about 65.2k. The ZL and GC totals agree with the PDF (157,300 and 157,093). IT is basic Eva, so it has few codes.
- Currier and FSG map only through multi-code reverse keys, for example `E3B7`->G and `F5B8`->L in `STA-Curr_def.bit`. A parser must therefore match across code boundaries. Left-to-right, longest-match is my inference, not something I tested.
- Lossy or ambiguous points, as stated in sta.html:
  - Currier collapses strings of "i". It has one symbol for i+l (G) and i+i+l (H), and Currier's `II8` for `iiid` is inconsistent. One word, `O8AIIIE9` at f23v.1, would not round-trip. Fix: "bound" variants B7/B8/E3/F5/G4, which exist only in level 0.
  - GC (v101) records alternative spellings of the same i-strings on purpose (n vs iN, I vs ii, and so on). These get alternative codes Fc/Fb/Ga..Gd. They separate again at level 0, but level 2 merges them.
  - Level 0 -> 1 -> 2 are irreversible regularisations (`STA_L0-1.bit`, `STA_L0-2.bit`). For FG, IT and ZL, level 0 equals level 1.
  - Reduced STA (`STA1R.bit`) is irreversible: it drops the v101 hooked f/p variants, the sh curl variants and rare variants.
  - Eva from STA is many-to-one (the `_Bint` file has 183 duplicate values).
  - aaa is many-to-one too, 120 duplicate values, for example A1, Ak and Al all map to `o0`.
- Native Eva / IT: the two Eva rule files are STA -> Eva only (one-way), at 302 rules each. The bidirectional `STA-Eva_def.bit` (`##BIT`, 242 rules) and `STA-EvaT_def.bit` (59 rules) are the ones to use for Eva -> STA. IT's native alphabet is Takahashi-style Eva, so `STA-EvaT_def.bit` is probably the right one (I, not tested).

## Unverified
- I did not compile `bitrans.c` or run any native -> STA -> native round trip, and did not download the five `-n` native files. "Lossless" rests on Zandbergen's statement and on the table design.
- I did not check that all five native files' symbols are covered by the `_def.bit` rules, nor that the output equals the published STA files.
- Not read: IVTFF spec, the 26-page PDF beyond the head and tail, the per-code legend colours, the "Fc/Fb" alternate-GC codes in `GC2a_1.txt`, and `bitfiles.zip`.
- `STA-aaa.bit` is the real source of the STA->aaa map. The web page says the final aaa definition page is not published yet (version dated 18 May 2025). Treat the aaa mapping as a living file with possible revisions.
- My 2-char tokenizer for the STA files ignores IVTFF syntax such as `[a:b]` alternatives (it keeps the first reading), `{}` and `@nnn;`. Counts are approximate (about 4 characters off the ZL total in the PDF); the distinct-code counts are the reliable part.
