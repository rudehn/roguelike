"""World initialization."""

from __future__ import annotations

from random import Random
from typing import List

import tcod.ecs

import game.actor_tools
import game.world.procgen
from game.components import (
    AIBuilder,
    HP,
    Defense,
    DefenseBonus,
    EffectsApplied,
    EquipSlot,
    Energy,
    Graphic,
    HPBonus,
    MaxHP,
    Name,
    Position,
    PowerBonus,
    Speed,
    StartingEffects,
    RewardXP,
    SpawnWeight,
    Attack,
)
from game.creatures import Creatures
from game.effect import add_effect_to_entity, Effect
from game.effects import Healing, Poisoned, Regeneration
from game.item import ApplyAction
from game.item_tools import equip_item
from game.items import Potion, RandomTargetScroll, TargetScroll
from game.world.map_tools import get_map
from game.ui.messages import MessageLog, add_message
from game.spell import EntitySpell, PositionSpell
from game.spells import Confusion, Fireball, LightningBolt
from game.tags import IsActor, IsEffect, IsIn, IsItem, IsPlayer


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
    equip_item(player, world["dagger"].instantiate())
    equip_item(player, world["leather_armor"].instantiate())

    game.actor_tools.update_fov(player)

    add_message(world, "Hello and welcome, adventurer, to yet another dungeon!", "welcome_text")
    return world


def init_new_equippable(
    world: tcod.ecs.Registry,
    name: str,
    ch: int,
    fg: tuple[int, int, int],
    equip_slot: str,
    power_bonus: int | None = None,
    defense_bonus: int | None = None,
    hp_bonus: int | None = None,
    effects_applied: tuple[str] | None = None,
    spawn_weight: tuple[tuple[int, int], ...] | None = None,
):
    equippable = world[name]
    equippable.tags.add(IsItem)
    equippable.components[Name] = name.replace("_", " ").capitalize()
    equippable.components[Graphic] = Graphic(ch, fg)
    equippable.components[EquipSlot] = equip_slot
    if power_bonus:
        equippable.components[PowerBonus] = power_bonus
    if defense_bonus:
        equippable.components[DefenseBonus] = defense_bonus
    if hp_bonus:
        equippable.components[HPBonus] = hp_bonus
    if effects_applied:
        # TODO - verify all specified are effects
        equippable.components[EffectsApplied] = tuple(map(lambda e: world[e], [e for e in effects_applied]))

    if spawn_weight:
        equippable.components[SpawnWeight] = spawn_weight


def init_new_creature(
    world: tcod.ecs.Registry,
    name: str,
    ch: int,
    fg: tuple[int, int, int],
    hp: int,
    attack: int,
    defense: int,
    speed: int,
    xp: int,
    ai: AIBuilder | None,
    energy: int = 100,
    passives: tuple[str, ...] | None = None,
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
    race.components[HP] = race.components[MaxHP] = hp
    race.components[Attack] = attack
    race.components[Defense] = defense
    race.components[RewardXP] = xp
    if ai:
        race.components[AIBuilder] = ai
    if passives:
        race.components[StartingEffects] = passives
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
    effects = [
        ("lesser_healing", Healing(4)),
        ("healing", Healing(10)),
        ("greater_healing", Healing(20)),
        ("lesser_regeneration", Regeneration(1)),
        ("lesser_poison", Poisoned(amount=1, duration=4)),
        ("poison", Poisoned(amount=2, duration=5)),
        ("greater_poison", Poisoned(amount=3, duration=6)),
    ]
    for effect in effects:
        init_new_effect(world, effect[0], effect[1])

def init_creatures(world: tcod.ecs.Registry) -> None:
    """Initialize monster database."""
    for creature in Creatures:
        init_new_creature(
            world,
            name=creature.name,
            ch=creature.ch,
            fg=creature.fg,
            hp=creature.hp,
            attack=creature.attack,
            defense=creature.defense,
            speed=creature.speed,
            xp=creature.xp,
            ai=creature.ai,
            spawn_weight=creature.spawn_weight,
            passives=creature.passives,
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
    confusion_scroll.components[SpawnWeight] = ((2, 25),)

    lightning_scroll = world["lightning_scroll"]
    lightning_scroll.tags.add(IsItem)
    lightning_scroll.components[Name] = "Lightning Scroll"
    lightning_scroll.components[Graphic] = Graphic(ord("~"), (255, 255, 0))
    lightning_scroll.components[ApplyAction] = RandomTargetScroll(maximum_range=5)
    lightning_scroll.components[EntitySpell] = LightningBolt(damage=20)
    lightning_scroll.components[SpawnWeight] = ((3, 25),)

    fireball_scroll = world["fireball_scroll"]
    fireball_scroll.tags.add(IsItem)
    fireball_scroll.components[Name] = "Fireball Scroll"
    fireball_scroll.components[Graphic] = Graphic(ord("~"), (255, 0, 0))
    fireball_scroll.components[ApplyAction] = TargetScroll()
    fireball_scroll.components[PositionSpell] = Fireball(damage=12, radius=3)
    fireball_scroll.components[SpawnWeight] = ((6, 25),)

    equippables = (
        ("dagger", ord("/"), (0, 191, 255), "weapon", )
    )

    init_new_equippable(
        world=world,
        name="dagger",
        ch=ord("/"),
        fg=(0, 191, 255),
        equip_slot="weapon",
        power_bonus=2,
        hp_bonus=20,
        effects_applied=("lesser_poison",)
    )
    init_new_equippable(
        world=world,
        name="sword",
        ch=ord("/"),
        fg=(0, 191, 255),
        equip_slot="weapon",
        power_bonus=4,
        spawn_weight=((4, 5),)
    )
    init_new_equippable(
        world=world,
        name="sword",
        ch=ord("/"),
        fg=(0, 191, 255),
        equip_slot="weapon",
        power_bonus=4,
        hp_bonus=20,
        spawn_weight=((4, 5),)
    )

    init_new_equippable(
        world=world,
        name="leather_armor",
        ch=ord("["),
        fg=(139, 69, 19),
        equip_slot="armor",
        defense_bonus=1,
    )
    init_new_equippable(
        world=world,
        name="chain_mail",
        ch=ord("["),
        fg=(139, 69, 19),
        equip_slot="armor",
        defense_bonus=3,
        spawn_weight=((6, 15),)
    )
