import g
from random import Random

def roll_from_notation(notation: str):
    """
    Return a dice roll result from a set of dice specified by notation
    Notation examples: 1d20, 4d4, 2d8, etc
    """
    # TODO - validate input
    num, sides = dice_from_str(notation)
    return roll(num, sides)

def dice_from_str(notation: str):
    """
    Convert from a notation of 1d20 or 4d4 into the numerical
    inputs for a dice roll
    """
    notation = notation.replace(" ", "")
    # TODO - validate input
    num, sides = map(int, notation.split("d"))
    return num, sides

def roll(num: int, sides: int):
    total = 0
    rng = g.world[None].components[Random]
    for _ in range(num):
        total += rng.randint(1, sides)
    return total
