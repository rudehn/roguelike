"""Abstract state classes."""

from __future__ import annotations

from typing import Protocol

import tcod.console
import tcod.event  # noqa: TCH002


class State(Protocol):
    """State protocol."""

    __slots__ = ()

    def update(self) -> State:
        """Handle any actions & events."""
        ...

    def on_draw(self, console: tcod.console.Console, /) -> None:
        """Handle drawing."""
        ...
