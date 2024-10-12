"""Common entity components."""

from __future__ import annotations

from typing import Any, Callable, Dict, Final, NamedTuple, NewType, Protocol, Self

import attrs
import numpy as np
import tcod.ecs
import tcod.ecs.callbacks
from numpy.typing import NDArray

from game.action import Action, ActionResult
from game.combat.combat_types import DamageResistance
from game.constants import TraitActivation, TraitTarget
from game.effect import Effect
from game.tags import IsIn, IsItem, IsPlayer

# TODO - refactor
class BaseAI(Protocol):

    __slots__ = ()

    def get_action(self, actor: tcod.ecs.Entity) -> Action:
        """Get the next action the AI wants to perform"""
        ...

    def perform_action(self, action: Action, actor: tcod.ecs.Entity) -> ActionResult:
        """Perform the action & handle any cleanup code that needs to run"""
        ...

@attrs.define
class AIBuilder:
    """Create an Action (AI) instance from an action class + parameters"""
    ai: type[BaseAI]
    kwargs: Dict[str, Any] | None = None

    def build(self):
        return self.ai(**self.kwargs) if self.kwargs else self.ai()

@attrs.define(frozen=True)
class Position:
    """Entity position."""

    x: int
    y: int
    map: tcod.ecs.Entity

    def __add__(self, other: tuple[int, int]) -> Position:
        """Return a Position offset by `other`."""
        return self.__class__(self.x + other[0], self.y + other[1], self.map)

    def replace(self, x: int | None = None, y: int | None = None, map: tcod.ecs.Entity | None = None) -> Self:  # noqa: A002
        """Return a copy with attributes replaced."""
        return self.__class__(self.x if x is None else x, self.y if y is None else y, self.map if map is None else map)

    @property
    def ij(self) -> tuple[int, int]:
        """Return coordinates for Numpy indexing."""
        return self.y, self.x

    def distance_squared(self, other: Position) -> int:
        """Return the squared distance between two positions."""
        assert self.map == other.map
        return (self.x - other.x) ** 2 + (self.y - other.y) ** 1

@attrs.define(frozen=True)
class DelayedAction:
    # An action that can take multiple turns due to a the player's speed being
    # lower than the action cost
    action: Action


@attrs.define(frozen=True)
class RacialTrait:
    effect_name: str
    target: TraitTarget
    activation: TraitActivation


@attrs.define(frozen=True)
class Graphic:
    """Entity glyph."""

    ch: int
    fg: tuple[int, int, int]


class MapShape(NamedTuple):
    """The shape of a map entity."""

    height: int
    width: int

# Map related components
Tiles: Final = ("Tiles", NDArray[np.int8])
"""The tile indexes of a map entity."""

VisibleTiles: Final = ("VisibleTiles", NDArray[np.bool])
"""Player visible tiles for a map."""

MemoryTiles: Final = ("MemoryTiles", NDArray[np.int8])
"""Last seen tiles for a map."""

Floor: Final = ("Floor", int)
"""Dungeon floor."""

# Entity related components
Name: Final = ("Name", str)
"""Name of an entity."""

AI: Final = ("AI", BaseAI)
"""Action for AI actor."""

Energy: Final = ("Energy", int)
"""How much energy entities have to perform actions"""

Speed: Final = ("Speed", int)
"""How quickly entities regain energy"""

AttackSpeed: Final = ("Speed", float)
"""Inverse multiplier for attack action cost. 0.5 is 2x cost"""

MoveSpeed: Final = ("Speed", float)
"""Inverse multiplier for move action cost. 0.5 is 2x cost"""

HP: Final = ("HP", int)
"""Current hit points."""

MaxHP: Final = ("MaxHP", int)
"""Maximum hit points."""

# Attack: Final = ("Attack", str)
# """Damage stat for the entity. Represented by dice notation. Ex 1d4."""

STR: Final = ("STR", int)
"""Strength stat for the entity."""

DEX: Final = ("DEX", int)
"""Dexterity stat for the entity."""

CON: Final = ("CON", int)
"""Constitution stat for the entity."""

Defense: Final = ("Defense", int)
"""Defense stat for the entity."""

Level: Final = ("Level", int)
"""Character level."""

XP: Final = ("XP", int)
"""Character experience."""

RewardXP: Final = ("RewardXP", int)
"""Character experience reward."""

Resistances: Final = ("Resistances", tuple[DamageResistance, ...])

SpawnWeight: Final = ("SpawnWeight", tuple[tuple[int, int], ...])
"""Spawn rate as `((floor, weight), ...)`."""

EffectsApplied: Final = ("EffectsApplied", tuple[tcod.ecs.Entity, ...])
"""Effects the entity will apply each turn to the target"""

StartingEffects: Final = ("StartingEffects", tuple[str, ...])
"""Effects that an entity starts with when created"""

RacialTraits: Final = ("RacialTraits", tuple[RacialTrait, ...])
"""Racial traits the entity has"""

LootDropChance: Final = ("LootDropChance", float)
"""Chance the entity has to drop loot on death."""

all_stat_components = [Speed, AttackSpeed, MoveSpeed, HP, MaxHP, STR, DEX, CON, Defense, Resistances]


# Equipment stats
# EquipSlotType = NewType('EquipSlotType', tuple[object])
EquipSlot: Final = ("EquipSlot", int)
"""Name of the equipment slot this item uses."""

PowerBonus: Final = ("PowerBonus", str)
"""Bonus attack power. In dice notation. Ex 1d4"""

DefenseBonus: Final = ("DefenseBonus", int)
"""Bonus defense power."""

HPBonus: Final = ("HPBonus", int)
"""Bonus health."""

# Inventory
AssignedKey: Final = ("AssignedKey", str)
"""Name of the KeySym for this item."""


MaxCount: Final = ("MaxCount", int)
"""Max stack size for this item type."""

Count: Final = ("Count", int)
"""Stacked item count."""


@tcod.ecs.callbacks.register_component_changed(component=Position)
def on_position_changed(entity: tcod.ecs.Entity, old: Position | None, new: Position | None) -> None:
    """Called when an entities position is changed."""
    if old == new:
        return
    if old is not None:
        entity.tags.remove(old)
    if new is not None:
        entity.tags.add(new)
        entity.relation_tag[IsIn] = new.map
    else:
        del entity.relation_tags_many[IsIn]


@tcod.ecs.callbacks.register_component_changed(component=TraitActivation)
def on_trait_activation_changed(entity: tcod.ecs.Entity, old: TraitActivation | None, new: TraitActivation | None) -> None:
    """Called when an entities position is changed."""
    if old == new:
        return
    if old is not None:
        entity.tags.remove(old)
    if new is not None:
        entity.tags.add(new)
    else:
        pass
        #del entity.relation_tags_many[IsIn]


@tcod.ecs.callbacks.register_component_changed(component=HP)
def on_hp_changed(entity: tcod.ecs.Entity, old: int | None, new: int | None) -> None:
    """Called when an entities position is changed."""
    if old == new:
        return
    if isinstance(new, int) and new <=0:
        # The actor with this HP has died
        # Now check that it wasn't the player
        if not IsPlayer in entity.tags:
            # Now we need to get the drop chance percent
            loot_pct = entity.components.get(LootDropChance, 0)
            from random import Random
            rng = entity.registry[None].components[Random]
            if rng.random() > loot_pct:
                return
            # Then get the current floor #
            map_ = entity.relation_tag[IsIn]
            floor = map_.components[Floor]
            # Then generate probabilities for items to spawn
            # TODO - refactor code to fix imports
            from game.world.procgen import get_template_weights
            from game.items.item_tools import spawn_item
            items = entity.registry.Q.all_of(components=[SpawnWeight], tags=[IsItem], depth=0)
            item_weights = get_template_weights(items, floor)
            # Then pick from probability list
            item = rng.choices(**item_weights)[0]
            # Then spawn the item at the location the entity died
            spawn_item(item, entity.components[Position])

# @tcod.ecs.callbacks.register_component_changed(component=EquipSlot)
# def on_equipslot_changed(entity: tcod.ecs.Entity, old: EquipSlotType | None, new: EquipSlotType | None) -> None:
#     """Called when an entities equipment is changed."""
#     print("in equipslot changed")
#     print("old", old)
#     print("new", new)
