.PHONY: snapshot snapshot-verify snapshot-push snapshot-pull test lint map g1

BUCKET := gs://lemur-voynich-ocr-snapshot

snapshot:
	uv run python -m voynich_ocr.snapshot fetch
	uv run python -m voynich_ocr.snapshot verify

snapshot-verify:
	uv run python -m voynich_ocr.snapshot verify

snapshot-push: snapshot-verify
	gcloud storage rsync --recursive data/raw $(BUCKET)/raw

snapshot-pull:
	gcloud storage rsync --recursive $(BUCKET)/raw data/raw
	uv run python -m voynich_ocr.snapshot verify

test:
	uv run pytest -q

lint:
	uv run ruff check .

map: snapshot-verify
	uv run python -m voynich_ocr.disagreement --out build/map
	mkdir -p results/map-v0
	cp build/map/summary.json results/map-v0/summary.json

g1: map
	uv run python -m voynich_ocr.g1
