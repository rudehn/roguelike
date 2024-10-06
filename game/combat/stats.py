import tcod.ecs

from game.components import CON, Defense, DefenseBonus, DEX, HP, MaxHP, PowerBonus, STR
from game.tags import Affecting
from game.dice import roll_from_notation

def get_current_health(entity: tcod.ecs.Entity):
    return entity.components.get(HP, 0)

def get_max_health(entity: tcod.ecs.Entity):
    return entity.components.get(MaxHP, 0)

def get_base_strength(entity: tcod.ecs.Entity):
    # 1 STR = 1 Attack power; physical damage, crit damage
    return entity.components.get(STR, 0)

def get_derived_strength(entity: tcod.ecs.Entity):
    base_str = get_base_strength(entity)
    return base_str

def get_attack(entity: tcod.ecs.Entity):
    # Attack is based on strength. 1 STR = 1 attack
    base_attack = get_derived_strength(entity)

    # TODO - should weapons stack on top of base damage?
    # TODO - weapons should roll dice too
    for e in entity.registry.Q.all_of(components=[PowerBonus], relations=[(Affecting, entity)]):
        base_attack += roll_from_notation(e.components[PowerBonus])
    return base_attack


def get_defense(actor: tcod.ecs.Entity) -> int:
    """Get an entities defense power."""
    defense_power = actor.components.get(Defense, 0)
    for e in actor.registry.Q.all_of(components=[DefenseBonus], relations=[(Affecting, actor)]):
        defense_power += e.components[DefenseBonus]
    return defense_power

def get_base_dexterity(entity: tcod.ecs.Entity):
    # 1 dex = increase crit chance, attack speed, move speed, dodge
    return entity.components.get(DEX, 0)

def get_derived_dexterity(entity: tcod.ecs.Entity):
    return entity.components.get(DEX, 0)

def get_crit_chance(entity: tcod.ecs.Entity):
    # Crit chance is 2% * dex
    # Return a value between [0-1 ]
    dex = get_derived_dexterity(entity)
    return .02 * dex

def get_crit_damage(entity: tcod.ecs.Entity):
    """
    Crit damage is heavily based on strength, and slightly on dex
    Return a multiplier for damage. Ex 2.0 is 200% more damage
    """
    str_ = get_derived_strength(entity)
    dex = get_derived_dexterity(entity)

    return 1 + (.1 * str_) + (.05 * dex)




def get_base_constitution(entity: tcod.ecs.Entity):
    # 1 CON = increase health, health regen?, resilience?
    return entity.components.get(CON, 0)

def get_derived_constitution(entity: tcod.ecs.Entity):
    return entity.components.get(CON, 0)


def recalculate_stats(actor: tcod.ecs.Entity):
    pass
    # TODO - need to keep track of base stats + modifiers to base stats
    # max_hp = actor.components.get(MaxHP, 0)

    # for e in actor.registry.Q.all_of(components=[HPBonus], relations=[(Affecting, actor)]):
    #     max_hp += e.components[HPBonus]

    # actor.components[MaxHP] = max_hp

def get_entity_with_stat_preview(actor: tcod.ecs.Entity, *,
                                 str_: int| None = None,
                                 con: int | None = None,
                                 dex: int | None = None):
    clone = actor.instantiate()
    if str_:
        clone.components[STR] = str_
    if con:
        clone.components[CON] = con
    if dex:
        clone.components[DEX] = dex
    return clone
