from voynich_ocr import naibbe


def test_a_plaintext_token_matches_its_decryption_or_one_of_the_listed_options():
    assert naibbe.consistent("in te (ra|ar*) a", "in te ar a")
    assert naibbe.consistent("(in ga*|ing)", "ing")


def test_a_plaintext_token_absent_from_the_options_or_a_different_token_count_is_inconsistent():
    assert not naibbe.consistent("in (ra|ar*)", "in ta")
    assert not naibbe.consistent("in te", "in te a")
