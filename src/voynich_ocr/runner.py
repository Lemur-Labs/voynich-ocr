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
MAX_HOURS = 6
SEEDS = (20261027, 20261028, 20261029)
MODELS = ROOT / "build" / "model"


def ketos_args(seed: int, out: Path) -> list[str]:
    return [
        "ketos", "-d", "cuda:0", "--precision", "32-true", "-s", str(seed), "-r",
        "train", "--arch", "vgsl", "-f", "path", "--no-reorder",
        "-t", str(LINES / "train.txt"), "-e", str(LINES / "eval.txt"),
        "-q", "early", "--lag", "10", "-o", str(out),
    ]  # fmt: skip


def pack(lines: Path = LINES) -> tuple[Path, str]:
    """A tar of the line dataset, named by the hash of its contents."""
    files = sorted(p for p in lines.rglob("*") if p.is_file())
    digest = hashlib.sha256()
    for p in files:
        digest.update(str(p.relative_to(lines)).encode() + b"\0" + p.read_bytes())
    tar = ROOT / "build" / f"lines-{digest.hexdigest()[:16]}.tar"
    if not tar.exists():
        with tarfile.open(tar, "w") as t:
            for p in files:
                t.add(p, arcname=str(p.relative_to(lines)))
    return tar, digest.hexdigest()


def _commit() -> str:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True)
    pushed = subprocess.run(["git", "branch", "-r", "--contains", head.stdout.strip()], cwd=ROOT, check=True,
                            capture_output=True, text=True)  # fmt: skip
    if not pushed.stdout.strip():
        raise SystemExit("HEAD is not on GitHub; the VM clones the commit it trains")
    return head.stdout.strip()


def launch(seed: int) -> str:
    commit = _commit()
    tar, digest = pack()
    lines = f"{BUCKET}/lines/{tar.name}"
    subprocess.run(["gcloud", "storage", "cp", "--no-clobber", str(tar), lines], check=True)
    run = f"{BUCKET}/runs/{commit[:12]}-{digest[:12]}-{seed}"
    name = f"train-{seed}"
    for zone in ZONES:
        r = subprocess.run(
            [
                "gcloud", "compute", "instances", "create", name, f"--project={PROJECT}", f"--zone={zone}",
                f"--machine-type={MACHINE}", "--accelerator=type=nvidia-l4,count=1",
                f"--image-project={IMAGE[0]}", f"--image-family={IMAGE[1]}", "--boot-disk-size=100GB",
                "--provisioning-model=SPOT", "--instance-termination-action=DELETE",
                f"--max-run-duration={MAX_HOURS}h", "--scopes=storage-rw,compute-rw",
                f"--metadata=install-nvidia-driver=True,commit={commit},seed={seed},lines={lines},run={run}",
                f"--metadata-from-file=startup-script={ROOT / 'vm' / 'train.sh'}",
            ],
            check=False,
            capture_output=True,
            text=True,
        )  # fmt: skip
        if r.returncode == 0:
            return run
        print(f"{zone}: {r.stderr.strip().splitlines()[-1]}", file=sys.stderr)
    raise SystemExit("no zone had capacity")


def train(seed: int) -> None:
    out = MODELS / str(seed)
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(ketos_args(seed, out), cwd=ROOT, check=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="runner")
    p.add_argument("command", choices=["launch", "train"])
    p.add_argument("--seed", type=int, choices=SEEDS, required=True)
    args = p.parse_args(argv)
    if args.command == "launch":
        print(launch(args.seed))
    else:
        train(args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
