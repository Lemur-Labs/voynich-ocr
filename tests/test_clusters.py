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
