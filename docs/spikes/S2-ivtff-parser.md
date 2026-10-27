# S2: IVTFF parser spike

Spec: IVTFF_format.pdf, format 2.0.1, doc issue 2.0.2 (08/07/2025). ivtt.c v2.4 (07/09/2025). Fetched 2026-10-26/27. Scratch: `.../scratchpad/{s2-data,s2-scripts,s2-misc,s2-out}`.

## Verdict
IVTFF is small and line-oriented; a Python parser is about 150 lines and well-bounded. Build it. `ivtt` is a usable differential oracle for the text-extraction path only (comments stripped, first alternative taken, spaces normalised). It is not an oracle for structure, validation, or alphabet conversion (it has none; that is `bitrans`). Parse the five files in full, then check against ivtt `-x2` output. I did this for the first-alternative/strip-comments path: my 15-line emulation matches ivtt byte-for-byte on ZL3b, FG2a and CD2a. On IT2a and GC2a it matches once the one `!` locus ivtt drops is accounted for (below). Do NOT use the PyPI `ivtff` 0.0.1 (58 lines, regex-only) as a reference.

## Parser checklist (example from the real files)
Header (line 1, must be >=18 chars): `#=IVTFF Eva- 2.0 M 5`. Fields: alphabet (4ch), version, M/D/A, then an extra trailing field (`5`; real files carry it, the spec does not mention it).
- `#` lines: free text anywhere, even between loci (ZL: 2897 of them; 6 exceed the 80-char limit). Never interpret.
- Page header: `<f1r>      <! $Q=A $P=A $F=a $B=1 $I=T $L=A $H=1 $C=1 $X=V>` where vars are `$X=y`, and value `@` is legal (spec). Page vars reset per page. Names like `f89v2`, `f1r` are NOT purely `f\d+[rv]`; the ivtff package regex would drop these.
- Locus: `<f1r.7,*P0>` = page `.` num `,` locator + type, optional `;T` transcriber (spec only; 0 in these files). Locators seen: `@ + * = & ~ / !`. Types seen: P0 P1 Pb Pc Pr Pt L0 La Lc Lf Ln Lp Ls Lt Lx Lz Ca Cc Ri Ro. Whitespace after `>` is padding.
- `!` locator, e.g. `<f89v2.26,!Lf>    ?ds??o` (IT, GC; text that does not exist in the MS).
- Paragraph marks: `<%>` at line start, `<$>` at end: `<f1r.1,@P0>       <%>fachys...`, `<f1r.6,=Pt>       ydaraishy<$>`.
- Drawing intrusion `<->` (implies a word space) and `<~>`: `...ol<->o,l,tchey`, `...aiin<->shy.chckhy<~>oltchedy`.
- Text tags `<@H=2>`, which follow `<%>`: `<f115r.1,@P0>     <%><@H=2>f{c'hh}dar...` (five-character dedicated comment; 1 per file in 4 files).
- Free comment `<! ... >` (ZL only): `...[cth:oto]res.y.kor.sholdy<!@254;>`. Can contain `@nnn;`; `/` inside loses meaning. Must be stripped BEFORE tokenising other constructs.
- High-ascii `@nnn;` (128-255): GC `ohai@228;Ae`, ZL `{c@132;h}s`; also appears inside `<! >` and inside `{ }` and `[ ]`.
- Ligature `{...}` (ZL only, 446 occurrences, 2-17 chars between braces; content may include apostrophes and `@nnn;`): `{c'ha},chodam`, `{c'h@148;h}y`.
- Alternatives `[a:b]` and `[a:b:c]` (ZL only; 814 two-way, 3 three-way). Options may be multi-character (207 do), contain `?` (154), or nest a ligature: `[sh:{@209;h}]ody`; three-way: `ot[ee:a:ei]y`. First option is the preferred one. Colon is mandatory in 2.0 (the ivtff package tolerates `[ab]`; none in these files).
- Spaces: `.` certain, `,` uncertain (ZL 2748, GC 2459, FG 4, CD/IT 0 since those files carry no uncertain spaces). A `,` or `.` is never leading/trailing/doubled in 2.0, and my check (`spaceviol`) found no violations in these files.
- Unreadable `?` (one) and `???` (unknown run); my counts include runs of 2-6 `?` (e.g. IT has `??????` x7), so treat `?+` as a token and not just 1 or 3.
- Line continuation `/` (trailing `/` and leading `/`): spec only. 0 occurrences in all five files. Implement per spec anyway (cheap); untested against real data.
- `&nnn;` codes: none in any file. The task premise (`&nnn;`) is the pre-2.0 notation; 2.0 uses `@nnn;`.
- Alphabet-dependent characters. The GC (v101) text legitimately contains `! ( + & % $ \ ^ | # * ,` as letters, and `,` there reads as an uncertain space in ivtt but is also in v101's character set. A generic parser must treat the alphabet as opaque tokens and expose the raw text; do not assume `[a-z]`. `*` appears 164 times in GC, with no special meaning in the 2.0 spec (old unreadable marker).
- Encoding: every file is pure 7-bit ASCII, LF endings, max line 340 chars (spec limit 2048).
- Spec 6.10 only recommends locus ordering; do not rely on it. Page names should match the Annex 1 list; I did not cross-check it.

## Per-file counts
| | CD2a (Currier) | FG2a (FSG) | GC2a (v101) | IT2a (EvaT) | ZL3b (Eva) |
|---|---|---|---|---|---|
| SHA-256 | edc18e6de699c50d575925d4f469685ccbbe22c9755b9b8a3b002f83253cbde5 | a1460a05ff610a406e62b4095a8f8e88c04653c1ef4aa5ad6428ddb1ac01fe06 | b09570cb6c993bc2d87134d115e60a978650a8a6495483ddbb1f6005a586096f | 7f27a8b0feed8f6de0a99900df6bf912dd1d295c38e5f830bac8b41c3f536fb5 | bf5b6d4ac1e3a51b1847a9c388318d609020441ccd56984c901c32b09beccafc |
| bytes | 132833 | 264787 | 314916 | 342104 | 411671 |
| header | Curr 2.0 M 1 | FSG- 2.0 M 2 | v101 2.0 M 6 | EvaT 2.0 M 3 | Eva- 2.0 M 5 |
| page headers (all distinct) | 131 | 202 | 226 | 225 | 227 |
| loci | 2196 | 4060 | 5367 | 5215 | 5385 |
| `#` lines | 149 | 4 | 228 | 3 | 2897 |
| locus types (distinct) | 8 | 11 | 20 | 19 | 20 |
| locators | `@+*=~` | `@+*=` | `@+*=&~/!` | `@+*=&~!` | `@+*=&~/` |
| `<!...>` comments | 0 | 0 | 0 | 0 | 863 |
| `<%>`/`<$>` | 236/236 | 734/734 | 775/775 | 772/772 | 740/740 |
| `<->` / `<~>` | 260 / 6 | 0 / 0 | 0 / 0 | 875 / 0 | 758 / 6 |
| `<@H=n>` tags | 0 | 2 | 2 | 2 | 2 |
| `[a:b]` / `[a:b:c]` | 0 | 0 | 0 | 0 | 814 / 3 |
| `{...}` ligatures | 0 | 0 | 0 | 0 | 446 |
| `@nnn;` (distinct values, range) | 0 | 0 | 98 (149-255) | 0 | 90 (130-255) |
| `&nnn;` | 0 | 0 | 0 | 0 | 0 |
| `?` runs (1 / 2 / 3+) | 125/23/3 | 175/31/36 | 71/9/2 | 118/23/23 | 216/7/26 |
| `*` | 0 | 0 | 164 | 0 | 0 |
| `.` / `,` spaces | 13799 / 0 | 29272 / 4 | 32875 / 2459 | 31829 / 0 | 30129 / 2748 |
| continuation `/`, `;T` ids | 0 | 0 | 0 | 0 | 0 |
| pages also in all other 4 files | 131 | 131 | 131 | 131 | 131 |

Coverage: page union 227 (ZL); CD covers 131, FG 202. Locus ids common to all five: 2185; union 5386; ZL-only 18 loci (all other files have no locus the others lack). CD loci are a subset of every other file's. (Locus id = `fNN.n`, ignoring locator/type, which differ between files.) The text-tag count above is the same 1 `<@H=2>` plus 1 `<@H=3>` per file, so 2 each, and CD has none.

## ivtt as oracle
- Source: single file `ivtt.c`, 66 KB, https://mail.voynich.nu/software/ivtt/ivtt.c (also IVTT_manual.pdf). License: none stated in the source or manual (grep for licen/copyright finds nothing). Treat it as all-rights-reserved-by-default; fine to run locally, so check with Zandbergen before vendoring it or redistributing it.
- Build: `cc -O1 -o ivtt ivtt.c` works on macOS (Darwin 25.6, Apple clang), 5 warnings, no errors. Built in the scratch dir, nothing installed.
- Gotcha: with no input file argument it reads stdin and will hang; always pass files, and use `</dev/null` in scripts. It returned exit code 3 on every successful run I made (`return 3` at ivtt.c:2139), so don't treat nonzero as failure without reading the source.
- Options: `-x0..8` shortcuts (e.g. `-x2` = remove comments/foliation/paragraph marks, take first alternate, remove blanks; one line per locus); `-c` comments, `-p` paragraph/drawing marks, `-u0..5` alternates (keep/first/`?`/drop word/drop line), `-l` ligature braces, `-a` `@nnn;` vs high byte, `-s`/`-h` certain/uncertain spaces, `-w` wrapping, `-b` blanks, `-t`/`+t` transcriber, `-q` paragraph lines, page/locus include/exclude by page variables, `-m3` diagnostics (no output). It does NOT convert alphabets (use `bitrans`, same directory) and does not emit a structured parse.
- Differential result: `ivtt -x2` vs my independent regex emulation, per locus: ZL3b 5385/5385 identical, FG2a 4060/4060, CD2a 2196/2196. IT2a and GC2a: ivtt writes 5214/5366 lines, one fewer than loci, because it silently counts `<f89v2.26,!Lf>` as "1 for invalid locus" and drops it, even though format 2.0.1 Table 8 lists `!` as valid. Changing that locator to `+` makes ivtt emit all 5215 lines. So ivtt v2.4 lags the spec on `!`. Use `-m3` diagnostics and the stderr stats ("lines read / de-selected / invalid locus") as part of any comparison.
- Limits as oracle: it only exercises options I choose; on these files the interesting constructs (alternatives, ligatures, `<! >`) exist only in ZL3b, so differential coverage of them comes from one file. Good extra checks: `-u2`, `-l2`, `-a2`, `-s1 -h2`. I ran `-u2 -l2 -a2` and `-u1` for exit status only, not for a diff.

## Unverified
- Annex 1 page-name list and the order rule were not checked against the files; I did not validate that every page header is legal.
- I did not read IVTT_manual.pdf in full (option table only), nor the full ivtt.c; behaviour of `-l2`, `-u3..5`, `-s`/`-h` options is untested.
- Continuation lines, `;T` transcriber ids, are absent from the data, so those parser paths are spec-only.
- The meaning of "2 lines de-selected" (1 after the `!` fix) in ivtt stats, and of the exit code 3, is unknown.
- Trailing 6th header field (e.g. `5`) is undocumented in the spec; purpose unknown.
- Spec text was read via pdftotext (layout), not visually; Table 8/9 transcriptions may have lost nuance.
- The `ivtff` PyPI package was read (single `__init__.py`); behaviour not executed.
- License of the data files was not checked.
