from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Pokemon:
    """Canonical in-memory representation for quiz gameplay."""

    dex_number: int
    name: str
    generation: int
    types: tuple[str, ...]
    hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int
    height_dm: int
    weight_hg: int
    is_mega: bool = False
    is_regional_variant: bool = False
    variant_region: str | None = None
    introduced_generation: int | None = None
    aliases: tuple[str, ...] = field(default_factory=tuple)

    @property
    def bst(self) -> int:
        return (
            self.hp
            + self.attack
            + self.defense
            + self.special_attack
            + self.special_defense
            + self.speed
        )

    @property
    def all_names(self) -> set[str]:
        return {self.name.casefold(), *(a.casefold() for a in self.aliases)}


@dataclass(slots=True)
class GameSettings:
    allow_megas: bool = True
    allow_regionals: bool = True
    allowed_generations: set[int] | None = None
    mute_bgm: bool = False
    mute_input_sfx: bool = False
    mute_completion_sfx: bool = False
    mute_low_health_sfx: bool = False

    def accepts(self, mon: Pokemon) -> bool:
        if not self.allow_megas and mon.is_mega:
            return False
        if not self.allow_regionals and mon.is_regional_variant:
            return False
        if self.allowed_generations is not None and mon.generation not in self.allowed_generations:
            return False
        return True
