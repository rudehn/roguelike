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
from tcod.event import KeySym, Modifier, Scancode

import g
import game.color
import game.world.world_init
from game.action import Action, Impossible, Poll, Success  # noqa: TCH001
from game.action_tools import do_player_action, get_entity_energy, get_entity_speed, update_entity_energy
from game.actions import ApplyItem, Bump, DropItem, PickupItem, TakeStairs
from game.actor_tools import can_level_up, get_player_actor, level_up, required_xp_for_level, update_fov
from game.components import AI, HP, XP, Defense, Level, MaxHP, Position, Attack, Effect
from game.constants import CURSOR_Y_KEYS, DIRECTION_KEYS
from game.combat.combat import get_defense, get_evade_chance
from game.entity_tools import get_desc
from game.effect import remove_effect_from_entity
from game.items.item_tools import get_inventory_keys
from game.ui.messages import add_message, Message, MessageLog
from game.ui.rendering import main_render, render_messages
from game.state import State
from game.tags import IsEffect, IsPlayer, IsIn, Affecting


def process_entity_turn(entity: tcod.ecs.Entity, action: Action):
    available_energy = get_entity_energy(entity)
    # Entity has enough energy to perform this action
    while available_energy >= action.cost:
        result = action(entity)
        match result:
            case Success(message=message):
                # For now, take energy away for impossible actions
                update_entity_energy(entity, -action.cost)
                available_energy -= action.cost
            case Impossible(reason=reason):
                update_entity_energy(entity, -action.cost)
                available_energy -= action.cost
    update_entity_energy(entity, get_entity_speed(entity))

    for e in entity.registry.Q.all_of(components=[Effect], tags=[IsEffect], relations=[(Affecting, entity)]):
        effect = e.components[Effect]
        consumed = effect.affect(entity)
        if consumed:
            remove_effect_from_entity(entity, e)

@attrs.define
class InGame(State):
    """In-game main player control state."""

    def on_event(self, event: tcod.event.Event) -> State:  # noqa: C901, PLR0911
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
        match event:
            case tcod.event.KeyDown(sym=KeySym.ESCAPE):
                return MainMenu()
            case tcod.event.KeyDown(sym=KeySym.c):
                return CharacterScreen()
            case tcod.event.KeyDown(sym=KeySym.v):
                messages: Reversible[Message] = g.world[None].components[MessageLog]
                return MessageHistoryScreen(log_length=len(messages), cursor=len(messages) - 1)
            case tcod.event.KeyDown(sym=KeySym.i):
                return ItemSelect.player_verb(player, "use", ApplyItem)
            case tcod.event.KeyDown(sym=KeySym.d):
                return ItemSelect.player_verb(player, "drop", DropItem)
            case tcod.event.KeyDown(sym=KeySym.SLASH):
                return PositionSelect.init_look()

        # Can't handle actions on player death
        if player.components[HP] <= 0:
            return self

        match event:
            case tcod.event.KeyDown(sym=KeySym.g):
                player_action = PickupItem()
            case tcod.event.KeyDown(sym=KeySym.PERIOD, mod=mod) if mod & Modifier.SHIFT:
                player_action = TakeStairs("down")
            case tcod.event.KeyDown(sym=KeySym.COMMA, mod=mod) if mod & Modifier.SHIFT:
                player_action = TakeStairs("up")
            case tcod.event.KeyDown(scancode=Scancode.NONUSBACKSLASH, mod=mod) if mod & Modifier.SHIFT:
                player_action = TakeStairs("down")
            case tcod.event.KeyDown(scancode=Scancode.NONUSBACKSLASH, mod=mod) if not mod & Modifier.SHIFT:
                player_action = TakeStairs("up")
            case tcod.event.KeyDown(sym=sym) if sym in DIRECTION_KEYS:
                player_action = Bump(DIRECTION_KEYS[sym])
            case _:
                return self  # Didn't get any expected input

        process_entity_turn(player, player_action)

        # Update all the enemies in the same map as the player
        for entity in player.registry.Q.all_of(components=[AI], relations=[(IsIn, player.relation_tag[IsIn])]):
            action = entity.components[AI]
            process_entity_turn(entity, action)

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

    def on_event(self, event: tcod.event.Event) -> State:
        """Handle item selection."""
        match event:
            case tcod.event.KeyDown(sym=sym) if sym in self.items:
                return self.pick_callback(self.items[sym])
            case tcod.event.KeyDown(sym=KeySym.ESCAPE) if self.cancel_callback is not None:
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
        return cls(pick_callback=lambda _: InGame(), cancel_callback=InGame)

    def on_event(self, event: tcod.event.Event) -> State:
        """Handle cursor movement and selection."""
        match event:
            case tcod.event.KeyDown(sym=sym) if sym in DIRECTION_KEYS:
                g.world["cursor"].components[Position] += DIRECTION_KEYS[sym]
            case (
                tcod.event.KeyDown(sym=KeySym.RETURN)
                | tcod.event.KeyDown(sym=KeySym.KP_ENTER)
                | tcod.event.MouseButtonDown(button=tcod.event.MouseButton.LEFT)
            ):
                try:
                    return self.pick_callback(g.world["cursor"].components[Position])
                finally:
                    g.world["cursor"].clear()
            case tcod.event.MouseMotion(position=position):
                g.world["cursor"].components[Position] = g.world["cursor"].components[Position].replace(*position)
            case (
                tcod.event.KeyDown(sym=KeySym.ESCAPE)
                | tcod.event.MouseButtonDown(button=tcod.event.MouseButton.RIGHT)
            ) if self.cancel_callback is not None:
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

    def on_event(self, event: tcod.event.Event) -> State:
        """Handle menu keys."""
        match event:
            case tcod.event.KeyDown(sym=KeySym.q):
                raise SystemExit
            case tcod.event.KeyDown(sym=KeySym.c | KeySym.ESCAPE):
                if hasattr(g, "world"):
                    return InGame()
            case tcod.event.KeyDown(sym=KeySym.n):
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

    def on_draw(self, console: tcod.console.Console) -> None:
        """Draw the level up menu."""
        player = get_player_actor(g.world)
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
            string=f"a) Constitution (+20 HP, from {player.components[MaxHP]})",
        )
        console.print(
            x=x + 1,
            y=y + 5,
            string=f"b) Attack (+1 attack, from {player.components[Attack]})",
        )
        console.print(
            x=x + 1,
            y=y + 6,
            string=f"c) Defense (+1 defense, from {player.components[Defense]})",
        )

    def on_event(self, event: tcod.event.Event) -> State:
        """Apply level up mechanics."""
        player = get_player_actor(g.world)

        match event:
            case tcod.event.KeyDown(sym=KeySym.a):
                player.components[MaxHP] += 20
                player.components[HP] += 20
                level_up(player)
                add_message(g.world, "Your health improves!")
                return InGame()
            case tcod.event.KeyDown(sym=KeySym.b):
                player.components[Attack] += 1
                level_up(player)
                add_message(g.world, "You feel stronger!")
                return InGame()
            case tcod.event.KeyDown(sym=KeySym.c):
                player.components[Defense] += 1
                level_up(player)
                add_message(g.world, "Your movements are getting swifter!")
                return InGame()

        return self


@attrs.define
class CharacterScreen:
    """Character screen state."""

    def on_draw(self, console: tcod.console.Console) -> None:
        """Draw player stats."""
        main_render(g.world, console)
        console.rgb["fg"] //= 8
        console.rgb["bg"] //= 8
        x = 1
        y = 1

        player = get_player_actor(g.world)
        x = 1
        y = 1

        title = "Character Information"

        width = len(title) + 6

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=7,
            title=title,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        console.print(x=x + 1, y=y + 1, string=f"Level: {player.components.get(Level, 1)}")
        console.print(x=x + 1, y=y + 2, string=f"XP: {player.components.get(XP, 0)}")
        console.print(
            x=x + 1,
            y=y + 3,
            string=f"XP for next Level: {required_xp_for_level(player) - player.components.get(XP, 0)}",
        )

        console.print(x=x + 1, y=y + 4, string=f"Attack: {player.components[Attack]}")
        console.print(x=x + 1, y=y + 5, string=f"Defense: {player.components[Defense]}")
        # console.print(x=x + 1, y=y + 6, string=f"Damage: {get_min_damage(player)} - {get_max_damage(player)}")
        # console.print(x=x + 1, y=y + 7, string=f"Block: {get_defense(player)}")
        # console.print(x=x + 1, y=y + 8, string=f"Crit Chance: {get_crit_chance(player):.0%}")
        # console.print(x=x + 1, y=y + 9, string=f"Crit Mult: {get_crit_damage_pct(player)}")
        # console.print(x=x + 1, y=y + 10, string=f"Evade Chance: {get_evade_chance(player):.0%}")

    def on_event(self, event: tcod.event.Event) -> State:
        """Exit state on any key."""
        match event:
            case tcod.event.KeyDown():
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

    def on_event(self, event: tcod.event.Event) -> State:
        """Exit state on any key."""
        match event:
            case tcod.event.KeyDown(sym=sym) if sym in CURSOR_Y_KEYS :
                adjust = CURSOR_Y_KEYS[sym]
                if adjust < 0 and self.cursor == 0:
                    # Only move from the top to the bottom when you're on the edge.
                    self.cursor = self.log_length - 1
                elif adjust > 0 and self.cursor == self.log_length - 1:
                    # Same with bottom to top movement.
                    self.cursor = 0
                else:
                    # Otherwise move while staying clamped to the bounds of the history log.
                    self.cursor = max(0, min(self.cursor + adjust, self.log_length - 1))
            case tcod.event.KeyDown(sym=KeySym.HOME):
                self.cursor = 0 # Move directly to the top message
            case tcod.event.KeyDown(sym=KeySym.END):
                self.cursor = self.log_length - 1  # Move directly to the last message
            case tcod.event.KeyDown():
                return InGame()  # Any other key moves back to the main menu
        return self
