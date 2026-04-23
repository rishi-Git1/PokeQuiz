from pokequiz.games.squirdle import compare_guess, type_slot
from pokequiz.models import Pokemon


def _mon(
    name: str,
    types: tuple[str, ...],
    *,
    gen: int = 1,
    hp: int = 39,
    atk: int = 52,
    defe: int = 43,
    spa: int = 60,
    spd: int = 50,
    spe: int = 65,
    h: int = 6,
    w: int = 85,
) -> Pokemon:
    return Pokemon(
        1,
        name,
        gen,
        types,
        hp,
        atk,
        defe,
        spa,
        spd,
        spe,
        h,
        w,
        aliases=(name,),
    )


def test_pure_fire_vs_fire_flying_slots():
    charmander = _mon("charmander", ("fire",))
    charizard = _mon("charizard", ("fire", "flying"))
    fb = compare_guess(charmander, charizard)
    assert fb["type_1"] == "correct"
    assert fb["type_2"] == "incorrect"


def test_mono_secondary_category_matches():
    a = _mon("a", ("water",))
    b = _mon("b", ("water",))
    fb = compare_guess(a, b)
    assert fb["type_1"] == "correct"
    assert fb["type_2"] == "correct"


def test_dual_type_both_wrong_order():
    # Positional: rock/dark vs dark/rock
    tyranitar = _mon("tyranitar", ("rock", "dark"))
    other = _mon("other", ("dark", "rock"))
    fb = compare_guess(tyranitar, other)
    assert fb["type_1"] == "incorrect"
    assert fb["type_2"] == "incorrect"


def test_type_slot_sentinel_distinct_from_real_type():
    mono = _mon("m", ("fire",))
    assert type_slot(mono, 1) != "flying"
