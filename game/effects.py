"""A collection of effects."""

from __future__ import annotations

import attrs
from tcod.ecs import Entity  # noqa: TCH002

from game.combat.combat import heal, poison
from game.components import Name
from game.ui.messages import add_message


@attrs.define
class Healing:
    """Healing effect that lasts 1 turn."""

    amount: int

    def affect(self, entity: Entity) -> bool:
        """Heal the target."""
        if amount := heal(entity, self.amount):
            add_message(
                entity.registry, f"""{entity.components.get(Name, "?")} recovers {amount} HP.""", fg="health_recovered"
            )
        return True

class Regeneration(Healing):
    """Healing effect that lasts forever."""

    def affect(self, entity: Entity) -> bool:
        super().affect(entity)
        return False

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
        return self.duration <= 0
