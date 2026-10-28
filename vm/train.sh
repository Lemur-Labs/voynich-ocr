#!/bin/bash
# Startup script for one training VM. Reads its parameters from instance metadata, trains, uploads, deletes itself.
set -euxo pipefail
export HOME=/root
md() { curl -sf -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/$1"; }
COMMIT=$(md attributes/commit)
SEED=$(md attributes/seed)
LINES=$(md attributes/lines)
RUN=$(md attributes/run)
NAME=$(md name)
ZONE=$(md zone | awk -F/ '{print $NF}')

finish() {
  gcloud storage cp /var/log/train.log "$RUN/train.log" || true
  gcloud compute instances delete "$NAME" --zone "$ZONE" --quiet
}
trap finish EXIT
exec > /var/log/train.log 2>&1

curl -LsSf https://astral.sh/uv/0.9.17/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
git clone https://github.com/Lemur-Labs/voynich-ocr.git /work && cd /work && git checkout "$COMMIT"
uv sync --frozen
gcloud storage cp "$LINES" /tmp/lines.tar && mkdir -p build/lines && tar -xf /tmp/lines.tar -C build/lines
nvidia-smi
uv run python -m voynich_ocr.runner train --seed "$SEED"
gcloud storage cp --recursive "build/model/$SEED" "$RUN/"
echo done | gcloud storage cp - "$RUN/DONE"
