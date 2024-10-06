"""Main actions."""

from __future__ import annotations

from random import Random
from typing import Literal, Final, TYPE_CHECKING, Self

import attrs
import tcod.ecs  # noqa: TCH002

from game.action import Action, ActionResult, Impossible, Success
from game.actor_tools import spawn_actor, update_fov
from game.combat.combat import melee_damage
from game.components import Effect, EffectsApplied, EquipSlot, MapShape, Name, Position, Tiles
from game.constants import DEFAULT_ACTION_COST
from game.effect import remove_effect_from_entity
from game.entity_tools import get_name
from game.items.item import ApplyAction
from game.items.item_tools import add_to_inventory, equip_item, unequip_item
from game.map import MapKey
from game.tags import Affecting, EquippedBy, IsAlive, IsBlocking, IsEffect, IsIn, IsItem, IsPlayer
from game.travel import path_to
from game.ui.messages import add_message
from game.world.map_tools import get_map
from game.world.tiles import TILES

if TYPE_CHECKING:
    from game.combat.ai import SpawnerAI

@attrs.define
class Move:
    """Move an entity in a direction."""
    cost: int = attrs.field(kw_only=True, default=DEFAULT_ACTION_COST)
    direction: tuple[int, int]

    def get_action_state(self, entity: tcod.ecs.Entity) -> ActionResult:
        """
        Check if the direction we are attempting to go is valid
        """
        new_position = entity.components[Position] + self.direction
        map_shape = new_position.map.components[MapShape]
        if not (0 <= new_position.x < map_shape.width and 0 <= new_position.y < map_shape.height):
            return Impossible("Out of bounds.")
        tile_index = new_position.map.components[Tiles][new_position.ij]
        if TILES["walk_cost"][tile_index] == 0:
            return Impossible(f"""Blocked by {TILES["name"][tile_index]}.""")
        if entity.registry.Q.all_of(tags=[IsBlocking, new_position]):
            return Impossible("Something is in the way.")  # Blocked by entity
        return Success()


    def __call__(self, entity: tcod.ecs.Entity) -> ActionResult:
        """Check and apply the movement."""
        assert -1 <= self.direction[0] <= 1 and -1 <= self.direction[1] <= 1, self.direction  # noqa: PT018
        if self.direction == (0, 0):
            return wait(entity)

        state = self.get_action_state(entity)
        if isinstance(state, Impossible):
            return state

        entity.components[Position] += self.direction
        return Success()


@attrs.define
class Melee:
    """Attack an entity in a direction."""

    direction: tuple[int, int]
    cost: int = attrs.field(kw_only=True, default=DEFAULT_ACTION_COST)

    def __call__(self, entity: tcod.ecs.Entity) -> ActionResult:
        """Check and apply the movement."""
        new_position = entity.components[Position] + self.direction
        try:
            (player,) = entity.registry.Q.all_of(tags=[IsPlayer])
            (target,) = entity.registry.Q.all_of(tags=[IsAlive, new_position])
        except ValueError:
            return Impossible("Nothing there to attack.")  # No actor at position.

        melee_damage(entity, target)
        return Success()


@attrs.define
class Bump:
    """Context sensitive action in a direction."""

    direction: tuple[int, int]

    def __call__(self, entity: tcod.ecs.Entity) -> Action:
        """Check and apply the movement."""
        if self.direction == (0, 0):
            return Wait()
        new_position = entity.components[Position] + self.direction
        map_ = entity.components[Position].map
        if entity.registry.Q.all_of(tags=[IsAlive, new_position], relations=[(IsIn, map_)]):
            return Melee(self.direction)
        return Move(self.direction)



@attrs.define
class FollowPath:
    """Follow path action."""

    path: list[Position] = attrs.field(factory=list)

    @classmethod
    def to_dest(cls, actor: tcod.ecs.Entity, dest: Position) -> Self:
        """Path to a destination."""
        return cls(path_to(actor, dest))

    def __bool__(self) -> bool:
        """Return True if a path exists."""
        return bool(self.path)

    def __call__(self, actor: tcod.ecs.Entity) -> Action:
        """Move along the path."""
        if not self.path:
            # TODO - should indicate this is an impossible action, No path.
            return Wait()
        actor_pos: Final = actor.components[Position]
        dest: Final = self.path.pop(0)
        # TODO - sometimes these numbers are like (-2, 1), should be bound to [-1, 0, 1]
        dx = min(1, max(-1, dest.x - actor_pos.x))
        dy = min(1, max(-1, dest.y - actor_pos.y))
        action = Move((dx, dy))
        state = action.get_action_state(actor)
        if not isinstance(state, Success):
            self.path = []
        return action


@attrs.define
class Wait:
    cost: int = attrs.field(kw_only=True, default=DEFAULT_ACTION_COST)

    def __call__(self, entity: tcod.ecs.Entity) -> ActionResult:
        return Success()

def wait(entity: tcod.ecs.Entity) -> Success:  # noqa: ARG001
    """Do nothing and return successfully."""
    return Success()


@attrs.define
class PickupItem:
    """Pickup an item and add it to the inventory, if there is room for it."""

    cost: int = attrs.field(kw_only=True, default=DEFAULT_ACTION_COST)

    def __call__(self, actor: tcod.ecs.Entity) -> ActionResult:
        """Check for and pickup item."""
        items_here = actor.registry.Q.all_of(tags=[IsItem, actor.components[Position]]).get_entities()
        if not items_here:
            return Impossible("There is nothing here to pick up.")
        item = next(iter(items_here))

        return add_to_inventory(actor, item)


@attrs.define
class ApplyItem:
    """Use an item directly."""

    item: tcod.ecs.Entity
    cost: int = attrs.field(kw_only=True, default=DEFAULT_ACTION_COST)

    def __call__(self, actor: tcod.ecs.Entity) -> ActionResult:
        """Defer to items apply behavior."""
        if EquipSlot in self.item.components:
            if EquippedBy in self.item.relation_tag:
                unequip_item(self.item)
                add_message(actor.registry, f"You unequip the {get_name(self.item)}.")
            else:
                equip_item(actor, self.item)
                add_message(actor.registry, f"You equip the {get_name(self.item)}.")
            return Success()
        if ApplyAction in self.item.components:
            return self.item.components[ApplyAction].on_apply(actor, self.item)
        return Impossible(f"""Can not use the {get_name(self.item)}""")


@attrs.define
class DropItem:
    """Place an item on the floor."""

    item: tcod.ecs.Entity
    cost: int = attrs.field(kw_only=True, default=DEFAULT_ACTION_COST)

    def __call__(self, actor: tcod.ecs.Entity) -> ActionResult:
        """Drop item from inventory."""
        item = self.item
        assert item.relation_tag[IsIn] is actor
        add_message(actor.registry, f"""You drop the {item.components.get(Name, "?")}!""")
        unequip_item(item)
        del item.relation_tag[IsIn]
        item.components[Position] = actor.components[Position]
        return Success()


@attrs.define
class TakeStairs:
    """Traverse stairs action."""

    dir: Literal["down", "up"]
    cost: int = attrs.field(kw_only=True, default=DEFAULT_ACTION_COST)

    def __call__(self, actor: tcod.ecs.Entity) -> ActionResult:
        """Find and traverse stairs for this actor."""
        dir_tag = "DownStairs" if self.dir == "down" else "UpStairs"
        dir_tag_reverse = "DownStairs" if self.dir == "up" else "UpStairs"
        stairs_found = actor.registry.Q.all_of(tags=[actor.components[Position], dir_tag]).get_entities()
        if not stairs_found:
            return Impossible(f"There are no {self.dir}ward stairs here!")

        (stairs,) = stairs_found
        if MapKey not in stairs.components:
            return Impossible("You can not leave yet.")  # Generic description for non-exits for now.

        dir_desc = "descend" if self.dir == "down" else "ascend"
        return MoveLevel(
            dest_map=stairs.components[MapKey],
            exit_tag=(dir_tag_reverse,),
            message=f"""You {dir_desc} the stairs.""",
        )(actor)


@attrs.define
class MoveLevel:
    """Handle level transition."""

    dest_map: MapKey
    exit_tag: tuple[object, ...] = ()
    message: str = ""
    cost: int = attrs.field(kw_only=True, default=DEFAULT_ACTION_COST)

    def __call__(self, actor: tcod.ecs.Entity) -> ActionResult:
        """Move actor to the exit passage of the destination map."""
        update_fov(actor, clear=True)

        dest_map = get_map(actor.registry, self.dest_map)
        (dest_stairs,) = actor.registry.Q.all_of(tags=self.exit_tag, relations=[(IsIn, dest_map)]).get_entities()
        add_message(actor.registry, self.message)
        actor.components[Position] = dest_stairs.components[Position]
        return Success()

@attrs.define
class SpawnEntity:
    spawner: SpawnerAI
    cost: int = attrs.field(kw_only=True, default=DEFAULT_ACTION_COST)

    def __call__(self, actor: tcod.ecs.Entity) -> ActionResult:
        actor_pos: Final = actor.components[Position]
        map_: Final = actor.relation_tag[IsIn]
        spawned_entity = actor.registry[self.spawner.spawned_entity_name]
        # Spawn a new entity if the spawn timer is greater than the spawn rate
        rng = actor.registry[None].components[Random]
        if self.spawner.spawn_timer >= self.spawner.spawn_rate:
            self.spawner.spawn_timer = 0
            # Get a random location near the spawner.
            x=actor_pos.x + rng.randint(-3, 3)
            y=actor_pos.y + rng.randint(-3, 3)
            new_position = Position(x, y, map_)
            # Check if out of bounds or not walkable
            map_shape = new_position.map.components[MapShape]
            tile_index = new_position.map.components[Tiles][new_position.ij]

            tries = 0
            # TODO - consolidate logic with Move action into function
            while (
                not (0 <= new_position.x < map_shape.width and 0 <= new_position.y < map_shape.height) or # Out of bounds
                (TILES["walk_cost"][tile_index] == 0) or # Not walkable
                actor.registry.Q.all_of(tags=[IsBlocking, new_position], relations=[(IsIn, map_)]).get_entities() # Blocked by an entity
            ):
                x=actor_pos.x + rng.randint(-3, 3)
                y=actor_pos.y + rng.randint(-3, 3)
                new_position = Position(x, y, map_)
                tile_index = new_position.map.components[Tiles][new_position.ij]
                tries += 1
                if tries > 10:
                    return Success() # Wait action; no room to spawn an entity

            spawn_actor(spawned_entity, Position(x, y, map_))

            if self.spawner.visible:
                spawner_name = actor.components.get(Name, "?")
                spawned_name = spawned_entity.components.get(Name, "?")
                add_message(actor.registry,
                    f"The {spawner_name} spawned a new {spawned_name}!"
                )

        # Add 1 to the spawn timer.
        self.spawner.spawn_timer += 1
        return Success()
