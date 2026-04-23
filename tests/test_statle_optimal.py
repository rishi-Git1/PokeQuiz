from pokequiz.games.statle import STAT_NAMES, format_optimal_statle_summary, optimal_statle_assignment
from pokequiz.models import Pokemon


def _m(name: str, hp: int, attack: int, defense: int, spa: int, spd: int, spe: int) -> Pokemon:
    return Pokemon(1, name, 1, ("normal",), hp, attack, defense, spa, spd, spe, 1, 1, aliases=(name,))


def test_optimal_hits_each_specialized_round():
    # Round i's Pokémon is strongest in STAT_NAMES[i].
    rounds = [
        _m("r0", 100, 1, 1, 1, 1, 1),
        _m("r1", 1, 100, 1, 1, 1, 1),
        _m("r2", 1, 1, 100, 1, 1, 1),
        _m("r3", 1, 1, 1, 100, 1, 1),
        _m("r4", 1, 1, 1, 1, 100, 1),
        _m("r5", 1, 1, 1, 1, 1, 100),
    ]
    total, plan = optimal_statle_assignment(rounds)
    assert total == 600
    assert plan == list(STAT_NAMES)


def test_format_summary_contains_lines():
    rounds = [
        _m("r0", 10, 1, 1, 1, 1, 1),
        _m("r1", 1, 10, 1, 1, 1, 1),
        _m("r2", 1, 1, 10, 1, 1, 1),
        _m("r3", 1, 1, 1, 10, 1, 1),
        _m("r4", 1, 1, 1, 1, 10, 1),
        _m("r5", 1, 1, 1, 1, 1, 10),
    ]
    tot, plan = optimal_statle_assignment(rounds)
    text = format_optimal_statle_summary(rounds, plan, tot, your_total=12)
    assert "Best possible" in text
    assert "room to gain" in text
    assert "Round 1" in text
