"""
Holds the definition of all creatures in the game
"""
from typing import Callable, Final, Tuple

import attrs

from game.components import RacialTrait
from game.constants import TraitActivation, TraitTarget
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
    traits: Tuple[RacialTrait] = attrs.field(kw_only=True, default=None)


Creatures: Final = (
    Creature("player", ord("@"), (255, 255, 255), 30, 3, 0, 100, 0, ai=None),
    Creature("rat", ord("r"), (63, 127, 63), 2, 2, 0, 100, 4, spawn_weight=((1, 50),(3, 25), (5, 0))),
    Creature("orc", ord("o"), (63, 127, 63), 8, 4, 0, 100, 8, spawn_weight=((1, 50),(3, 70), (5, 90), (8, 40))),
    Creature("rat_nest", ord("S"), (63, 127, 63), 10, 0, 0, 100, 12, spawn_weight=((2, 20), (3, 40), (4, 60), (5, 80)), ai=AIBuilder(SpawnerAI, {"spawned_entity_name": "rat", "spawn_rate": 4})),
    Creature("troll", ord("T"), (0, 127, 0), 25, 3, 0, 100, 100, spawn_weight=((4, 5), (5, 15), (7, 40)),
             traits=(RacialTrait("lesser_regeneration", TraitTarget.SELF, TraitActivation.ON_CREATE),))
    # Creature("snake", ord("s"), (63, 127, 63), 10, 3, 0, 200, 35, spawn_weight=((2, 80),)),
)
