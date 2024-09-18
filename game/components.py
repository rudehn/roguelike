"""Common entity components."""

from __future__ import annotations

from typing import Final, NamedTuple, NewType, Self

import attrs
import numpy as np
import tcod.ecs
import tcod.ecs.callbacks
from numpy.typing import NDArray

from game.action import Action
from game.effect import Effect
from game.tags import IsIn


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
class Graphic:
    """Entity glyph."""

    ch: int
    fg: tuple[int, int, int]


class MapShape(NamedTuple):
    """The shape of a map entity."""

    height: int
    width: int


Tiles: Final = ("Tiles", NDArray[np.int8])
"""The tile indexes of a map entity."""

VisibleTiles: Final = ("VisibleTiles", NDArray[np.bool])
"""Player visible tiles for a map."""

MemoryTiles: Final = ("MemoryTiles", NDArray[np.int8])
"""Last seen tiles for a map."""

Name: Final = ("Name", str)
"""Name of an entity."""

HP: Final = ("HP", int)
"""Current hit points."""

MaxHP: Final = ("MaxHP", int)
"""Maximum hit points."""

STR: Final = ("STR", int)
"""Strength stat for the entity."""

DEX: Final = ("DEX", int)
"""Dexterity stat for the entity."""

AI: Final = ("AI", Action)
"""Action for AI actor."""

Floor: Final = ("Floor", int)
"""Dungeon floor."""

Level: Final = ("Level", int)
"""Character level."""

XP: Final = ("XP", int)
"""Character experience."""

RewardXP: Final = ("RewardXP", int)
"""Character experience reward."""

SpawnWeight: Final = ("SpawnWeight", tuple[tuple[int, int], ...])
"""Spawn rate as `((floor, weight), ...)`."""

Passives: Final = ("Passives", tuple[Effect, ...])
"""Passive effects the entity will apply each turn"""

# EquipSlotType = NewType('EquipSlotType', tuple[object])
EquipSlot: Final = ("EquipSlot", int)
"""Name of the equipment slot this item uses."""

PowerBonus: Final = ("PowerBonus", int)
"""Bonus attack power."""

DefenseBonus: Final = ("DefenseBonus", int)
"""Bonus defense power."""

HPBonus: Final = ("HPBonus", int)
"""Bonus health."""

AssignedKey: Final = ("AssignedKey", str)
"""Name of the KeySym for this item."""

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

# @tcod.ecs.callbacks.register_component_changed(component=EquipSlot)
# def on_equipslot_changed(entity: tcod.ecs.Entity, old: EquipSlotType | None, new: EquipSlotType | None) -> None:
#     """Called when an entities equipment is changed."""
#     print("in equipslot changed")
#     print("old", old)
#     print("new", new)
