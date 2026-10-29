import json

from voynich_ocr import g1


def _page(tmp_path, page, n_dis, n_agree, token="o0"):
    ms = [{"page": page, "token": token, "class": "disagree", "gated": True}] * n_dis
    ms += [{"page": page, "token": token, "class": "agree", "gated": True}] * n_agree
    ms += [{"page": page, "token": token, "class": "disagree", "gated": False}] * 50
    (tmp_path / f"{page}.json").write_text(json.dumps({"instances": ms}))


def test_pipeline_coverage_draws_only_non_test_pages_of_gated_instances(tmp_path):
    for i in range(6):
        _page(tmp_path, f"f{i}r", 5, 10)
    _page(tmp_path, "f9r", 0, 1, token="x0")
    out = g1.pipeline_coverage(tmp_path, test={"f9r"}, pages=4, draws=5)
    assert out["eligible"] == 6
    assert out["within_type_p5_p50_p95"] == [1.0, 1.0, 1.0]
    assert out["within_page_p5_p50_p95"] == [0.0, 0.0, 0.0]
