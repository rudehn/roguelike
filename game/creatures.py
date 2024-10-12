"""
Holds the definition of all creatures in the game
"""
from typing import Callable, Final, Tuple

import attrs

from game.action import Action
from game.combat.ai import HostileAI, SpawnerAI
from game.combat.combat_types import DamageType, DamageResistance, ResistanceLevel
from game.components import BaseAI, RacialTrait
from game.constants import TraitActivation, TraitTarget
from game.effect import Effect
from game.effects import Regeneration
from game.components import AIBuilder


# TODO - add validation here
@attrs.define
class Creature:
    name: str
    ch: int
    fg: Tuple[int, int, int]
    hp: int
    strength: int
    constitution: int
    dexterity: int
    defense: int
    xp: int
    speed: int = attrs.field(kw_only=True, default=10) # How quickly energy replenishes for this entity
    attack_speed: float = attrs.field(kw_only=True, default=1) # Speed multiplier for attack action cost. 0.5 is 2x cost
    move_speed: float = attrs.field(kw_only=True, default=1) # Speed multiplier for move action cost. 0.5 is 2x cost
    loot_drop_pct: float = attrs.field(kw_only=True, default=.25)
    spawn_weight: Tuple[Tuple[int, int], ...] = attrs.field(kw_only=True, default=None)
    damage_type: DamageType = attrs.field(kw_only=True, default=DamageType.PHYSICAL)
    resistances: Tuple[DamageResistance, ...] = attrs.field(kw_only=True, factory=tuple)
    ai: AIBuilder | None = attrs.field(kw_only=True, default=AIBuilder(HostileAI))
    # ai: Callable[[], BaseAI] | None = attrs.field(kw_only=True, factory=lambda: HostileAI)
    traits: Tuple[RacialTrait] = attrs.field(kw_only=True, default=None)


"""
Stats

STR - +1 attack, +5% crit damage
CON - +5 health
DEX - +1% crit chance, +1% dodge chance, +10% crit damage

Secondary stats:
crit chance
crit damage
dodge
resistance
attack speed
movement speed
health regen
drop chance
armor
armor pierce
armor protection (roll pierce vs protect, 1 succeed reduce armor by 1/2, 2 succeed reduce to 0)

Do we need a base HP value?
health on level up?

Each enemy should have a unique feel. A combination of stats + (future) skills that defines who that enemy is
For example, rats swarm and do little damage, trolls regenerate, etc

Some ideas:
* spawners should be hard to kill, spawn less frequently and be on the wall (like a rats nest)
* Slow enemy that deals huge damage
* Enemy with double attack
* a defensive tank
* a buffer that stays away from the player, groups with other creatures and provides some buff
* A ranged attacker
* A healer
* An invisible attacker, becomes visible on attack
* An enemy with enhanced movement speed
"""

Creatures: Final = (
    Creature("player", ord("@"), (255, 255, 255), 20, 5, 5, 5, 0, 0, ai=None, loot_drop_pct=0),
    Creature("rat", ord("r"), (63, 200, 63), 4, 2, 1, 2, 0, 5, spawn_weight=((1, 50),(3, 25), (5, 0))),
    Creature("orc", ord("o"), (63, 127, 63), 6, 4, 2, 2, 0, 10, spawn_weight=((1, 50),(3, 70), (5, 90), (8, 40))),
    Creature("rat_nest", ord("S"), (63, 127, 63), 10, 0, 2, 0, 0, 12, spawn_weight=((2, 20), (3, 40), (4, 60), (5, 80), (6, 60), (8, 30), (10, 0)),
             ai=AIBuilder(SpawnerAI, {"spawned_entity_name": "rat", "spawn_rate": 4})),
    Creature("troll", ord("T"), (0, 127, 0), 16, 6, 4, 1, 0, 50, spawn_weight=((6, 5), (7, 15), (8, 30)),
             traits=(RacialTrait("lesser_regeneration", TraitTarget.SELF, TraitActivation.ON_CREATE),)),
    Creature("troll_cave", ord("S"), (0, 127, 0), 20, 0, 5, 0, 0, 75, spawn_weight=((6, 10), (8, 20), (12, 10), (15, 0)),
             ai=AIBuilder(SpawnerAI, {"spawned_entity_name": "troll", "spawn_rate": 20})),
    Creature("acid_slime", ord("a"), (0, 200, 0), 8, 4, 2, 1, 0, 10, damage_type=DamageType.POISON,
             resistances=(DamageResistance(DamageType.POISON, ResistanceLevel.IMMUNE),),spawn_weight=((3, 5), (6, 15), (10, 30)),
             traits=(RacialTrait("lesser_poison", TraitTarget.ENEMY, TraitActivation.ON_ATTACK),)),
    Creature("mama_acid_slime", ord("S"), (0, 200, 0), 20, 0, 5, 1, 0, 75, spawn_weight=((8, 5), (10, 10), (12, 15), (18, 0)),
             ai=AIBuilder(SpawnerAI, {"spawned_entity_name": "acid_slime", "spawn_rate": 10})),
    Creature("dragon", ord("D"), (200, 50, 50), 40, 12, 8, 10, 4, 250, damage_type=DamageType.FIRE, resistances=(DamageResistance(DamageType.FIRE, ResistanceLevel.IMMUNE),) )
)



# @attrs.define
# class Creature:
#     name: str
#     ch: int
#     fg: Tuple[int, int, int]
#     hp: int
#     attack: int
#     defense: int
#     xp: int
#     speed: int = attrs.field(kw_only=True, default=100)
#     loot_drop_pct: float = attrs.field(kw_only=True, default=.25)
#     spawn_weight: Tuple[Tuple[int, int], ...] = attrs.field(kw_only=True, default=None)
#     ai: AIBuilder | None = attrs.field(kw_only=True, default=AIBuilder(HostileAI))
#     # ai: Callable[[], BaseAI] | None = attrs.field(kw_only=True, factory=lambda: HostileAI)
#     traits: Tuple[RacialTrait] = attrs.field(kw_only=True, default=None)


# Creatures: Final = (
#     Creature("player", ord("@"), (255, 255, 255), 10, 3, 0, 0, ai=None, loot_drop_pct=0),
#     Creature("rat", ord("r"), (63, 127, 63), 2, 1, 0, 4, loot_drop_pct=0.05, spawn_weight=((1, 50),(3, 25), (5, 0))),
#     Creature("orc", ord("o"), (63, 127, 63), 6, 2, 0, 8, spawn_weight=((1, 50),(3, 70), (5, 90), (8, 40))),
#     Creature("rat_nest", ord("S"), (63, 127, 63), 10, 0, 0, 12, spawn_weight=((2, 20), (3, 40), (4, 60), (5, 80), (6, 60), (8, 30), (10, 0)),
#              ai=AIBuilder(SpawnerAI, {"spawned_entity_name": "rat", "spawn_rate": 4})),
#     Creature("troll", ord("T"), (0, 127, 0), 25, 3, 0, 100, spawn_weight=((4, 5), (5, 15), (7, 30)),
#              traits=(RacialTrait("lesser_regeneration", TraitTarget.SELF, TraitActivation.ON_CREATE),)),
#     Creature("troll_cave", ord("S"), (0, 127, 0), 30, 0, 0, 150, spawn_weight=((6, 10), (8, 20), (12, 10), (15, 0)),
#              ai=AIBuilder(SpawnerAI, {"spawned_entity_name": "troll", "spawn_rate": 15})),
#     Creature("acid_slime", ord("a"), (0, 200, 0), 8, 3, 0, 50, spawn_weight=((3, 5), (6, 15), (10, 30)),
#              traits=(RacialTrait("lesser_poison", TraitTarget.ENEMY, TraitActivation.ON_ATTACK),)),
#     Creature("mama_acid_slime", ord("S"), (0, 200, 0), 30, 0, 0, 150, spawn_weight=((8, 5), (10, 10), (12, 15), (18, 0)),
#              ai=AIBuilder(SpawnerAI, {"spawned_entity_name": "acid_slime", "spawn_rate": 8})),
#     # Creature("snake", ord("s"), (63, 127, 63), 10, 3, 0, 200, 35, spawn_weight=((2, 80),)),
# )
