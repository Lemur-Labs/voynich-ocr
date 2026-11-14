from voynich_ocr import snapshot


def _pinned(tmp_path):
    raw = tmp_path / "raw"
    (raw / "a").mkdir(parents=True)
    (raw / "a" / "x.txt").write_text("<f1r.1>  fachys.ykal\n")
    manifest = tmp_path / "manifest.sha256"
    snapshot.write_manifest({"a/x.txt": snapshot.sha256(raw / "a" / "x.txt")}, manifest)
    return raw, snapshot.read_manifest(manifest)


def test_verify_passes_when_files_match_their_pins(tmp_path):
    raw, pins = _pinned(tmp_path)
    assert snapshot.mismatches(pins, raw) == []


def test_verify_names_a_file_whose_bytes_changed_upstream(tmp_path):
    raw, pins = _pinned(tmp_path)
    (raw / "a" / "x.txt").write_text("<f1r.1>  fachys.ykal.ar\n")
    assert snapshot.mismatches(pins, raw) == ["changed  a/x.txt"]


def test_verify_names_a_missing_file(tmp_path):
    raw, pins = _pinned(tmp_path)
    (raw / "a" / "x.txt").unlink()
    assert snapshot.mismatches(pins, raw) == ["missing  a/x.txt"]


def test_every_source_is_pinned_and_every_pin_has_a_source():
    paths = {s["path"] for s in snapshot.load_sources()}
    assert paths == set(snapshot.read_manifest())


def test_select_matches_exact_paths_and_directory_prefixes():
    assert snapshot.selects("transliterations/sta/ZL3b.txt", ["transliterations/sta"])
    assert snapshot.selects("transliterations/sta/ZL3b.txt", ["transliterations/sta/ZL3b.txt"])
    assert snapshot.selects("transliterations/sta/ZL3b.txt", ["transliterations/sta/"])
    assert not snapshot.selects("transliterations/sta-other/ZL3b.txt", ["transliterations/sta"])
    assert not snapshot.selects("bitrans/bitrans.c", ["transliterations/sta"])


def test_fetch_skips_paths_outside_the_filter(tmp_path):
    raw = tmp_path / "raw"
    (raw / "keep").mkdir(parents=True)
    (raw / "skip").mkdir()
    (raw / "keep" / "f.txt").write_text("kept\n")
    (raw / "skip" / "f.txt").write_text("skipped\n")
    sources = [
        {"path": "keep/f.txt", "url": "file://" + str(raw / "keep" / "f.txt")},
        {"path": "skip/f.txt", "url": "file://" + str(raw / "skip" / "f.txt")},
    ]
    snapshot.fetch(sources, raw / "fetch", paths=["keep"])
    assert (raw / "fetch" / "keep" / "f.txt").exists()
    assert not (raw / "fetch" / "skip" / "f.txt").exists()


def test_verify_only_checks_the_selected_subset(tmp_path):
    raw, pins = _pinned(tmp_path)
    pins["b/y.txt"] = "0" * 64
    assert snapshot.mismatches(pins, raw) == ["missing  b/y.txt"]
    subset = {p: d for p, d in pins.items() if snapshot.selects(p, ["a"])}
    assert snapshot.mismatches(subset, raw) == []
