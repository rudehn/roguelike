from enum import auto, Enum

import attrs

class DamageType(Enum):
    PHYSICAL = auto()
    POISON = auto()
    FIRE = auto()

class ResistanceLevel(Enum):
    WEAK = auto() # 50% more damage
    NONE = auto() # 100% damage (default)
    MODERATE = auto() # 33% less damage
    HIGH = auto() # 66% less damage
    IMMUNE = auto() # No damage
    HEALED = auto() # 33% healing

@attrs.define(frozen=True)
class DamageResistance:
    damage_type: DamageType
    resistance: ResistanceLevel

@attrs.define
class AttackData:
    damage_type: DamageType
    damage_amount: int

# TODO - weapon types, to determine bleed?
