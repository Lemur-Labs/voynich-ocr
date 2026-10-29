import argparse
import hashlib
import subprocess
import sys
import tarfile
from pathlib import Path

from voynich_ocr.lines import OUT as LINES
from voynich_ocr.snapshot import ROOT

PROJECT = "lemur-voynich-ocr"
BUCKET = "gs://lemur-voynich-ocr-snapshot"
ZONES = ("us-central1-a", "us-central1-b", "us-central1-c")
MACHINE = "g2-standard-4"
IMAGE = ("deeplearning-platform-release", "common-cu129-ubuntu-2204-nvidia-580")
# Hard cap per VM: GCE deletes it at this age whatever the training state, which bounds spend per run.
MAX_HOURS = 10
SEEDS = (20261027, 20261028, 20261029)
MODELS = ROOT / "build" / "model"
PAPER = LINES.with_name("lines-paper")
# At kraken's default 1e-3 training collapses to predicting glyph frequencies.
SCHEDULE = ["--lrate", "1e-4", "--warmup", "1000"]
# Short fixed-length diagnostic runs, each a (line dataset, extra ketos train args) pair.
ARMS = {
    "lr": (LINES, SCHEDULE),
    "paper": (PAPER, []),
    "lr-paper": (PAPER, SCHEDULE),
}
ARM_EPOCHS = 10


def ketos_args(seed: int, out: Path, arm: str | None = None) -> list[str]:
    lines, extra = ARMS[arm] if arm else (LINES, SCHEDULE)
    stop = ["-q", "fixed", "-N", str(ARM_EPOCHS)] if arm else ["-q", "early", "--min-epochs", "30", "--lag", "20"]
    return [
        "ketos", "-d", "cuda:0", "--precision", "32-true", "-s", str(seed), "-r",
        "train", "--arch", "vgsl", "-f", "path", "--linetype", "baselines", "--no-reorder",
        "-t", str(lines / "train.txt"), "-e", str(lines / "eval.txt"),
        *stop, "--augment", *extra, "-o", str(out),
    ]  # fmt: skip


def pack(dirs: list[Path]) -> tuple[Path, str]:
    """A tar of line datasets, paths relative to build/, named by the hash of its contents."""
    base = LINES.parent
    if missing := [str(d) for d in dirs if not (d / "train.txt").exists()]:
        raise SystemExit(f"line datasets not built: {missing}")
    files = sorted(p for d in dirs for p in d.rglob("*") if p.is_file())
    digest = hashlib.sha256()
    for p in files:
        digest.update(str(p.relative_to(base)).encode() + b"\0" + p.read_bytes())
    tar = base / f"lines-{digest.hexdigest()[:16]}.tar"
    if not tar.exists():
        with tarfile.open(tar, "w") as t:
            for p in files:
                t.add(p, arcname=str(p.relative_to(base)))
    return tar, digest.hexdigest()


def _commit() -> str:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True)
    pushed = subprocess.run(["git", "branch", "-r", "--contains", head.stdout.strip()], cwd=ROOT, check=True,
                            capture_output=True, text=True)  # fmt: skip
    if not pushed.stdout.strip():
        raise SystemExit("HEAD is not on GitHub; the VM clones the commit it trains")
    return head.stdout.strip()


def instance_name(seed: int, digest: str, arms: list[str]) -> str:
    return "-".join([f"train-{seed}-{digest[:8]}", *arms])


def launch(seed: int, arms: list[str]) -> str:
    commit = _commit()
    tar, digest = pack(sorted({ARMS[a][0] for a in arms}) if arms else [LINES])
    lines = f"{BUCKET}/lines/{tar.name}"
    subprocess.run(["gcloud", "storage", "cp", "--no-clobber", str(tar), lines], check=True)
    run = f"{BUCKET}/runs/{commit[:12]}-{digest[:12]}-{'-'.join([str(seed), *arms])}"
    name = instance_name(seed, digest, arms)
    for zone in ZONES:
        r = subprocess.run(
            [
                "gcloud", "compute", "instances", "create", name, f"--project={PROJECT}", f"--zone={zone}",
                f"--machine-type={MACHINE}", "--accelerator=type=nvidia-l4,count=1",
                f"--image-project={IMAGE[0]}", f"--image-family={IMAGE[1]}", "--boot-disk-size=100GB",
                "--provisioning-model=STANDARD", "--instance-termination-action=DELETE",
                f"--max-run-duration={MAX_HOURS}h", "--scopes=storage-rw,compute-rw",
                f"--metadata=install-nvidia-driver=True,commit={commit},seed={seed},lines={lines},run={run},arms={'+'.join(arms)}",
                f"--metadata-from-file=startup-script={ROOT / 'vm' / 'train.sh'}",
            ],
            check=False,
            capture_output=True,
            text=True,
        )  # fmt: skip
        if r.returncode == 0:
            return run
        if "RESOURCE_POOL_EXHAUSTED" not in r.stderr and "enough resources" not in r.stderr:
            raise SystemExit(r.stderr)
        print(f"{zone}: no capacity", file=sys.stderr)
    raise SystemExit("no zone had capacity")


def train(seed: int, arm: str | None) -> None:
    out = MODELS / (f"{seed}-{arm}" if arm else str(seed))
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(ketos_args(seed, out, arm), cwd=ROOT, check=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="runner")
    p.add_argument("command", choices=["launch", "train"])
    p.add_argument("--seed", type=int, choices=SEEDS, required=True)
    p.add_argument("--arm", action="append", choices=list(ARMS), default=[], help="launch: repeatable; train: one")
    args = p.parse_args(argv)
    if args.command == "train" and len(args.arm) > 1:
        p.error("train takes one --arm")
    if args.command == "launch":
        print(launch(args.seed, args.arm))
    else:
        train(args.seed, args.arm[0] if args.arm else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
