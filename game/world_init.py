"""World initialization."""

from __future__ import annotations

from random import Random

import tcod.ecs

import game.actor_tools
import game.procgen
from game.components import (
    HP,
    DefenseBonus,
    DEX,
    EquipSlot,
    Graphic,
    HPBonus,
    MaxHP,
    Name,
    Passives,
    Position,
    PowerBonus,
    RewardXP,
    SpawnWeight,
    STR,
)
from game.effect import Effect
from game.effects import Healing
from game.item import ApplyAction
from game.item_tools import equip_item
from game.items import Potion, RandomTargetScroll, TargetScroll
from game.map_tools import get_map
from game.messages import MessageLog, add_message
from game.spell import EntitySpell, PositionSpell
from game.spells import Confusion, Fireball, LightningBolt
from game.tags import IsActor, IsIn, IsItem, IsPlayer


def new_world() -> tcod.ecs.Registry:
    """Return a new world."""
    world = tcod.ecs.Registry()
    world[None].components[Random] = Random()
    world[None].components[MessageLog] = MessageLog()

    init_creatures(world)
    init_items(world)

    map_ = get_map(world, game.procgen.Tombs(1))

    (start,) = world.Q.all_of(tags=["UpStairs"], relations=[(IsIn, map_)])

    player = game.actor_tools.spawn_actor(world["player"], start.components[Position])
    player.tags.add(IsPlayer)
    equip_item(player, world["dagger"].instantiate())
    equip_item(player, world["leather_armor"].instantiate())

    game.actor_tools.update_fov(player)

    add_message(world, "Hello and welcome, adventurer, to yet another dungeon!", "welcome_text")
    return world


def init_new_creature(
    world: tcod.ecs.Registry,
    name: str,
    ch: int,
    fg: tuple[int, int, int],
    hp: int,
    strength: int,
    dexterity: int,
    xp: int,
    passives: tuple[Effect, ...] = (),
    spawn_weight: tuple[tuple[int, int], ...] = (),
) -> None:
    """Setup a new creature type."""
    race = world[name]
    race.tags.add(IsActor)
    race.components[Name] = name
    race.components[Graphic] = Graphic(ch, fg)
    race.components[HP] = race.components[MaxHP] = hp
    race.components[STR] = strength
    race.components[DEX] = dexterity
    race.components[RewardXP] = xp
    if passives:
        race.components[Passives] = passives
    if spawn_weight:
        race.components[SpawnWeight] = spawn_weight


def init_creatures(world: tcod.ecs.Registry) -> None:
    """Initialize monster database."""
    init_new_creature(world, name="player", ch=ord("@"), fg=(255, 255, 255), hp=30, strength=5, dexterity=5, xp=0)
    init_new_creature(
        world, name="orc", ch=ord("o"), fg=(63, 127, 63), hp=10, strength=4, dexterity=0, xp=35, spawn_weight=((1, 80),)
    )
    init_new_creature(
        world,
        name="troll",
        ch=ord("T"),
        fg=(0, 127, 0),
        hp=16,
        strength=8,
        dexterity=1,
        xp=100,
        passives=(Healing(1),),
        spawn_weight=((3, 15), (5, 30), (7, 60)),
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
    confusion_scroll.components[SpawnWeight] = ((1, 25),)

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

    dagger = world["dagger"]
    dagger.tags.add(IsItem)
    dagger.components[Name] = "Dagger"
    dagger.components[Graphic] = Graphic(ord("/"), (0, 191, 255))
    dagger.components[PowerBonus] = 2
    dagger.components[HPBonus] = 20
    dagger.components[EquipSlot] = "weapon"

    sword = world["sword"]
    sword.tags.add(IsItem)
    sword.components[Name] = "Sword"
    sword.components[Graphic] = Graphic(ord("/"), (0, 191, 255))
    sword.components[PowerBonus] = 4
    sword.components[SpawnWeight] = ((4, 5),)
    sword.components[EquipSlot] = "weapon"

    leather_armor = world["leather_armor"]
    leather_armor.tags.add(IsItem)
    leather_armor.components[Name] = "Leather Armor"
    leather_armor.components[Graphic] = Graphic(ord("["), (139, 69, 19))
    leather_armor.components[DefenseBonus] = 1
    leather_armor.components[EquipSlot] = "armor"

    chain_mail = world["chain_mail"]
    chain_mail.tags.add(IsItem)
    chain_mail.components[Name] = "Chain Mail"
    chain_mail.components[Graphic] = Graphic(ord("["), (139, 69, 19))
    chain_mail.components[DefenseBonus] = 3
    chain_mail.components[SpawnWeight] = ((6, 15),)
    chain_mail.components[EquipSlot] = "armor"
