"""
Holds the definition of all creatures in the game
"""
from typing import Final, Tuple

import attrs

from game.effect import Effect
from game.effects import Healing

@attrs.define
class Creature:
    name: str
    ch: int
    fg: Tuple[int, int, int]
    hp: int
    attack: int
    defense: int
    xp: int
    spawn_weight: Tuple[Tuple[int, int], ...] = attrs.field(kw_only=True, default=None)
    passives: Tuple[Effect] = attrs.field(kw_only=True, default=None)

Creatures: Final = (
    Creature("player", ord("@"), (255, 255, 255), 30, 5, 1, 0),
    Creature("orc", ord("o"), (63, 127, 63), 10, 3, 0, 35, spawn_weight=((1, 80),)),
    Creature("troll", ord("T"), (0, 127, 0), 16, 5, 1, 100, spawn_weight=((3, 15), (5, 30), (7, 60)), passives=(Healing(1),))
)
