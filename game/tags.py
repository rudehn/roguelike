"""Common entity tags."""

from __future__ import annotations

from typing import Final

IsPlayer: Final = "IsPlayer"
"""Player entity."""

IsGhost: Final = "IsGhost"
"""Entity last seen position."""

IsActor: Final = "IsActor"
"""Creature category."""

IsItem: Final = "IsItem"
"""Item category."""

IsEffect: Final = "IsEffect"
"""Effect category."""

IsEffectSpawner: Final = "IsEffectSpawner"
"""Does this entity spawn an effect"""

IsBlocking: Final = "IsBlocking"
"""Entity blocks basic movement."""

IsAlive: Final = "IsAlive"
"""Enemy is spawned and has not died."""

IsTrait: Final = "IsTrait"
"""Trait category."""

TargetSelf: Final = "TargetSelf"
"""Trait targets the owner entity"""

TargetEnemy: Final = "TargetEnemy"
"""Trait targets the enemy"""

IsIn: Final = "IsIn"
"""Entity is-in relation."""

EquippedBy: Final = "EquippedBy"
"""Entity equipped-by relation."""

Affecting: Final = "Affecting"
"""Entity is-affecting relation."""
