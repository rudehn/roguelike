"""Combat logic."""

from __future__ import annotations

import enum
import logging
from random import Random

import attrs
import tcod.ecs  # noqa: TCH002

from game.combat.combat_types import AttackData, DamageType, ResistanceLevel
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
    Resistances,
    RewardXP,
    TraitActivation,
    TraitTarget,
    Attack,
)
from game.dice import roll, roll_from_notation
from game.effect import add_effect_to_entity
from game.ui.messages import add_message
from game.tags import Affecting, EquippedBy, IsAlive, IsBlocking, IsEffectSpawner, IsPlayer

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


def perform_attack(attacker: tcod.ecs.Entity, defender: tcod.ecs.Entity, attack: AttackData):
    rng = attacker.registry[None].components[Random]

    # First roll a d20 to see if we auto crit/miss
    # Crit is an auto-hit, allowing lower level monsters to still provide a threat
    # to the player
    to_hit = roll(1, 20)
    is_crit = False
    attack_color = "player_atk" if IsPlayer in attacker.tags else "enemy_atk"
    attack_desc = f"""{attacker.components[Name]} attacks {defender.components[Name]}"""

    if to_hit == 1:
        add_message(attacker.registry, f"{attack_desc} but missed.", attack_color)
        return

    # TODO roll 2d20, multiply then multiply by accuracy. Compare to 2d20, multiply then multiply by evasion
    if to_hit == 20:
        is_crit = True

    # Crit doubles the damage
    damage = attack.damage_amount * 2 if is_crit else attack.damage_amount
    resistance = get_resistance_level(defender, attack.damage_type)
    match resistance:
        case ResistanceLevel.WEAK:
            damage *= 1.5 # 50% more damage
        case ResistanceLevel.MODERATE:
            damage *= .66 # 33% less damage
        case ResistanceLevel.HIGH:
            damage *= .33 # 66% less damage
        case ResistanceLevel.IMMUNE:
            add_message(attacker.registry, f"{attack_desc} but it is immune to this damage!", attack_color)
            return
        case ResistanceLevel.HEALED:
            healed_amount = heal(defender, int(damage * .33)) # Heal for 33% of damage
            add_message(attacker.registry, f"{attack_desc} but it healed for {healed_amount} hp!", attack_color)
            return
        case ResistanceLevel.NONE:
            pass

    # Calculate armor value, cap at 75% damage mitigation, will at least apply 1 damage
    defense = get_defense(defender)
    damage = int(max(1, damage*.25, damage-defense))
    if is_crit:
        add_message(attacker.registry, f"{attack_desc} and crits for {damage} hit points!", attack_color)
    else:
        add_message(attacker.registry, f"{attack_desc} for {damage} hit points.", attack_color)

    apply_damage(defender, damage, blame=attacker)

    # TODO - miss chance accuracy/evade
    # TODO - inflict status type based on damage type; modify chance by resistance
    # TODO - how do we determine status power? Assign a tier to creatures? Roll to hit, then roll for severity?
    # - function to look up entities that inflict that status type; need to update entity to include type?
    # TODO - damage should be a dice roll
    # - how to determine player base damage w/ no weapon?
    # How to determine if weapon applies a status effect?




def get_resistance_level(actor: tcod.ecs.Entity, damage_type: DamageType) -> ResistanceLevel:
    resistances = actor.components.get(Resistances, ())
    resistance_level = ResistanceLevel.NONE

    # Now check if we have a resistance to the damage type specified
    for res in resistances:
        if res.damage_type == damage_type:
            resistance_level = res.resistance
            break

    return resistance_level

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

def get_attack(actor: tcod.ecs.Entity) -> int:
    """
    Get an entities attack power.
    """
    attack_power = roll_from_notation(actor.components.get(Attack, "0d1"))

    # TODO - should weapons stack on top of base damage?
    # TODO - weapons should roll dice too
    for e in actor.registry.Q.all_of(components=[PowerBonus], relations=[(Affecting, actor)]):
        attack_power += roll_from_notation(e.components[PowerBonus])
    return attack_power


def get_defense(actor: tcod.ecs.Entity) -> int:
    """Get an entities defense power."""
    defense_power = actor.components.get(Defense, 0)
    for e in actor.registry.Q.all_of(components=[DefenseBonus], relations=[(Affecting, actor)]):
        defense_power += e.components[DefenseBonus]
    return defense_power


def melee_damage(attacker: tcod.ecs.Entity, target: tcod.ecs.Entity):
    """Get melee damage for attacking target."""
    # Calculate if we hit
    attack = get_attack(attacker)
    perform_attack(attacker, target, AttackData(DamageType.PHYSICAL, attack))

    # # This grabs all of the attacker's equipment that apply effects
    # for effect in attacker.registry.Q.all_of(components=[EffectsApplied], relations=[(EquippedBy, attacker)]):
    #     equip_effects = effect.components[EffectsApplied]
    #     for equip_effect in equip_effects:
    #         add_effect_to_entity(target, equip_effect)

    # # This grabs all the racial traits that spawn an effect on attack
    # for effect_spawner in attacker.registry.Q.all_of(components=[TraitActivation, TraitTarget], tags=[IsEffectSpawner, TraitActivation.ON_ATTACK], relations=[(Affecting, attacker)]):
    #     target_type = effect_spawner.components[TraitTarget]
    #     effects = effect_spawner.components[EffectsApplied]
    #     for effect in effects:
    #         match target_type:
    #             case TraitTarget.SELF:
    #                 add_effect_to_entity(attacker, effect)

    #             case TraitTarget.ENEMY:
    #                 add_effect_to_entity(target, effect)

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
