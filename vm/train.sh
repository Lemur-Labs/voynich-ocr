#!/bin/bash
# Startup script for one training VM. Reads its parameters from instance metadata, trains, uploads, deletes itself.
set -euxo pipefail
export HOME=/root
md() { curl -sf -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/$1"; }
COMMIT=$(md attributes/commit)
SEED=$(md attributes/seed)
LINES=$(md attributes/lines)
RUN=$(md attributes/run)
ARMS=$(md attributes/arms || true)
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
gcloud storage cp "$LINES" /tmp/lines.tar && mkdir -p build && tar -xf /tmp/lines.tar -C build
nvidia-smi
mkdir -p build/model
(while sleep 900; do gcloud storage rsync --recursive build/model "$RUN/model" || true; done) &
pids=()
if [ -z "$ARMS" ]; then
  uv run python -m voynich_ocr.runner train --seed "$SEED" & pids+=($!)
else
  for arm in ${ARMS//+/ }; do
    uv run python -m voynich_ocr.runner train --seed "$SEED" --arm "$arm" > "/var/log/train-$arm.log" 2>&1 & pids+=($!)
  done
fi
rc=0
for pid in "${pids[@]}"; do wait "$pid" || rc=1; done
gcloud storage rsync --recursive build/model "$RUN/model"
gcloud storage cp /var/log/train-*.log "$RUN/" || true
[ "$rc" = 0 ] && echo done | gcloud storage cp - "$RUN/DONE"
