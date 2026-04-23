from pokequiz.games.statle import remaining_stats


def test_remaining_stats_excludes_used():
    remaining = remaining_stats(["attack", "speed"])
    assert "attack" not in remaining
    assert "speed" not in remaining
    assert len(remaining) == 4
