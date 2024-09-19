#!/usr/bin/env python
"""Main module."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import NoReturn

import imageio
import tcod.console
import tcod.context
import tcod.ecs
import tcod.event
import tcod.tileset

import g
import game.actor_tools
import game.world.procgen
import game.states
import game.world.world_init
from game.world.world_tools import load_world, save_world

TITLE = "Nate's Roguelike"
CONSOLE_SIZE = 80, 50
SAVE_PATH = Path("saved.sav")

ASSETS_DIR = Path(__file__) / "../assets"
TILESET = ASSETS_DIR / "Alloy_curses_12x12.png"

logger = logging.getLogger(__name__)


def main() -> NoReturn:  # noqa: C901
    """Main entry point."""
    logging.basicConfig(level="DEBUG")
    tileset = tcod.tileset.load_tilesheet(TILESET, 16, 16, tcod.tileset.CHARMAP_CP437)
    g.console = tcod.console.Console(*CONSOLE_SIZE)

    g.state = game.states.MainMenu()

    if SAVE_PATH.exists():
        try:
            g.world = load_world(SAVE_PATH)
        except Exception:
            logger.exception("Failed to load %s", SAVE_PATH)

    try:
        with tcod.context.new(console=g.console, tileset=tileset, title=TITLE) as g.context:
            while True:
                g.console.clear()
                g.state.on_draw(g.console)
                g.context.present(g.console)

                for event in tcod.event.wait():
                    event = g.context.convert_event(event)  # noqa: PLW2901
                    match event:
                        case tcod.event.Quit():
                            raise SystemExit
                        case tcod.event.MouseMotion(position=position):
                            g.cursor_location = position
                        case tcod.event.WindowEvent(type="WindowLeave"):
                            g.cursor_location = None
                        case tcod.event.KeyDown(sym=tcod.event.KeySym.PRINTSCREEN):
                            screenshots = Path("screenshots")
                            screenshots.mkdir(exist_ok=True)
                            imageio.imsave(
                                screenshots / f"tt2024.{datetime.now():%Y-%m-%d-%H-%M-%S-%f}.png",  # noqa: DTZ005
                                tileset.render(g.console),
                            )
                    try:
                        g.state = g.state.on_event(event)
                    except Exception:
                        logger.exception("Caught error from on_event")
    finally:
        if hasattr(g, "world"):
            save_world(g.world, SAVE_PATH)


if __name__ == "__main__":
    main()


"""
TODO
- Update TargetScroll to include max range
- Split AI into it's own file
- One file for protocols?
- AreaOfEffect an area of effect with just 1 cell is kinda weird...
- should passives run on some impossible actions?
- Figure out tags for downstairs & upstairs & how we travel between levels
- Show a stat screen for enemies?

- Enemy spawner - with spawned monsters having AI to wander the map
- More equipment slots
- Add weapon stats that multiply power
- Add events: on turn start/end
- Add a skill system?
- Don't like the melee combat system returning a class

- Passive ideas
- retaliate
- rough skin

- Intro screen
- Character selection: race/class

story line - somebody took my son? Find him on Floor 20; Robin hood style?
Damage - D4 + 3
Implement camera system
Make dungeons small at low levels but grow larger w/ more/bigger rooms

Update ActionResult to return an alternative action with it's own cost
Make armor/items affect speed
make different types of units have different walk speeds, but consistent attack speeds

More actions that should have costs:
- dropping an item
- equip/unequip
TODO - if a player tries to do two actions with a 50 weight, they will only do 1 per turn
- Need to set the desired action, then attempt it next turn
- If a player attempts to perform an action with a cost greater than their energy,
the user has to double click to perform the action
"""
