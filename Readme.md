Current entities w/components that have systems defined:

Items:
- relation_tag: IsIn
- tags: IsItem
- components:
    - Name
    - Count
    - Position
    - Graphic
    - SpawnWeight
    - AssignedKey
- Consumables
    - ApplyAction - what function is called when consumed
        - Potion: needs Effect
        - TargetScroll: needs PositionSpell
        - RandomTargetScroll: needs EntitySpell
- Equipment (currently supports weapon/armor)
    - relation-tags: EquippedBy, Affecting
    - EquipSlot
    - PowerBonus
    - DefenseBonus

Effects:
- Healing

Creatures:
- tags: IsActor, IsPlayer (Only for player)
- components:
    - Name
    - Graphic
    - HP
    - MaxHP
    - Attack
    - Defense
    - RewardXP
    - Passives
        - Health / turn
    - SpawnWeight

Combat:
- Stats


Plan for character balance:
Create different character builds
- Warrior/tank - a melee focused build with high strength & constitution. Can deal damage & block attacks
- Rogue/ranger - a ranged focus build with high dexterity, crit chance & crit damage
- Mage/spellcaster - a ranged magic focused build with high intelligence, mana pool & spell damage

TODO - how to resistances fit in here?
- Any way to mix & match parts of a build
- Block works for physical attacks
- Evade works for physical + magic
