"""Combat logic."""

from __future__ import annotations

import enum
import logging
from random import Random

import attrs
import tcod.ecs  # noqa: TCH002

from game.components import (
    AI,
    HP,
    XP,
    Defense,
    DefenseBonus,
    EffectsApplied,
    Graphic,
    HPBonus,
    MaxHP,
    Name,
    PowerBonus,
    RewardXP,
    Attack,
)
from game.effect import add_effect_to_entity
from game.ui.messages import add_message
from game.tags import Affecting, EquippedBy, IsAlive, IsBlocking, IsPlayer

logger = logging.getLogger(__name__)

"""
Stat system:
- STR
- DEX
- CON
- INT

Secondary stats:
- hp
- evade
- regen
- accuracy?
- crit chance
- crit damage
- block/armor
- pierce / penetration&protection (attacker penetration beats defender protection), so defence is now halved
    - penetration/protection determined by weapon types

Classes w/ main stats?
- every 2 points increased bonus damage by 1
- every 5 points increases defense by 1
- 10 max health per CON
- 10 max mana per INT
- 0.5% acc per DEX
- 0.5& crit chance per LCK
- lifesteal
- insta death
- min/max damage
- block percentage vs raw number?
- Damage mitigation?
- resistance (physical & elemental)
    - fire/poison/paralize/confuse/fear

- Add speed to determine combat order? multiple moves per turn?
- Luck boosts item generation odds for higher tier loot
- add negative modifiers for equipment? Heavy armor lowers dex, etc
"""
class CombatActionTypes(enum.Enum):
    ATTACK = enum.auto()
    CRIT = enum.auto()
    MISSED = enum.auto()
    BLOCKED = enum.auto()

@attrs.define
class CombatAction:
    damage: int
    action_type: CombatActionTypes


def recalculate_stats(actor: tcod.ecs.Entity):
    pass
    # TODO - need to keep track of base stats + modifiers to base stats
    # max_hp = actor.components.get(MaxHP, 0)

    # for e in actor.registry.Q.all_of(components=[HPBonus], relations=[(Affecting, actor)]):
    #     max_hp += e.components[HPBonus]

    # actor.components[MaxHP] = max_hp


def get_evade_chance(actor: tcod.ecs.Entity) -> float:
    """
    Evade percentage is calculated as follows

    evade = min(.75, (DEX / 2) / 100)

    with dex being the only stat affecting
    """
    # dex = actor.components.get(DEX, 0)
    # evade = min(.75, (dex / 2) / 100)
    return 0

def get_crit_chance(actor: tcod.ecs.Entity) -> float:
    """
    Crit chance percentage is calculated as follows

    crit_chance = min(.75, (DEX + (STR / 4)) / 100)

    with DEX being the primary stat
    """
    # dex = actor.components.get(DEX, 0)
    # str_ = actor.components.get(STR, 0)
    # crit_chance = min(.75, (dex + (str_ / 4) ) / 100)
    return 0

def get_crit_damage_pct(actor: tcod.ecs.Entity) -> float:
    """
    Crit damage percentage is calculated as follows

    crit_damage = (DEX + STR) / 100

    with DEX and STR contributing equally
    """
    # dex = actor.components.get(DEX, 0)
    # str_ = actor.components.get(STR, 0)
    # crit_damage = 1 + ((dex + str_) / 100)
    return 1

def get_min_damage(actor: tcod.ecs.Entity) -> int:
    """
    Min damage is calculated as follows
    power = (STR // 2) + sum(equipment_bonus)
    """

    # min_damage = int(actor.components.get(STR, 0) // 2)

    # for e in actor.registry.Q.all_of(components=[PowerBonus], relations=[(Affecting, actor)]):
    #     min_damage += e.components[PowerBonus]
    return 0

def get_max_damage(actor: tcod.ecs.Entity) -> int:
    """
    Max damage is calculated as follows
    power = STR + sum(equipment_bonus)
    """

    # max_damage = actor.components.get(STR, 0)

    # for e in actor.registry.Q.all_of(components=[PowerBonus], relations=[(Affecting, actor)]):
    #     max_damage += e.components[PowerBonus]
    return 0

def get_attack(actor: tcod.ecs.Entity) -> int:
    """
    Get an entities attack power.
    """
    attack_power = actor.components.get(Attack, 0)
    for e in actor.registry.Q.all_of(components=[PowerBonus], relations=[(Affecting, actor)]):
        attack_power += e.components[PowerBonus]
    return attack_power


def get_defense(actor: tcod.ecs.Entity) -> int:
    """Get an entities defense power."""
    defense_power = actor.components.get(Defense, 0)
    for e in actor.registry.Q.all_of(components=[DefenseBonus], relations=[(Affecting, actor)]):
        defense_power += e.components[DefenseBonus]
    return defense_power


def melee_damage(attacker: tcod.ecs.Entity, target: tcod.ecs.Entity) -> CombatAction:
    """Get melee damage for attacking target."""
    # Calculate if we hit
    rng = attacker.registry[None].components[Random]
    if rng.random() <= get_evade_chance(target):
        return CombatAction(damage=0, action_type=CombatActionTypes.MISSED)

    attack = get_attack(attacker)
    defense = get_defense(target)
    action_type = CombatActionTypes.ATTACK
    # Check for a crit
    if rng.random() <= get_crit_chance(attacker):
        attack = int(attack * get_crit_damage_pct(attacker))
        action_type = CombatActionTypes.CRIT

    damage = max(0, attack - defense)
    if damage == 0:
        action_type = CombatActionTypes.BLOCKED
    else:
        # This grabs all of the attacker's equipment that apply effects
        for effect in attacker.registry.Q.all_of(components=[EffectsApplied], relations=[(EquippedBy, attacker)]):
            equip_effects = effect.components[EffectsApplied]
            print("all effects", equip_effects)
            for equip_effect in equip_effects:
                print("an effect", equip_effect)
                add_effect_to_entity(target, equip_effect)
    return CombatAction(damage=damage, action_type=action_type)

def apply_damage(entity: tcod.ecs.Entity, damage: int, blame: tcod.ecs.Entity) -> None:
    """Deal damage to an entity."""
    entity.components[HP] -= damage
    if entity.components[HP] <= 0:
        die(entity, blame)


def die(entity: tcod.ecs.Entity, blame: tcod.ecs.Entity | None) -> None:
    """Kill an entity."""
    is_player = IsPlayer in entity.tags
    add_message(
        entity.registry,
        text="You died!" if is_player else f"{entity.components[Name]} is dead!",
        fg="player_die" if is_player else "enemy_die",
    )
    if blame:
        blame.components.setdefault(XP, 0)
        blame.components[XP] += entity.components.get(RewardXP, 0)
        add_message(
            entity.registry, f"{blame.components[Name]} gains {entity.components.get(RewardXP, 0)} experience points."
        )

    entity.components[Graphic] = Graphic(ord("%"), (191, 0, 0))
    entity.components[Name] = f"remains of {entity.components[Name]}"
    entity.components.pop(AI, None)
    entity.tags.discard(IsBlocking)
    entity.tags.discard(IsAlive)


def heal(entity: tcod.ecs.Entity, amount: int) -> int:
    """Recover the HP of `entity` by `amount`. Return the actual amount restored."""
    if not (entity.components.keys() >= {HP, MaxHP}):
        logger.info("%r has no HP/MaxHP component", entity)
        return 0
    old_hp = entity.components[HP]
    new_hp = min(old_hp + amount, entity.components[MaxHP])
    entity.components[HP] = new_hp
    return new_hp - old_hp


def poison(entity: tcod.ecs.Entity, amount: int) -> int:
    """Poison the HP of `entity` by `amount`. Return the actual amount poisoned."""
    if not (entity.components.keys() >= {HP, MaxHP}):
        logger.info("%r has no HP/MaxHP component", entity)
        return 0
    old_hp = entity.components[HP]
    new_hp = max(old_hp - amount, 0)
    entity.components[HP] = new_hp
    return old_hp - new_hp
