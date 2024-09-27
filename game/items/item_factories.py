

import attrs

from game.items.item_types import EquipmentSlots

@attrs.define
class Equipment:
    name: str
    ch: int
    fg: tuple[int, int, int]
    slot: EquipmentSlots
    attack_bonus: str | None = attrs.field(kw_only=True, default=None)
    # damage_type
    # effects applied
    defense_bonus: int | None = attrs.field(kw_only=True, default=None)
    hp_bonus: int | None = attrs.field(kw_only=True, default=None)
    spawn_weight: tuple[tuple[int, int], ...] = attrs.field(kw_only=True, default=None)

EquipmentItems = (
    Equipment(
        name="dagger",
        ch=ord("/"),
        fg=(0, 191, 255),
        slot=EquipmentSlots.WEAPON,
        attack_bonus="1d4",
        spawn_weight=((1, 5),)
        # hp_bonus=20,
        #effects_applied=("lesser_poison",)
    ),
    Equipment(
        name="sword",
        ch=ord("/"),
        fg=(0, 191, 255),
        slot=EquipmentSlots.WEAPON,
        attack_bonus="1d6",
        spawn_weight=((4, 5),)
    ),
    Equipment(
        name="long_sword",
        ch=ord("/"),
        fg=(0, 191, 255),
        slot=EquipmentSlots.WEAPON,
        attack_bonus="1d8",
        spawn_weight=((6, 5),)
    ),
    Equipment(
        name="great_sword",
        ch=ord("/"),
        fg=(0, 191, 255),
        slot=EquipmentSlots.WEAPON,
        attack_bonus="2d6",
        spawn_weight=((8, 5),)
    ),

    Equipment(
        name="leather_armor",
        ch=ord("["),
        fg=(139, 69, 19),
        slot=EquipmentSlots.ARMOR,
        defense_bonus=1,
        spawn_weight=((1, 5),)
    ),
    Equipment(
        name="padded_armor",
        ch=ord("["),
        fg=(139, 69, 19),
        slot=EquipmentSlots.ARMOR,
        defense_bonus=2,
        spawn_weight=((3, 5),)
    ),
    Equipment(
        name="chain_mail",
        ch=ord("["),
        fg=(139, 69, 19),
        slot=EquipmentSlots.ARMOR,
        defense_bonus=3,
        spawn_weight=((5, 5),)
    ),
    Equipment(
        name="plate_armor",
        ch=ord("["),
        fg=(139, 69, 19),
        slot=EquipmentSlots.ARMOR,
        defense_bonus=5,
        spawn_weight=((7, 5),)
    )

)
