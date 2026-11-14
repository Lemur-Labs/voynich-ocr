.PHONY: snapshot snapshot-verify snapshot-map snapshot-push snapshot-pull test lint map g1 seg lines audit reproduce explorer

BUCKET := gs://lemur-voynich-ocr-snapshot

# Everything the map and its CI proof need: the five STA transliterations, the STA-AAA alphabet
# and the ivtt oracle source. Deliberately not the ~150 page images.
MAP_SNAPSHOT_PATHS := transliterations/sta bitrans/STA-aaa.bit ivtt/ivtt.c
MAP_SNAPSHOT_ARGS := $(foreach p,$(MAP_SNAPSHOT_PATHS),--path=$(p))

snapshot:
	uv run python -m voynich_ocr.snapshot fetch
	uv run python -m voynich_ocr.snapshot verify

snapshot-verify:
	uv run python -m voynich_ocr.snapshot verify

snapshot-map:
	uv run python -m voynich_ocr.snapshot fetch $(MAP_SNAPSHOT_ARGS)
	uv run python -m voynich_ocr.snapshot verify $(MAP_SNAPSHOT_ARGS)

snapshot-push: snapshot-verify
	gcloud storage rsync --recursive data/raw $(BUCKET)/raw

snapshot-pull:
	gcloud storage rsync --recursive $(BUCKET)/raw data/raw
	uv run python -m voynich_ocr.snapshot verify

test:
	uv run pytest -q

lint:
	uv run ruff check .

map: snapshot-map
	uv run python -m voynich_ocr.disagreement --out build/map

g1: map
	uv run python -m voynich_ocr.g1

# Full fresh-clone proof: snapshot → map → g1, every regenerated artifact byte-compared
# against the committed record (results/) and the map-v0 release's SHA256SUMS.
reproduce:
	uv sync --locked
	$(MAKE) snapshot
	mkdir -p build/reproduce
	git show HEAD:results/g1/checks.json > build/reproduce/g1-checks-expected.json
	$(MAKE) g1
	uv run python -m voynich_ocr.reproduce
	@echo "reproduce: all regenerated artifacts match the committed record"

seg: snapshot-verify
	uv run python -m voynich_ocr.segment

lines: seg
	uv run python -m voynich_ocr.lines

audit:
	uv run python -m voynich_ocr.audit

# Static disagreement explorer over the published no-readings map outputs (needs `make map`).
explorer: map
	uv run python -m voynich_ocr.explorer
