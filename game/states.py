"""Main game states."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Reversible, Self

import attrs
import numpy as np  # noqa: TCH002
import tcod.console
import tcod.constants
import tcod.event
from numpy.typing import NDArray  # noqa: TCH002
from tcod import libtcodpy
from tcod.ecs import Entity  # noqa: TCH002
from tcod.event import KeySym, MouseButton

import g
import game.color
import game.world.world_init
from game.action import Action, Impossible, Poll, Success  # noqa: TCH001
from game.action_tools import do_player_action, get_adjusted_action_cost, get_entity_energy, get_entity_speed, update_entity_energy
from game.actions import ApplyItem, Bump, DropItem, Melee, Move, PickupItem, TakeStairs
from game.actor_tools import get_actors_at_position, can_level_up, get_player_actor, level_up, required_xp_for_level, update_fov
from game.components import AI, AttackSpeed, CON, DelayedAction, DEX, HP, XP, Defense, Level, MaxHP, MoveSpeed, Position, STR, Effect
from game.constants import CURSOR_Y_KEYS, DIRECTION_KEYS
from game.combat.stats import get_attack, get_base_dexterity, get_base_constitution, get_base_strength, get_crit_chance, get_crit_damage, get_defense, get_entity_with_stat_preview, get_current_health, get_max_health
from game.entity_tools import get_desc
from game.effect import remove_effect_from_entity
from game.items.item_tools import get_inventory_keys
from game.ui.messages import add_message, Message, MessageLog
from game.ui.rendering import main_render, render_entity_stats, render_messages
from game.state import State
from game.tags import IsEffect, IsPlayer, IsIn, Affecting

def process_player_turn(entity: Entity):
    delayed_action = entity.components.get(DelayedAction)
    if delayed_action:
        # Try to continue with a previous action
        action = delayed_action.action
    else:
        # Find a new action to perform
        action: Action | None = None
        for key, direction in DIRECTION_KEYS.items():
            if g.inputs.is_key_pressed(key):
                action = Bump(direction)(entity)
        if g.inputs.is_key_just_pressed(KeySym.g):
            action = PickupItem()
        elif g.inputs.is_key_pressed(KeySym.PERIOD) and g.inputs.is_key_pressed(KeySym.LSHIFT):
            action = TakeStairs("down")
        elif g.inputs.is_key_pressed(KeySym.COMMA) and g.inputs.is_key_pressed(KeySym.LSHIFT):
            action = TakeStairs("up")

    if not action:
        return True # Still player's turn


    available_energy = get_entity_energy(entity)
    performed_action = False
    adjusted_cost = get_adjusted_action_cost(entity, action)

    if available_energy >= adjusted_cost:
        action(entity)
        performed_action = True
        update_entity_energy(entity, -adjusted_cost)
        available_energy -= adjusted_cost

    # If we performed an action this turn, remove any existing delayedActions on the entity
    if performed_action:
        entity.components.pop(DelayedAction, None)
        if available_energy > 0:
            # We want to try and finish our turn with another action, return control
            return True
    elif available_energy >= 0:
        # We didn't perform an action, but still have energy so we started a new action, but didn't finish it
        entity.components[DelayedAction] = DelayedAction(action)

    # After all actions are taken, start adding our energy back
    update_entity_energy(entity, get_entity_speed(entity))

    # Now do all effects on the entity
    if performed_action:
        for e in entity.registry.Q.all_of(components=[Effect], tags=[IsEffect], relations=[(Affecting, entity)]):
            effect = e.components[Effect]
            consumed = effect.affect(entity)
            if consumed:
                remove_effect_from_entity(entity, e)

    return False # Player's turn is over

def process_enemy_turn(entity: Entity):
    ai = entity.components[AI]
    available_energy = get_entity_energy(entity)
    performed_action = False

    # First check if the entity has an ongoing action
    # delayed_action = entity.components.get(DelayedAction)
    # if delayed_action:
    #     action = delayed_action.action
    # else:
    action = ai.get_action(entity)

    adjusted_cost = get_adjusted_action_cost(entity, action)

    while available_energy >= adjusted_cost:
        action(entity)
        performed_action = True
        update_entity_energy(entity, -adjusted_cost)
        available_energy -= adjusted_cost

        # Get new action and cost
        action = ai.get_action(entity)
        adjusted_cost = get_adjusted_action_cost(entity, action)

    # After all actions are taken, start adding our energy back
    update_entity_energy(entity, get_entity_speed(entity))

    # If we performed an action this turn, remove any existing delayedActions on the entity
    # if performed_action:
    #     entity.components.pop(DelayedAction, None)
    # elif available_energy >= 0:
    #     # We still have energy left over this turn, so we started a new action, but didn't finish it
    #     entity.components[DelayedAction] = DelayedAction(action)

    # Now do all effects on the entity

    if performed_action:
        for e in entity.registry.Q.all_of(components=[Effect], tags=[IsEffect], relations=[(Affecting, entity)]):
            effect = e.components[Effect]
            consumed = effect.affect(entity)
            if consumed:
                remove_effect_from_entity(entity, e)


@attrs.define
class InGame(State):
    """In-game main player control state."""

    def update(self) -> State:  # noqa: C901, PLR0911
        """
        Handle basic events and movement.

        Actors move with a 'speed' system. If actors have enough energy to perform their desired
        action, they will do so, deplete their energy by the cost of the action, and replenish their
        energy by their 'speed' component.

        We always process the player first, so that coming back to the InGame state from another state
        doesn't give an enemy a free turn.
        """
        player = get_player_actor(g.world)
        # First handle if we have any state changes

        if g.inputs.is_key_just_pressed(KeySym.ESCAPE):
            return MainMenu()
        elif g.inputs.is_key_just_pressed(KeySym.c):
            return CharacterScreen(player)
        elif g.inputs.is_key_just_pressed(KeySym.v):
            messages: Reversible[Message] = g.world[None].components[MessageLog]
            return MessageHistoryScreen(log_length=len(messages), cursor=len(messages) - 1)
        elif g.inputs.is_key_just_pressed(KeySym.i):
            return ItemSelect.player_verb(player, "use", ApplyItem)
        elif g.inputs.is_key_just_pressed(KeySym.d):
            return ItemSelect.player_verb(player, "drop", DropItem)
        elif g.inputs.is_key_just_pressed(KeySym.SLASH):
            print("Doing look")
            return PositionSelect.init_look()

        # Can't handle actions on player death
        if player.components[HP] <= 0:
            return self

            # if not player_action:
            #     return self # Don't have a continued action & no user input to specify next action

        # TODO - this is messy, clean up the logic
        # If a player didn't have an action to perform, or had the energy to perform multiple actions
        # Then it's still the player's turn to process, so kick control back up to main.py
        still_players_turn = process_player_turn(player)
        if still_players_turn:
            update_fov(player)
            return self

        # Update all the enemies in the same map as the player
        for entity in player.registry.Q.all_of(components=[AI], relations=[(IsIn, player.relation_tag[IsIn])]):
            process_enemy_turn(entity)

        update_fov(player) # Update the FOV after every action so we can see fast enemies move before attacking
        if can_level_up(player):
            return LevelUp()

        # Stay in the game
        return self

    def on_draw(self, console: tcod.console.Console) -> None:
        """Render the current map and entities."""
        main_render(g.world, console)


@attrs.define(kw_only=True)
class ItemSelect(State):
    """Item selection interface."""

    items: dict[KeySym, Entity]
    title: str = "Select an item"

    pick_callback: Callable[[Entity], State]
    cancel_callback: Callable[[], State] | None = None

    @classmethod
    def player_verb(cls, player: Entity, verb: str, action: Callable[[Entity], Action]) -> Self:
        """Initialize a common player verb on item menu."""
        return cls(
            title=f"Select an item to {verb}",
            items={KeySym[k]: v for k, v in sorted(get_inventory_keys(player).items())},
            pick_callback=lambda item: do_player_action(player, action(item)),
            cancel_callback=InGame,
        )

    def update(self) -> State:
        """Handle item selection."""
        for key, entity in self.items.items():
            if g.inputs.is_key_just_pressed(key):
                return self.pick_callback(entity)
        if g.inputs.is_key_just_pressed(KeySym.ESCAPE) and self.cancel_callback is not None:
            return self.cancel_callback()
        return self

    def on_draw(self, console: tcod.console.Console) -> None:
        """Render the item menu."""
        main_render(g.world, console)

        x = 5
        y = 5
        width = 30
        height = 2 + len(self.items)

        console.draw_frame(x=x, y=y, width=width, height=height, fg=(255, 255, 255), bg=(0, 0, 0))
        if self.title:
            console.print_box(
                x=x,
                y=y,
                width=width,
                height=1,
                string=f" {self.title} ",
                fg=(0, 0, 0),
                bg=(255, 255, 255),
                alignment=tcod.constants.CENTER,
            )
        for i, (sym, item) in enumerate(self.items.items(), start=1):
            key_char = sym.name
            console.print(x=x + 1, y=y + i, string=f"{key_char}) {get_desc(item)}", fg=(255, 255, 255))
        footer_rect: dict[str, Any] = {"x": x + 1, "y": y + height - 1, "width": width - 2, "height": 1}
        console.print_box(**footer_rect, string="[a-z] select", fg=(255, 255, 255))
        if self.cancel_callback is not None:
            console.print_box(**footer_rect, string="[esc] cancel", fg=(255, 255, 255), alignment=tcod.constants.RIGHT)


@attrs.define(kw_only=True)
class PositionSelect:
    """Look handler and position pick tool."""

    pick_callback: Callable[[Position], State]
    cancel_callback: Callable[[], State] | None = InGame
    highlighter: Callable[[Position], NDArray[np.bool]] | None = None

    @classmethod
    def init_look(cls) -> Self:
        """Initialize a basic look state."""
        (player,) = g.world.Q.all_of(tags=[IsPlayer])
        g.world["cursor"].components[Position] = player.components[Position]

        def callback(pos: Position):
            actors = get_actors_at_position(g.world, pos)
            if not actors:
                print("Returning inGAME")
                return InGame()
            print("Returning character selection")
            (actor,) = actors
            return CharacterScreen(actor)
        return cls(pick_callback=lambda pos: callback(pos), cancel_callback=InGame)

    def update(self) -> State:
        """Handle cursor movement and selection."""
        for key, direction in DIRECTION_KEYS.items():
            if g.inputs.is_key_just_pressed(key):
                g.world["cursor"].components[Position] += direction
        if g.inputs.is_key_just_pressed(KeySym.RETURN) or g.inputs.is_key_just_pressed(KeySym.KP_ENTER) or g.inputs.is_mouse_pressed(MouseButton.LEFT):
            try:
                return self.pick_callback(g.world["cursor"].components[Position])
            finally:
                g.world["cursor"].clear()
        if g.inputs.mouse_moved:
            g.world["cursor"].components[Position] = g.world["cursor"].components[Position].replace(*g.inputs.cursor_location)
        if self.cancel_callback is not None and (g.inputs.is_key_just_pressed(KeySym.ESCAPE) or g.inputs.is_mouse_pressed(MouseButton.RIGHT)):
            g.world["cursor"].clear()
            return self.cancel_callback()
        return self

    def on_draw(self, console: tcod.console.Console) -> None:
        """Render the main screen."""
        highlight = self.highlighter(g.world["cursor"].components[Position]) if self.highlighter is not None else None
        main_render(g.world, console, highlight=highlight)


@attrs.define
class MainMenu:
    """Handle the main menu rendering and input."""

    def update(self) -> State:
        """Handle menu keys."""
        if g.inputs.is_key_just_pressed(KeySym.q):
            raise SystemExit
        elif g.inputs.is_key_just_pressed(KeySym.c) or g.inputs.is_key_just_pressed(KeySym.ESCAPE):
            if hasattr(g, "world"):
                return InGame()
        elif g.inputs.is_key_just_pressed(KeySym.n):
            g.world = game.world.world_init.new_world()
            return InGame()

        return self

    def on_draw(self, console: tcod.console.Console) -> None:
        """Render the main menu."""
        if hasattr(g, "world"):
            main_render(g.world, console)
            console.rgb["fg"] //= 8
            console.rgb["bg"] //= 8

        console.print(
            console.width // 2,
            console.height // 2 - 4,
            "My cool adventure game",
            fg=game.color.menu_title,
            alignment=tcod.constants.CENTER,
        )
        console.print(
            console.width // 2,
            console.height - 2,
            'By Nate Rude',
            fg=game.color.menu_title,
            alignment=tcod.constants.CENTER,
        )

        menu_width = 24
        for i, text in enumerate(["[N] Play a new game", "[C] Continue last game", "[Q] Quit"]):
            console.print(
                console.width // 2,
                console.height // 2 - 2 + i,
                text.ljust(menu_width),
                fg=game.color.menu_text,
                bg=game.color.black,
                alignment=tcod.constants.CENTER,
                bg_blend=libtcodpy.BKGND_ALPHA(64),
            )


@attrs.define
class LevelUp:
    """Level up state."""
    cursor: int = 0
    display_stat_preview: bool = False
    preview_entity: Entity | None = None

    def on_draw(self, console: tcod.console.Console) -> None:
        """Draw the level up menu."""
        main_render(g.world, console)
        console.rgb["fg"] //= 8
        console.rgb["bg"] //= 8
        x = 1
        y = 1

        console.draw_frame(
            x=x,
            y=y,
            width=35,
            height=8,
            title="Level Up",
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        console.print(x=x + 1, y=y + 1, string="Congratulations! You level up!")
        console.print(x=x + 1, y=y + 2, string="Select an attribute to increase.")

        console.print(
            x=x + 1,
            y=y + 4,
            string=f"a) {"*" if self.cursor == 0 else ""} +1 Constitution",
        )
        console.print(
            x=x + 1,
            y=y + 5,
            string=f"b) {"*" if self.cursor == 1 else ""} +1 Strength",
        )
        console.print(
            x=x + 1,
            y=y + 6,
            string=f"c) {"*" if self.cursor == 2 else ""} +1 Dexterity",
        )

        if self.display_stat_preview:
            player = get_player_actor(g.world)
            kwargs = {
                0: {"con": get_base_constitution(player) + 1, "hp": get_current_health(player) + 5, "max_hp": get_max_health(player) + 5},
                1: {"str_": get_base_strength(player) + 1},
                2: {"dex": get_base_dexterity(player) + 1},
            }[self.cursor]
            if self.preview_entity:
                self.preview_entity.clear()
            self.preview_entity = get_entity_with_stat_preview(player, **kwargs)
            preview_console = render_entity_stats(self.preview_entity)
            preview_console.blit(console, dest_x=36)

    def update(self) -> State:
        """Apply level up mechanics."""
        player = get_player_actor(g.world)
        if g.inputs.is_key_just_pressed(KeySym.UP):
            self.cursor = max(0, self.cursor - 1)
        elif g.inputs.is_key_just_pressed(KeySym.DOWN):
            self.cursor = min(2, self.cursor + 1)
        elif g.inputs.is_key_just_pressed(KeySym.RIGHT):
            self.display_stat_preview = True
        elif g.inputs.is_key_just_pressed(KeySym.LEFT):
            self.display_stat_preview = False
        elif g.inputs.is_key_just_pressed(KeySym.RETURN):
            func = {
                0: self.do_con_levelup,
                1: self.do_str_levelup,
                2: self.do_dex_levelup,
            }[self.cursor]
            return func(player)
        elif g.inputs.is_key_just_pressed(KeySym.a):
            return self.do_con_levelup(player)
        elif g.inputs.is_key_just_pressed(KeySym.b):
            return self.do_str_levelup(player)
        elif g.inputs.is_key_just_pressed(KeySym.c):
            return self.do_dex_levelup(player)

        return self

    def do_con_levelup(self, player: Entity):
        # TODO - update logic to calculate from CON
        player.components[CON] += 1
        player.components[MaxHP] += 5
        player.components[HP] += 5
        level_up(player)
        add_message(g.world, "Your health improves!")
        return InGame()

    def do_str_levelup(self, player: Entity):
        player.components[STR] += 1
        level_up(player)
        add_message(g.world, "You feel stronger!")
        return InGame()

    def do_dex_levelup(self, player: Entity):
        player.components[DEX] += 1
        level_up(player)
        add_message(g.world, "Your movements are getting swifter!")
        return InGame()

@attrs.define
class CharacterScreen:
    """Character screen state."""
    entity: Entity

    def on_draw(self, console: tcod.console.Console) -> None:
        """Draw player stats."""
        main_render(g.world, console)
        console.rgb["fg"] //= 8
        console.rgb["bg"] //= 8

        stats_console = render_entity_stats(self.entity)
        stats_console.blit(console)

    def update(self) -> State:
        """Exit state on any key."""
        if g.inputs.is_any_key_just_pressed():
            return InGame()
        return self


@attrs.define
class MessageHistoryScreen():
    log_length: int
    cursor: int

    def on_draw(self, console: tcod.console.Console) -> None:
        """Draw message log history."""
        main_render(g.world, console)
        console.rgb["fg"] //= 8
        console.rgb["bg"] //= 8

        log_console = tcod.Console(console.width - 6, console.height - 6)

        # Draw a frame with a custom banner title.
        log_console.draw_frame(0, 0, log_console.width, log_console.height)
        log_console.print_box(
            0, 0, log_console.width, 1, "┤Message history├", alignment=tcod.CENTER
        )

        # Render the message log using the cursor parameter.
        message_console = render_messages(
            g.world,
            log_console.width - 2,
            log_console.height - 2,
            slc = slice(self.cursor + 1),
        )
        message_console.blit(log_console, 1, 1)
        log_console.blit(console, 3, 3)

    def update(self) -> State:
        """Exit state on any key."""
        adjust_keys_pressed = False
        for key, adjust in CURSOR_Y_KEYS.items():
            if g.inputs.is_key_pressed(key):
                adjust_keys_pressed = True
                if adjust < 0 and self.cursor == 0:
                    # Only move from the top to the bottom when you're on the edge.
                    self.cursor = self.log_length - 1
                elif adjust > 0 and self.cursor == self.log_length - 1:
                    # Same with bottom to top movement.
                    self.cursor = 0
                else:
                    # Otherwise move while staying clamped to the bounds of the history log.
                    self.cursor = max(0, min(self.cursor + adjust, self.log_length - 1))
        if g.inputs.is_key_just_pressed(KeySym.HOME):
            self.cursor = 0 # Move directly to the top message
        elif g.inputs.is_key_just_pressed(KeySym.END):
            self.cursor = self.log_length - 1  # Move directly to the last message
        elif not adjust_keys_pressed and g.inputs.is_any_key_just_pressed():
            return InGame()  # Any other key moves back to the main menu
        return self
