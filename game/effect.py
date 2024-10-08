"""Effect base types."""

from __future__ import annotations

import copy
from typing import Protocol

from tcod.ecs import Entity  # noqa: TCH002

from game.tags import Affecting

def spawn_effect(template: Entity):
    effect = template.instantiate()
    # We don't want to mutate the state of the global effect
    effect.components[Effect] = copy.deepcopy(template.components[Effect])


    # trait.components[TraitActivation] = activation

    # # TODO - can we copy position and put the targeting code in like trait activation, then do a filter by
    # # specific enum value?
    # match target:
    #     case TraitTarget.SELF:
    #         trait.tags.add(TargetSelf)
    #     case TraitTarget.ENEMY:
    #         trait.tags.add(TargetEnemy)

    return effect

def add_effect_to_entity(entity: Entity, effect_template: Entity):
    """
    Add the specified effect to the specified entity
    """
    effect = spawn_effect(effect_template)
    effect.relation_tag[Affecting] = entity
    return effect

def remove_effect_from_entity(entity: Entity, effect: Entity):
    """Remove the specified effect from the specified entity"""
    effect.relation_tag.pop(Affecting, None)
    effect.clear()

class Effect(Protocol):
    """A common effect protocol.."""

    __slots__ = ()

    def affect(self, entity: Entity) -> bool:
        """
        Apply this effect to `entity`.

        Returns if the effect has been fully consumed.
        """
        ...
