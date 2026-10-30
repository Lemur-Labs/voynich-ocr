import argparse
import contextlib
import functools
import importlib.util
import io
import json
import random
import re
import sys
from types import ModuleType

import pandas as pd

from voynich_ocr.snapshot import RAW, ROOT

NAIBBE = RAW / "naibbe"
PLAINTEXT = NAIBBE / "input" / "examples" / "nathist_book16.txt"
SHIPPED = {
    "ciphertext": NAIBBE / "encrypted" / "nathist_output_ciphertext.txt",
    "respaced": NAIBBE / "respaced_plaintext" / "nathist_pre_encryption_respaced_plaintext.txt",
    "decrypted": NAIBBE / "decrypted" / "nathist_output_ciphertext_decrypted.txt",
}
SEED = 20261027
ROUND_TRIP_SEEDS = 100
ROUND_TRIP_LINES = 20
OUT = ROOT / "build" / "naibbe"


@functools.cache
def _module(name: str) -> ModuleType:
    """Greshko's script, unchanged. It reads its tables by relative path at import and prints a count."""
    spec = importlib.util.spec_from_file_location(f"greshko_{name}", NAIBBE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    with contextlib.chdir(NAIBBE), contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(module)
    return module


def encipher(plain: list[str], seed: int) -> tuple[list[str], list[str]]:
    """Ciphertext and respaced plaintext per line, as naibbe.py's main loop writes them, with Python's global
    `random` seeded first. Its space-removal step still runs, so the draws match the script's, but its output is
    discarded."""
    n = _module("naibbe")
    random.seed(seed)
    cipher, respaced = [], []
    for line in plain:
        cleaned = n.clean_line(line)
        if not cleaned:
            cipher.append("")
            respaced.append("")
            continue
        pre = io.StringIO()
        tokens = n.encrypt_naibbe(
            cleaned, n.naibbe_tables, n.placeholder_to_glyph, use_78=n.USE_78_CARD_DECK, pre_plaintext_file=pre
        )
        line_out = " ".join(tokens)
        n.respace_line(line_out, n.SPACE_REMOVAL_RATE)
        cipher.append(line_out)
        respaced.append(pre.getvalue().rstrip("\n"))
    return cipher, respaced


def decipher(cipher: list[str]) -> list[str]:
    d = _module("decrypt_naibbe")
    maps = d.build_reverse_mappings(pd.read_csv(NAIBBE / "references" / "naibbe_tables.csv"))
    return [d.decrypt_naibbe_line(line, *maps) for line in cipher]


def consistent(decrypted: str, respaced: str) -> bool:
    """Every plaintext token is the decrypted token, or one of the options decrypt_naibbe lists for it."""
    got = re.findall(r"\([^)]*\)|\S+", decrypted)
    want = respaced.split()
    if len(got) != len(want):
        return False
    return all(g == w or w in [o.rstrip("*") for o in g.strip("()").split("|")] for g, w in zip(got, want))


def _lines(path) -> list[str]:
    return path.read_text(encoding="utf-8").split("\n")


def check() -> dict:
    cipher, respaced, decrypted = (_lines(SHIPPED[k]) for k in ("ciphertext", "respaced", "decrypted"))
    ours = decipher(cipher)
    sample = [line for line in _lines(PLAINTEXT) if _module("naibbe").clean_line(line)][:ROUND_TRIP_LINES]
    trips = 0
    for seed in range(ROUND_TRIP_SEEDS):
        c, r = encipher(sample, seed)
        trips += all(consistent(x, y) for x, y in zip(decipher(c), r))
    report = {
        "shipped_lines": len(cipher),
        "shipped_decrypted_identical": ours == decrypted,
        "shipped_plaintext_consistent": sum(consistent(x, y) for x, y in zip(ours, respaced)),
        "round_trip_seeds": ROUND_TRIP_SEEDS,
        "round_trip_lines": len(sample),
        "round_trip_passed": trips,
        "seeded_repeatable": encipher(sample, SEED) == encipher(sample, SEED),
    }
    report["passed"] = (
        report["shipped_decrypted_identical"]
        and report["shipped_plaintext_consistent"] == len(cipher)
        and trips == ROUND_TRIP_SEEDS
        and report["seeded_repeatable"]
    )
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="naibbe")
    p.add_argument("command", choices=["check"])
    p.parse_args(argv)
    report = check()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "port_check.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
