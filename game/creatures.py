"""
Holds the definition of all creatures in the game
"""
from typing import Callable, Final, Tuple

import attrs

from game.effect import Effect
from game.effects import Regeneration
from game.components import AIBuilder
from game.actions import Action, BaseAI, HostileAI, SpawnerAI

@attrs.define
class Creature:
    name: str
    ch: int
    fg: Tuple[int, int, int]
    hp: int
    attack: int
    defense: int
    speed: int
    xp: int
    spawn_weight: Tuple[Tuple[int, int], ...] = attrs.field(kw_only=True, default=None)
    ai: AIBuilder | None = attrs.field(kw_only=True, default=AIBuilder(HostileAI))
    # ai: Callable[[], BaseAI] | None = attrs.field(kw_only=True, factory=lambda: HostileAI)
    passives: Tuple[str] = attrs.field(kw_only=True, default=None)


Creatures: Final = (
    Creature("player", ord("@"), (255, 255, 255), 30, 5, 0, 100, 0, ai=None),
    Creature("rat", ord("r"), (63, 127, 63), 4, 1, 0, 100, 3, spawn_weight=((3, 100),)),
    Creature("rat_nest", ord("S"), (63, 127, 63), 10, 1, 0, 100, 3, spawn_weight=((1, 100),), ai=AIBuilder(SpawnerAI, {"spawned_entity_name": "rat", "spawn_rate": 3})),
    Creature("troll", ord("T"), (0, 127, 0), 16, 5, 1, 100, 100, spawn_weight=((1, 100), (5, 30), (7, 60)), passives=("lesser_regeneration",))
    # Creature("orc", ord("o"), (63, 127, 63), 10, 3, 0, 50, 35, spawn_weight=((2, 80),)),
    # Creature("snake", ord("s"), (63, 127, 63), 10, 3, 0, 200, 35, spawn_weight=((2, 80),)),
)
