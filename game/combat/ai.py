from random import Random
import attrs
from typing import Final, Self
import tcod.ecs

from game.action import Action, ActionResult, Impossible, Success
from game.actions import Bump, Melee, Move, wait
from game.actor_tools import spawn_actor
from game.components import AI, MapShape, Name, Position, Tiles, VisibleTiles
from game.constants import DEFAULT_ACTION_COST
from game.entity_tools import get_name
from game.tags import IsBlocking, IsIn, IsPlayer
from game.travel import path_to
from game.ui.messages import add_message
from game.world.tiles import TILES


class BaseAI:

    def perform_action(self, actor: tcod.ecs.Entity) -> ActionResult:
        raise NotImplementedError()

    def __call__(self, actor: tcod.ecs.Entity) -> ActionResult:
        result = self.perform_action(actor)

        # for e in actor.registry.Q.all_of(components=[Effect], tags=[IsEffect], relations=[(Affecting, actor)]):
        #     effect = e.components[Effect]
        #     consumed = effect.affect(actor)
        #     if consumed:
        #         remove_effect_from_entity(actor, e)

        return result


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

    def __call__(self, actor: tcod.ecs.Entity) -> ActionResult:
        """Move along the path."""
        if not self.path:
            return Impossible("No path.")
        actor_pos: Final = actor.components[Position]
        dest: Final = self.path.pop(0)
        result = Move((dest.x - actor_pos.x, dest.y - actor_pos.y))(actor)
        if not isinstance(result, Success):
            self.path = []
        return result


@attrs.define
class HostileAI(BaseAI):
    """Generic hostile AI."""

    path: FollowPath | None = attrs.field(default=None)
    cost: int = attrs.field(kw_only=True, default=DEFAULT_ACTION_COST)

    def perform_action(self, actor: tcod.ecs.Entity) -> ActionResult:
        """Follow and attack player."""
        (target,) = actor.registry.Q.all_of(tags=[IsPlayer])
        actor_pos: Final = actor.components[Position]
        target_pos: Final = target.components[Position]
        map_: Final = actor.relation_tag[IsIn]
        dx: Final = target_pos.x - actor_pos.x
        dy: Final = target_pos.y - actor_pos.y
        distance: Final = max(abs(dx), abs(dy))  # Chebyshev distance
        if map_.components[VisibleTiles][actor_pos.ij]:
            if distance <= 1:
                return Melee((dx, dy))(actor)
            self.path = FollowPath.to_dest(actor, target_pos)
        if self.path:
            return self.path(actor)
        return wait(actor)


@attrs.define
class ConfusedAI(BaseAI):
    turns_remaining: int
    previous_ai: Action
    cost: int = attrs.field(kw_only=True, default=DEFAULT_ACTION_COST)

    def perform_action(self, actor: tcod.ecs.Entity) -> ActionResult:
         # Revert the AI back to the original state if the effect has run its course
        if self.turns_remaining <= 0:
            add_message(actor.registry, f"The {get_name(actor)} is no longer confused.")
            actor.components[AI] = self.previous_ai
            return Success()

        # Pick a random direction
        direction_x, direction_y = actor.registry[None].components[Random].choice([
            (-1, -1),  # Northwest
            (0, -1),  # North
            (1, -1),  # Northeast
            (-1, 0),  # West
            (1, 0),  # East
            (-1, 1),  # Southwest
            (0, 1),  # South
            (1, 1),  # Southeast
        ])

        self.turns_remaining -= 1
        # The actor will either try to move or attack in the chosen random direction.
        # It's possible the actor will just bump into the wall, waisting a turn.
        return Bump((direction_x, direction_y))(actor)


@attrs.define
class SpawnerAI(BaseAI):
    """
    A spawner enemy will spawn a new enemy (of the selected type) in a random location around itself
    """
    spawned_entity_name: str = attrs.field()
    spawn_rate: int = attrs.field() # Number of turns before a new entity is spawned
    initiated = attrs.field(kw_only=True, default=False)  # Keep track if this spawner has started spawning
    cost: int = attrs.field(kw_only=True, default=DEFAULT_ACTION_COST)
    visible = attrs.field(init=False, default=False)
    spawn_timer = attrs.field(init=False, default=0)

    def perform_action(self, actor: tcod.ecs.Entity) -> ActionResult:
        # TODO - check if spawned enemy doesn't exist
        spawned_entity = actor.registry[self.spawned_entity_name]
        actor_pos: Final = actor.components[Position]
        map_: Final = actor.relation_tag[IsIn]
        rng = actor.registry[None].components[Random]
        if map_.components[VisibleTiles][actor_pos.ij]:
            self.initiated = True
            self.visible = True
        else:
            self.visible = False

        if self.initiated:
            # Spawn a new entity if the spawn timer is greater than the spawn rate
            if self.spawn_timer >= self.spawn_rate:
                self.spawn_timer = 0
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

                if self.visible:
                    spawner_name = actor.components.get(Name, "?")
                    spawned_name = spawned_entity.components.get(Name, "?")
                    add_message(actor.registry,
                        f"The {spawner_name} spawned a new {spawned_name}!"
                    )

            # Add 1 to the spawn timer.
            self.spawn_timer += 1

        return Success()
