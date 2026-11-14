"""Explorer tests run on a tiny fixture of published-shape inputs: a no-readings TSV and a summary."""

import json

import pytest

from voynich_ocr import explorer

# One pairwise "top" entry, so the boundary check has a real token vocabulary to grep against.
SUMMARY = {
    "withheld_test_pages": 1,
    "maps": {
        "full": {
            "sources": ["ZL", "IT", "GC", "FG", "CD"],
            "overall": {
                "columns": 3,
                "classes": {"agree": 2, "disagree": 1},
                "gated": 2,
                "gated_disagree": 1,
                "gated_rate": 0.5,
            },
        },
        "leave-ZL-out": {
            "sources": ["IT", "GC", "FG", "CD"],
            "overall": {"columns": 3, "gated": 1, "gated_disagree": 0, "gated_rate": 0.0},
        },
    },
    "pairwise": {
        "ZL-IT": {
            "columns": 2,
            "differ": 1,
            "rate": 0.5,
            "top": [["a0", "o0", 1], ["c2:v3:c1", "c2:c1", 2]],
        }
    },
}

HEADER = "locus\tcolumn\ttier\tclass\tflag\tcontributing\tgated"


@pytest.fixture
def built(tmp_path):
    map_dir = tmp_path / "map"
    (map_dir / "published").mkdir(parents=True)
    (map_dir / "published" / "full.tsv").write_text(
        f"{HEADER}\n"
        "f1r.1\t0\t5\tagree\t\tZL,IT,GC,FG,CD\tgated\n"
        "f1r.1\t1\t5\tdisagree\tzl_uncertain\tZL,IT,GC,FG,CD\tgated\n"
        "f1r.2\t0\t2\tunscorable\t\tIT\t\n"
    )
    (map_dir / "summary.json").write_text(json.dumps(SUMMARY))
    out = tmp_path / "explorer"
    explorer.main(["--map-dir", str(map_dir), "--out", str(out)])
    return out


def test_writes_an_index_one_page_per_folio_and_one_per_column(built):
    assert (built / "index.html").exists()
    assert (built / "folios" / "f1r.html").exists()
    assert (built / "columns" / "f1r.1-0.html").exists()
    assert (built / "columns" / "f1r.1-1.html").exists()
    assert (built / "columns" / "f1r.2-0.html").exists()


def test_index_carries_the_headline_rate_and_the_pairwise_matrix(built):
    index = (built / "index.html").read_text()
    assert "0.5" in index
    assert "ZL-IT" in index
    assert "0.5</td>" in index


def test_folio_page_links_to_its_columns_and_back(built):
    folio = (built / "folios" / "f1r.html").read_text()
    assert 'href="../columns/f1r.1-1.html"' in folio
    assert 'href="../index.html"' in folio
    assert "disagree" in folio


def test_column_page_shows_class_tier_flag_contributors_and_gating(built):
    column = (built / "columns" / "f1r.1-1.html").read_text()
    assert "disagree" in column
    assert "zl uncertain" in column
    assert "ZL, IT, GC, FG, CD" in column
    assert 'href="../folios/f1r.html"' in column


def test_links_out_to_the_beinecke_image_and_voynich_nu(built):
    folio = (built / "folios" / "f1r.html").read_text()
    assert "https://collections.library.yale.edu/" in folio
    assert "https://www.voynich.nu/" in folio


def test_boundary_check_passes_on_the_built_site(built):
    assert explorer.check_boundary(built, SUMMARY, ["f1r.1", "f1r.2"]) == []


def test_boundary_check_flags_a_transliteration_token_and_an_image(tmp_path):
    (tmp_path / "p.html").write_text("<p>qokedy a0</p>")
    (tmp_path / "i.png").write_bytes(b"png")
    violations = explorer.check_boundary(tmp_path, SUMMARY, ["f1r.1", "f1r.2"])
    assert any("a0" in v for v in violations)
    assert any("image file" in v for v in violations)


def test_boundary_check_masks_locus_ids_but_not_tokens_outside_them(tmp_path):
    # A folio id like f68v3 contains the token-shaped substring v3; that is not a leak.
    (tmp_path / "p.html").write_text('<a href="folios/f68v3.html">folio f68v3</a>')
    assert explorer.check_boundary(tmp_path, SUMMARY, ["f68v3.1"]) == []
    (tmp_path / "q.html").write_text("<p>v3</p>")
    assert any("v3" in v for v in explorer.check_boundary(tmp_path, SUMMARY, ["f68v3.1"]))


def test_rejects_a_tsv_that_carries_readings(tmp_path):
    map_dir = tmp_path / "map"
    map_dir.mkdir()
    (map_dir / "summary.json").write_text(json.dumps(SUMMARY))
    leaky = map_dir / "leaky.tsv"
    leaky.write_text(
        "locus\tcolumn\ttier\tclass\tflag\tcontributing\treadings\tcodes\n"
        "f1r.1\t0\t5\tagree\t\tZL\tZL=a0\tZL=a0\n"
    )
    with pytest.raises(SystemExit, match="header"):
        explorer.read_cells(leaky)
