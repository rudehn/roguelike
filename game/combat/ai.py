from random import Random
import attrs
from typing import Final, Protocol, Self
import tcod.ecs

from game.action import Action, ActionResult, Impossible, Success
from game.actions import Bump, FollowPath, Melee, Move, SpawnEntity, Wait
from game.components import AI, MapShape, Name, Position, Tiles, VisibleTiles
from game.constants import DEFAULT_ACTION_COST
from game.entity_tools import get_name
from game.tags import IsBlocking, IsIn, IsPlayer
from game.ui.messages import add_message
from game.world.tiles import TILES


@attrs.define
class HostileAI:
    """Generic hostile AI."""

    path: FollowPath | None = attrs.field(default=None)

    def get_action(self, actor: tcod.ecs.Entity) -> Action:
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
                return Melee((dx, dy))
            self.path = FollowPath.to_dest(actor, target_pos)
        if self.path:
            return self.path(actor)
        return Wait()


@attrs.define
class ConfusedAI:
    turns_remaining: int
    previous_ai: Action

    def get_action(self, actor: tcod.ecs.Entity) -> Action:
         # Revert the AI back to the original state if the effect has run its course
        if self.turns_remaining <= 0:
            add_message(actor.registry, f"The {get_name(actor)} is no longer confused.")
            actor.components[AI] = self.previous_ai
            return Wait()

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
class SpawnerAI:
    """
    A spawner enemy will spawn a new enemy (of the selected type) in a random location around itself
    """
    spawned_entity_name: str = attrs.field()
    spawn_rate: int = attrs.field() # Number of turns before a new entity is spawned
    initiated: bool = attrs.field(kw_only=True, default=False)  # Keep track if this spawner has started spawning
    visible: bool = attrs.field(init=False, default=False)
    spawn_timer: int = attrs.field(init=False, default=0)

    def get_action(self, actor: tcod.ecs.Entity) -> Action:
        # TODO - check if spawned enemy doesn't exist
        actor_pos: Final = actor.components[Position]
        map_: Final = actor.relation_tag[IsIn]
        if map_.components[VisibleTiles][actor_pos.ij]:
            self.initiated = True
            self.visible = True
        else:
            self.visible = False

        if self.initiated:
            return SpawnEntity(self)

        return Wait()
