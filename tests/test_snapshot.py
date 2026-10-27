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
