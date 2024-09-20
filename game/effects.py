"""A collection of effects."""

from __future__ import annotations

import attrs
from tcod.ecs import Entity  # noqa: TCH002

from game.combat import heal, poison
from game.components import Name
from game.ui.messages import add_message


@attrs.define
class Healing:
    """Healing effect."""

    amount: int

    def affect(self, entity: Entity) -> None:
        """Heal the target."""
        if amount := heal(entity, self.amount):
            add_message(
                entity.registry, f"""{entity.components.get(Name, "?")} recovers {amount} HP.""", fg="health_recovered"
            )

@attrs.define
class Poisoned:
    """Poison effect"""
    amount: int
    duration: int

    def affect(self, entity: Entity):
        """Poison the target"""
        if self.duration > 0:
            if amount := poison(entity, self.amount):
                add_message(
                    entity.registry, f"""{entity.components.get(Name, "?")} took {amount} poison damage.""", fg="status_effect_applied"
                )
            self.duration -= 1
            # TODO - how do we remove the poison effect?
