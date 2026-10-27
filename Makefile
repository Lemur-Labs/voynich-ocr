.PHONY: snapshot snapshot-verify snapshot-push snapshot-pull test lint

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
