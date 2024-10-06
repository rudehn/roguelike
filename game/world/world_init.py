"""World initialization."""

from __future__ import annotations

from random import Random

import tcod.ecs

import game.actor_tools
import game.world.procgen
from game.combat.combat_types import DamageType, DamageResistance
from game.components import (
    AIBuilder,
    AttackSpeed,
    CON,
    DEX,
    STR,
    HP,
    Defense,
    DefenseBonus,
    EquipSlot,
    Energy,
    Graphic,
    HPBonus,
    LootDropChance,
    MaxHP,
    MoveSpeed,
    Name,
    Position,
    PowerBonus,
    RacialTrait,
    RacialTraits,
    Resistances,
    Speed,
    StartingEffects,
    RewardXP,
    SpawnWeight,
)
from game.creatures import Creatures
from game.effect import add_effect_to_entity, Effect
from game.effects import Healing, Poisoned, Regeneration
from game.items.item import ApplyAction
from game.items.item_tools import create_new_item, equip_item
from game.items.item_types import EquipmentSlots
from game.items.item_factories import EquipmentItems
from game.items.items import Potion, RandomTargetScroll, TargetScroll
from game.world.map_tools import get_map
from game.ui.messages import MessageLog, add_message
from game.spell import EntitySpell, PositionSpell
from game.spells import Confusion, Fireball, LightningBolt
from game.tags import IsActor, IsEffect, IsEffectSpawner, IsIn, IsItem, IsPlayer, IsTrait, TargetEnemy, TargetSelf


def new_world() -> tcod.ecs.Registry:
    """Return a new world."""
    world = tcod.ecs.Registry()
    world[None].components[Random] = Random()
    world[None].components[MessageLog] = MessageLog()

    init_effects(world)
    init_creatures(world)
    init_items(world)

    map_ = get_map(world, game.world.procgen.Tombs(1))

    (start,) = world.Q.all_of(tags=["UpStairs"], relations=[(IsIn, map_)])

    player = game.actor_tools.spawn_actor(world["player"], start.components[Position])
    player.tags.add(IsPlayer)
    # equip_item(player, create_new_item(world["dagger"]))
    # equip_item(player, create_new_item(world["leather_armor"]))

    game.actor_tools.update_fov(player)

    add_message(world, "Hello and welcome, adventurer, to yet another dungeon!", "welcome_text")
    return world

def init_new_equippable(
    world: tcod.ecs.Registry,
    name: str,
    ch: int,
    fg: tuple[int, int, int],
    equip_slot: EquipmentSlots,
    power_bonus: str | None = None,
    defense_bonus: int | None = None,
    hp_bonus: int | None = None,
    effects_applied: tuple[str] | None = None,
    spawn_weight: tuple[tuple[int, int], ...] | None = None,
):
    equippable = world[name]
    equippable.tags.add(IsItem)
    equippable.components[Name] = name.replace("_", " ").capitalize()
    equippable.components[Graphic] = Graphic(ch, fg)
    equippable.components[EquipSlot] = "weapon" if equip_slot == EquipmentSlots.WEAPON else "armor"
    if power_bonus:
        equippable.components[PowerBonus] = power_bonus
    if defense_bonus:
        equippable.components[DefenseBonus] = defense_bonus
    if hp_bonus:
        equippable.components[HPBonus] = hp_bonus

    if effects_applied:
        equippable.components[StartingEffects] = effects_applied

    if spawn_weight:
        equippable.components[SpawnWeight] = spawn_weight


def init_new_creature(
    world: tcod.ecs.Registry,
    name: str,
    ch: int,
    fg: tuple[int, int, int],
    hp: int,
    str: int,
    con: int,
    dex: int,
    defense: int,
    speed: int,
    attack_speed: float,
    move_speed: float,
    xp: int,
    loot_pct: float,
    damage_type: DamageType,
    resistances: tuple[DamageResistance, ...],
    ai: AIBuilder | None,
    energy: int = 100,
    traits: tuple[RacialTrait, ...] | None = None,
    spawn_weight: tuple[tuple[int, int], ...] | None = None,
) -> None:
    """
    Setup a new creature type.

    Can't init AI here, otherwise instantiated instances cant set the AI to
    """
    race = world[name]
    race.tags.add(IsActor)
    race.components[Name] = name.replace("_", " ")
    race.components[Graphic] = Graphic(ch, fg)
    race.components[Energy] = energy
    race.components[Speed] = speed
    race.components[AttackSpeed] = attack_speed
    race.components[MoveSpeed] = move_speed
    race.components[HP] = race.components[MaxHP] = hp
    race.components[STR] = str
    race.components[DEX] = dex
    race.components[CON] = con
    race.components[DamageType] = damage_type
    race.components[Defense] = defense
    race.components[RewardXP] = xp
    race.components[LootDropChance] = loot_pct

    if resistances:
        race.components[Resistances] = resistances
    if ai:
        race.components[AIBuilder] = ai
    if traits:
        race.components[RacialTraits] = traits
    if spawn_weight:
        race.components[SpawnWeight] = spawn_weight


def init_new_effect(
    world: tcod.ecs.Registry,
    name: str,
    effect_type: Effect,
):
    effect = world[name]
    effect.tags.add(IsEffect)
    effect.components[Name] = name
    effect.components[Effect] = effect_type

def init_effects(world: tcod.ecs.Registry):
    """Initialize the effects database"""

    effect_spawner = world['effect_spawner']
    effect_spawner.tags.add(IsEffectSpawner)

    effects: list[tuple[str, Effect]] = [
        ("lesser_healing", Healing(4)),
        ("healing", Healing(10)),
        ("greater_healing", Healing(20)),
        ("lesser_regeneration", Regeneration(1)),
        ("lesser_poison", Poisoned(amount=1, duration=4)),
        ("poison", Poisoned(amount=2, duration=5)),
        ("greater_poison", Poisoned(amount=3, duration=6)),
    ]
    for (effect_name, effect) in effects:
        init_new_effect(world, effect_name, effect)

def init_creatures(world: tcod.ecs.Registry) -> None:
    """Initialize monster database."""
    for creature in Creatures:
        init_new_creature(
            world,
            name=creature.name,
            ch=creature.ch,
            fg=creature.fg,
            hp=creature.hp,
            str=creature.strength,
            con=creature.constitution,
            dex=creature.dexterity,
            defense=creature.defense,
            speed=creature.speed,
            attack_speed=creature.attack_speed,
            move_speed=creature.move_speed,
            xp=creature.xp,
            loot_pct=creature.loot_drop_pct,
            damage_type=creature.damage_type,
            resistances=creature.resistances,
            ai=creature.ai,
            spawn_weight=creature.spawn_weight,
            traits=creature.traits,
        )


def init_items(world: tcod.ecs.Registry) -> None:
    """Initialize item database."""
    health_potion = world["health_potion"]
    health_potion.tags.add(IsItem)
    health_potion.components[Name] = "Health Potion"
    health_potion.components[Graphic] = Graphic(ord("!"), (127, 0, 255))
    health_potion.components[Effect] = Healing(4)
    health_potion.components[ApplyAction] = Potion()
    health_potion.components[SpawnWeight] = ((1, 35),)

    confusion_scroll = world["confusion_scroll"]
    confusion_scroll.tags.add(IsItem)
    confusion_scroll.components[Name] = "Confusion Scroll"
    confusion_scroll.components[Graphic] = Graphic(ord("~"), (207, 63, 255))
    confusion_scroll.components[ApplyAction] = TargetScroll()
    confusion_scroll.components[PositionSpell] = Confusion(duration=10)
    # confusion_scroll.components[ApplyAction] = RandomTargetScroll(maximum_range=5)
    # confusion_scroll.components[EntitySpell] = Confusion(duration=10)
    confusion_scroll.components[SpawnWeight] = ((2, 10),)

    lightning_scroll = world["lightning_scroll"]
    lightning_scroll.tags.add(IsItem)
    lightning_scroll.components[Name] = "Lightning Scroll"
    lightning_scroll.components[Graphic] = Graphic(ord("~"), (255, 255, 0))
    lightning_scroll.components[ApplyAction] = RandomTargetScroll(maximum_range=5)
    lightning_scroll.components[EntitySpell] = LightningBolt(damage=10)
    lightning_scroll.components[SpawnWeight] = ((3, 10),)

    fireball_scroll = world["fireball_scroll"]
    fireball_scroll.tags.add(IsItem)
    fireball_scroll.components[Name] = "Fireball Scroll"
    fireball_scroll.components[Graphic] = Graphic(ord("~"), (255, 0, 0))
    fireball_scroll.components[ApplyAction] = TargetScroll()
    fireball_scroll.components[PositionSpell] = Fireball(damage=12, radius=3)
    fireball_scroll.components[SpawnWeight] = ((6, 10),)

    for equipment in EquipmentItems:
        init_new_equippable(
            world,
            name=equipment.name,
            ch=equipment.ch,
            fg=equipment.fg,
            equip_slot=equipment.slot,
            power_bonus=equipment.attack_bonus,
            defense_bonus=equipment.defense_bonus,
            hp_bonus=equipment.hp_bonus,
            spawn_weight=equipment.spawn_weight,
        )
