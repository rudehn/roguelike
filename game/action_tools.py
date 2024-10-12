"""Action functions."""

from __future__ import annotations

import logging

import tcod.ecs  # noqa: TCH002
from tcod.event import KeySym

import g
import game.states
from game.action import Action, Impossible, Poll, Success
from game.actions import Bump, Melee, Move, PickupItem, TakeStairs
from game.actor_tools import can_level_up, update_fov
from game.components import AI, AttackSpeed, DelayedAction, Effect, Energy, HP, MoveSpeed, Speed
from game.constants import DIRECTION_KEYS
from game.effect import remove_effect_from_entity
from game.ui.messages import add_message
from game.state import State  # noqa: TCH001
from game.tags import Affecting, IsAlive, IsEffect, IsIn, IsPlayer

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

def process_enemy_turn(entity: tcod.ecs.Entity):
    ai = entity.components[AI]
    available_energy = get_entity_energy(entity)
    performed_action = False

    action = ai.get_action(entity)

    adjusted_cost = get_adjusted_action_cost(entity, action)

    while available_energy >= adjusted_cost:
        ai.perform_action(action, entity)
        performed_action = True
        update_entity_energy(entity, -adjusted_cost)
        available_energy -= adjusted_cost

        # Get new action and cost
        action = ai.get_action(entity)
        adjusted_cost = get_adjusted_action_cost(entity, action)

    # After all actions are taken, start adding our energy back
    update_entity_energy(entity, get_entity_speed(entity))

    # Now do all effects on the entity
    # TODO - if we updated speed increase from 10 to a standardized 50,
    # where 50 is the minimum cost of an action, we can remove this check
    # Currently, this penalizes/helps actions that take longer, IE if an enemy
    # was a slow mover & took 2 turns to move a tile, it would take 2 turns to run
    # the regeneration effect
    if performed_action:
        for e in entity.registry.Q.all_of(components=[Effect], tags=[IsEffect], relations=[(Affecting, entity)]):
            effect = e.components[Effect]
            consumed = effect.affect(entity)
            if consumed:
                remove_effect_from_entity(entity, e)


def handle_enemy_turns(registry: tcod.ecs.Registry, player: tcod.ecs.Entity):
    # Update all the enemies in the same map as the player

    for entity in registry.Q.all_of(components=[AI], relations=[(IsIn, player.relation_tag[IsIn])], tags=[IsAlive]):
        process_enemy_turn(entity)

def process_player_turn(player: tcod.ecs.Entity):
    delayed_action = player.components.get(DelayedAction)
    if delayed_action:
        # Try to continue with a previous action
        action = delayed_action.action
    else:
        # Find a new action to perform
        action: Action | None = None
        for key, direction in DIRECTION_KEYS.items():
            if g.inputs.is_key_just_pressed(key):
                action = Bump(direction)(player)
        if g.inputs.is_key_just_pressed(KeySym.g):
            action = PickupItem()
        elif g.inputs.is_key_pressed(KeySym.PERIOD) and g.inputs.is_key_pressed(KeySym.LSHIFT):
            action = TakeStairs("down")
        elif g.inputs.is_key_pressed(KeySym.COMMA) and g.inputs.is_key_pressed(KeySym.LSHIFT):
            action = TakeStairs("up")

    if not action:
        # No valid action, so return to the processing loop to await user input
        return game.states.InGame()

    return do_player_action(player, action)


def do_player_action(player: tcod.ecs.Entity, action: Action) -> State:
    """Perform an action on the player."""
    assert IsPlayer in player.tags
    if player.components[HP] <= 0:
        return game.states.InGame()

    # Make sure we have the energy available to perform the action
    available_energy = get_entity_energy(player)
    performed_action = False
    adjusted_cost = get_adjusted_action_cost(player, action)
    if available_energy >= adjusted_cost:
        result = action(player)
        update_fov(player)
        match result:
            case Success(message=message):
                if message:
                    add_message(player.registry, message)
            case Poll(state=state):
                return state
            case Impossible(reason=reason):
                # Redo player's turn on impossible actions
                add_message(player.registry, reason, fg="impossible")
                player.components.pop(DelayedAction, None)
                return game.states.InGame()

        performed_action = True
        update_entity_energy(player, -adjusted_cost)
        available_energy -= adjusted_cost
    if performed_action:
        player.components.pop(DelayedAction, None)
        if available_energy > 0:
            # We want to try and finish our turn with another action, return control
            return game.states.InGame()
    elif available_energy >= 0:
        # We didn't perform an action, but still have energy so we started a new action, but didn't finish it
        player.components[DelayedAction] = DelayedAction(action)

    # After all actions are taken, start adding our energy back
    update_entity_energy(player, get_entity_speed(player))

    # Now do all effects on the entity
    if performed_action:
        for e in player.registry.Q.all_of(components=[Effect], tags=[IsEffect], relations=[(Affecting, player)]):
            effect = e.components[Effect]
            consumed = effect.affect(player)
            if consumed:
                remove_effect_from_entity(player, e)

    handle_enemy_turns(player.registry, player)
    update_fov(player)

    if can_level_up(player):
        return game.states.LevelUp()

    return game.states.InGame()
