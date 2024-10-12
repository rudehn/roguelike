"""Global constants."""

from __future__ import annotations

from enum import auto, Enum
from typing import Final

from tcod.event import KeySym

CONSOLE_SIZE = (80, 50)
MAP_SIZE = (100, 100)

class TraitTarget(Enum):
    SELF = auto()
    ENEMY = auto()

class TraitActivation(Enum):
    """When the trait spawns an effect on the target entity"""
    ON_CREATE = auto()
    ON_ATTACK = auto()
    ON_DEFEND = auto()

DEFAULT_ACTION_COST: Final = 100

CURSOR_Y_KEYS: Final = {
    KeySym.UP: -1,
    KeySym.DOWN: 1,
    KeySym.PAGEUP: -10,
    KeySym.PAGEDOWN: 10,
 }

DIRECTION_KEYS: Final = {
    # Arrow keys
    KeySym.LEFT: (-1, 0),
    KeySym.RIGHT: (1, 0),
    KeySym.UP: (0, -1),
    KeySym.DOWN: (0, 1),
    # Arrow key diagonals
    KeySym.HOME: (-1, -1),
    KeySym.END: (-1, 1),
    KeySym.PAGEUP: (1, -1),
    KeySym.PAGEDOWN: (1, 1),
    # Keypad
    KeySym.KP_4: (-1, 0),
    KeySym.KP_6: (1, 0),
    KeySym.KP_8: (0, -1),
    KeySym.KP_2: (0, 1),
    KeySym.KP_7: (-1, -1),
    KeySym.KP_1: (-1, 1),
    KeySym.KP_9: (1, -1),
    KeySym.KP_3: (1, 1),
    KeySym.KP_5: (0, 0),
    # VI keys
    KeySym.h: (-1, 0),
    KeySym.l: (1, 0),
    KeySym.k: (0, -1),
    KeySym.j: (0, 1),
    KeySym.y: (-1, -1),
    KeySym.b: (-1, 1),
    KeySym.u: (1, -1),
    KeySym.n: (1, 1),
    KeySym.PERIOD: (0, 0),
}

INVENTORY_KEYS = "abcdefghijklmnopqrstuvwxyz"
