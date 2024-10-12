"""Rendering functions."""

from __future__ import annotations

from collections.abc import Reversible

import numpy as np
import tcod.camera
import tcod.console
import tcod.ecs
from numpy.typing import NDArray  # noqa: TCH002

import g
from game.actor_tools import get_player_actor, required_xp_for_level
from game.combat.stats import (
    get_attack,
    get_crit_chance,
    get_crit_damage,
    get_current_health,
    get_defense,
    get_derived_constitution,
    get_derived_dexterity,
    get_derived_strength,
    get_max_health,
)
from game.components import HP, XP, Floor, Graphic, Level, MapShape, MaxHP, MemoryTiles, Name, Position, Tiles, VisibleTiles
from game.entity_tools import get_name


from game.ui.messages import Message, MessageLog
from game.tags import IsAlive, IsGhost, IsIn, IsItem, IsPlayer
from game.world.tiles import TILES

from .. import color


def render_bar(
    console: tcod.console.Console,
    *,
    x: int,
    y: int,
    width: int,
    text: str,
    value: float,
    empty_color: tuple[int, int, int],
    full_color: tuple[int, int, int],
    text_color: tuple[int, int, int] = color.bar_text,
) -> None:
    """Render a progress bar with text."""
    bar_width = int(value * width)

    console.draw_rect(x=x, y=y, width=width, height=1, ch=ord(" "), bg=empty_color)

    if bar_width > 0:
        console.draw_rect(x=x, y=y, width=bar_width, height=1, ch=ord(" "), bg=full_color)

    console.print_box(x=x, y=y, height=1, width=width, string=text, fg=text_color)

def render_messages(world: tcod.ecs.Registry, width: int, height: int, *, slc: slice | None = None) -> tcod.console.Console:
    """Return a console with the messages from `world` rendered to it.

    The `messages` are rendered starting at the last message and working backwards.
    """
    messages: Reversible[Message] = world[None].components[MessageLog]
    if slc:
        messages = messages[slc]
    console = tcod.console.Console(width, height)
    y = height

    for message in reversed(messages):
        y -= tcod.console.get_height_rect(width, message.full_text)
        console.print_box(x=0, y=y, width=width, height=0, string=message.full_text, fg=message.fg)
        if y <= 0:
            break  # No more space to print messages.
    return console


def render_names_at_position(console: tcod.console.Console, x: int, y: int, pos: Position) -> None:
    """Render names of entities at `pos` to `console`."""
    map_height, map_width = pos.map.components[MapShape]
    if not (0 <= pos.x < map_width and 0 <= pos.y < map_height):
        return
    is_visible = pos.map.components[VisibleTiles].item(pos.ij)
    known_entities = [
        entity
        for entity in pos.map.registry.Q.all_of(components=[Name], tags=[pos])
        if is_visible or (IsGhost in entity.tags)
    ]
    names = ", ".join(entity.components[Name] for entity in known_entities)
    console.print(x=x, y=y, string=names, fg=color.white)


def main_render(  # noqa: C901
    world: tcod.ecs.Registry, console: tcod.console.Console, *, highlight: NDArray[np.bool] | None = None
) -> None:
    """Main rendering code."""
    player = get_player_actor(world)
    map_ = player.relation_tag[IsIn]
    pos = player.components[Position]
    justify = (0, 0)
    camera_ij = tcod.camera.get_camera(console.rgb.shape, pos.ij, (map_.components[MapShape], justify))
    console_slices, map_slices = tcod.camera.get_slices(
        (console.height, console.width), map_.components[MapShape], camera_ij
    )

    visible = map_.components[VisibleTiles][map_slices]
    not_visible = ~visible

    light_tiles = map_.components[Tiles][map_slices]
    dark_tiles = map_.components[MemoryTiles][map_slices]

    console.rgb[console_slices] = TILES["graphic"][np.where(visible, light_tiles, dark_tiles)]

    rendered_priority: dict[Position, int] = {}
    for entity in world.Q.all_of(components=[Position, Graphic], relations=[(IsIn, map_)]):
        pos = entity.components[Position]
        e_screen_y, e_screen_x = pos.ij[0] - camera_ij[0], pos.ij[1] - camera_ij[1]
        translated_pos = Position(e_screen_x, e_screen_y, map_)
        if not (0 <= translated_pos.x < console.width and 0 <= translated_pos.y < console.height):
            continue  # Out of bounds
        if visible[translated_pos.ij] == (IsGhost in entity.tags):
            continue
        render_order = 1
        if IsItem in entity.tags:
            render_order = 2
        if IsAlive in entity.tags:
            render_order = 3
        if IsPlayer in entity.tags:
            render_order = 4
        if rendered_priority.get(pos, 0) >= render_order:
            continue  # Do not render over a more important entity
        rendered_priority[pos] = render_order
        graphic = entity.components[Graphic]
        console.rgb[["ch", "fg"]][translated_pos.ij] = graphic.ch, graphic.fg

    console.rgb["fg"][console_slices][not_visible] //= 2
    console.rgb["bg"][console_slices][not_visible] //= 2

    cursor_pos = world["cursor"].components.get(Position)
    if highlight is not None:
        console.rgb[["fg", "bg"]][console_slices][highlight[map_slices]] = ((0, 0, 0), (0xC0, 0xC0, 0xC0))

    if cursor_pos is not None:
        e_screen_y, e_screen_x = cursor_pos.ij[0] - camera_ij[0], cursor_pos.ij[1] - camera_ij[1]
        translated_cursor_pos = Position(e_screen_x, e_screen_y, map_)

        if (0 <= translated_cursor_pos.x < console_slices[1].stop
            and 0 <= translated_cursor_pos.y < console_slices[0].stop
        ):
            console.rgb[["fg", "bg"]][console_slices][translated_cursor_pos.ij] = ((0, 0, 0), (255, 255, 255))

    render_bar(
        console,
        x=0,
        y=45,
        width=20,
        value=player.components[HP] / player.components.get(MaxHP, 1),
        text=f" HP: {player.components[HP]}/{player.components.get(MaxHP, 0)}",
        empty_color=color.bar_empty,
        full_color=color.bar_filled,
    )
    player.components.setdefault(XP, 0)
    render_bar(
        console,
        x=0,
        y=46,
        width=20,
        value=player.components[XP] / required_xp_for_level(player),
        text=f" XP: {player.components[XP]}/{required_xp_for_level(player)}",
        empty_color=color.bar_xp_empty,
        full_color=color.bar_xp_filled,
    )
    console.print(x=0, y=47, string=f""" Dungeon level: {map_.components.get(Floor, "?")}""", fg=(255, 255, 255))
    render_messages(world, width=40, height=5).blit(dest=console, dest_x=21, dest_y=45)
    if g.cursor_location:
        e_screen_y, e_screen_x = g.cursor_location[1] + camera_ij[0], g.cursor_location[0] + camera_ij[1]
        translated_pos = Position(e_screen_x, e_screen_y, map_)
        render_names_at_position(console, x=21, y=44, pos=translated_pos)


def render_entity_stats(entity: tcod.ecs.Entity):
    x = 1
    y = 1

    name = get_name(entity).capitalize()
    title = f"{name} Information"

    is_player = IsPlayer in entity.tags
    y_offset = 4 if is_player else 1

    width = len(title) + 6 + 1
    height = 9 + y_offset + 1
    console = tcod.console.Console(width=width, height=height)

    console.draw_frame(
        x=x,
        y=y,
        width=width-1,
        height=height-1,
        title=title,
        clear=True,
        fg=(255, 255, 255),
        bg=(0, 0, 0),
    )

    if is_player:
        console.print(x=x + 1, y=y + 1, string=f"Level: {entity.components.get(Level, 1)}")
        console.print(x=x + 1, y=y + 2, string=f"XP: {entity.components.get(XP, 0)}")
        console.print(
            x=x + 1,
            y=y + 3,
            string=f"XP for next Level: {required_xp_for_level(entity) - entity.components.get(XP, 0)}",
        )


    console.print(x=x + 1, y=y_offset + 1, string=f"HP: {get_current_health(entity)}/{get_max_health(entity)}")
    console.print(x=x + 1, y=y_offset + 2, string=f"CON: {get_derived_constitution(entity)}")
    console.print(x=x + 1, y=y_offset + 3, string=f"STR: {get_derived_strength(entity)}")
    console.print(x=x + 1, y=y_offset + 4, string=f"DEX: {get_derived_dexterity(entity)}")
    console.print(x=x + 1, y=y_offset + 5, string=f"Attack: {get_attack(entity)}")
    console.print(x=x + 1, y=y_offset + 6, string=f"Defense: {get_defense(entity)}")
    console.print(x=x + 1, y=y_offset + 7, string=f"Crit Chance: {100 * get_crit_chance(entity)}")
    console.print(x=x + 1, y=y_offset + 8, string=f"Crit Damage: {get_crit_damage(entity):.2f}x")

    return console
