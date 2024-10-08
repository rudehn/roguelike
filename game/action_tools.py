"""Action functions."""

from __future__ import annotations

import logging

import tcod.ecs  # noqa: TCH002

import game.states
from game.action import Action, Impossible, Poll, Success
from game.actions import Melee, Move
from game.actor_tools import can_level_up, update_fov
from game.components import AI, AttackSpeed, Energy, HP, MoveSpeed, Speed
from game.ui.messages import add_message
from game.state import State  # noqa: TCH001
from game.tags import IsIn, IsPlayer

logger = logging.getLogger(__name__)


def get_adjusted_action_cost(entity: tcod.ecs.Entity, action: Action):
    cost = action.cost
    if isinstance(action, Move):
        move_speed = entity.components.get(MoveSpeed, 1.0)
        cost = int(cost / move_speed)  # 0.5 speed is a 2x increase, 2 speed is a 50% decrease
    elif isinstance(action, Melee):
        attack_speed = entity.components.get(AttackSpeed, 1.0)
        cost = int(cost / attack_speed)  # 0.5 speed is a 2x increase, 2 speed is a 50% decrease
    return cost


def get_entity_energy(entity: tcod.ecs.Entity) -> int:
    """Return the entity's energy"""
    return entity.components.get(Energy, 0)

def update_entity_energy(entity: tcod.ecs.Entity, amount: int):
    """Update the entity's energy by the specified amount"""
    entity.components.setdefault(Energy, 0)
    entity.components[Energy] += amount

def get_entity_speed(entity: tcod.ecs.Entity):
    return entity.components.get(Speed, 0)

def do_player_action(player: tcod.ecs.Entity, action: Action) -> State:
    """Perform an action on the player."""
    assert IsPlayer in player.tags
    if player.components[HP] <= 0:
        return game.states.InGame()
    result = action(player)
    update_fov(player)
    match result:
        case Success(message=message):
            if message:
                add_message(player.registry, message)
            #handle_enemy_turns(player.registry, player.relation_tag[IsIn])
        case Poll(state=state):
            return state
        case Impossible(reason=reason):
            add_message(player.registry, reason, fg="impossible")

    if can_level_up(player):
        return game.states.LevelUp()

    return game.states.InGame()
