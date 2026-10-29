import numpy as np
from PIL import Image

from voynich_ocr import clusters as cl


def test_crop_pads_to_square_with_the_border_colour_then_resizes():
    page = np.full((100, 200, 3), 200, dtype=np.uint8)
    page[40:60, 50:90] = 20
    out = np.asarray(cl.crop(Image.fromarray(page), [[30, 30], [110, 30], [110, 70], [30, 70]]))
    assert out.shape == (cl.CROP, cl.CROP, 3)
    assert (out[:10] == 200).all() and (out[-10:] == 200).all()
    assert (out[cl.CROP // 2, cl.CROP // 2] < 60).all()


def test_features_are_unit_length():
    page = np.full((64, 64, 3), 255, dtype=np.uint8)
    page[20:40, 10:50] = 0
    feats = cl.hog([Image.fromarray(page), Image.fromarray(page.transpose(1, 0, 2).copy())])
    assert np.allclose(np.linalg.norm(feats, axis=1), 1)


def test_blank_crop_gives_a_zero_feature_not_nan():
    feats = cl.hog([Image.new("RGB", (cl.CROP, cl.CROP), (230, 220, 200))])
    assert not np.isnan(feats).any()



def test_kmeans_fits_in_float64():
    x = np.random.default_rng(0).standard_normal((200, 8)).astype(np.float32)
    assert cl.fit(x, 4).cluster_centers_.dtype == np.float64


def test_k_counts_distinct_tokens_in_the_training_labels_not_the_codec(tmp_path):
    root = tmp_path / "lines"
    (root / "f1r").mkdir(parents=True)
    (root / "codec.json").write_text('{"o0": "\\ue000", "d0": "\\ue001", "z0": "\\ue002", " ": " "}')
    (root / "f1r" / "f1r_1.gt.txt").write_text(" \n")
    (root / "f1r" / "f1r_2.gt.txt").write_text("\n")
    (root / "train.txt").write_text(f"{root}/f1r/f1r_1.png\n")
    (root / "eval.txt").write_text(f"{root}/f1r/f1r_2.png\n")
    assert cl.k(root) == cl.K_PER_TOKEN * 2


def test_hog_of_no_crops_is_an_empty_matrix_of_the_feature_width():
    one = cl.hog([Image.new("RGB", (cl.CROP, cl.CROP), (230, 220, 200))])
    assert cl.hog([]).shape == (0, one.shape[1])
