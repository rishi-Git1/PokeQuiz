from pokequiz.data import _introduced_gen


def test_mega_is_gen_6():
    is_mega, is_regional, gen, region = _introduced_gen("charizard-mega-x", 1)
    assert is_mega is True
    assert is_regional is False
    assert gen == 6
    assert region is None


def test_regional_uses_debut_gen():
    is_mega, is_regional, gen, region = _introduced_gen("meowth-galar", 1)
    assert is_mega is False
    assert is_regional is True
    assert gen == 8
    assert region == "galar"
