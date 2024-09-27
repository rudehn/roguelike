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
from game.constants import CONSOLE_SIZE
import game.world.world_init
from game.world.world_tools import load_world, save_world

TITLE = "Nate's Roguelike"
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
- Figure out tags for downstairs & upstairs & how we travel between levels
- Show a stat screen for enemies?

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

https://github.com/jossse69/Python-RL/blob/main/components/equippable.py
Apply status effects to ground. Poison/confusion/burn
- Apply status effect to weapon, attacking generates poison, bleeding, etc
https://github.com/jossse69/Python-RL/blob/main/entity_factories.py
https://github.com/jossse69/Python-RL/blob/main/components/ai.py#L130
https://github.com/bkeil/CompleteRoguelikeTutorial/blob/master/entity_types.py#L118

Confusion AI shouldn't assume the entity can move; sometimes it should just make the entity take the wait action
AIs shouldn't have a cost; their actions should have a cost

To apply effects to a target, I think I need to fetch all Effects for equipables effecting myself (somehow get the armor in there)
and then I need to "build" the effect & attach it to the target entity. When It's attached, we check if the target
is immune to the effect. Then on the entities turn, we iterate all effects applied to it and apply them
We also need to add a mechanism to update the duration, or stack effects, so we likely need a function to
join together by effect type to sum & report

TODO - attacking should only grab the effect from the weapon used
Add effect strings when the effect is initiated

# Organize components & other code
print messages when picking up loot
lightning bolt struck the remains of rat
refactor potions to use DB of effects

Update combat system;
- STR
- DEX
- CON
- AGI
- add dice rolls for attack, static defense, add pierce (possibly at higher STR?); AGI increases speed


Things to implement:

Racial Traits:
- Each trait is just an effect that the race has. The effect can be a boon for the creature, such as regeneration, or
  it can apply a negative effect on any attacker. This requires effects to have specific types, such as acting on the
  owner, vs apply on hit, apply on being hit, apply on death, etc.
- Racial traits can also provide immunities, like poison immunity


Implement Priority:
- Apply adding racial traits on being hit
- Figure out how to give extra parameters to effects like Bleed
- Add zone spawner enemies
- Zone ideas: poison, slow
- And corresponding immunities

more equipment, some that apply spike defense when hit
bleed effect - target takes a percentage of the damage every turn
TODO - how do we create effects like Bleed that need the context of how much damage was done?
- Do we need to check attached effects for on hit/ on attack to see if we are weakened, etc?

Create an "Attack" object, that specifies the attacker, defender, attack type, attack damage, etc
Update the Effect class to use a on_hit, on_attack function?
Add tiers of loot, or tiers of enemies. Higher tier enemies should have a higher chance of dropping loot
Remove item spawning on the ground, should be loot from enemies
Make a really strong enemy that's slow


Replace effect spawner entity key with object()

A player will want an increased loot drop chance if defeating an enemy that's beyond the threat level of the current level.player

Increaes map size w/ camera

Story - in a city, go into sewers, find dungeon, get teleported somewhere
Add weapons that do different damage types


TODO:
- Create 20 levels of dungeon, add monsters in them and 20th floor should have a boss
  - Boss should be able to use a double attack; Ex dragon has breath attack + claws
- Then create stats system for STR, DEX, CON,
- Then add chance to miss; accuracy + evade
- Then update character screen
- Then add screen to view enemy stats
- Then add items & refactor item generation code
  - Update attack code to factor in damage type from weapon
- Then add monsters with items
- Then add effects; spawn from damage type dealt

- Add weapon str/dex requirements
Energy to enter/leave a tile type
"""
