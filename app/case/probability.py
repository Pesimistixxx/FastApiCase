import math
import random
from typing import Sequence

from app.skin.models import Skin_model


def calculate_probabilities(skins, sigma: int, math_exception: int):
    weights = []
    prices = [skin.price for skin in skins]

    for price in prices:
        weights.append(math.exp(-(price - math_exception) ** 2 / (2 * sigma ** 2)))

    total_weight = sum(weights)

    if total_weight == 0:
        n = len(prices)
        if n == 0:
            return []
        return [1 / n] * n

    probabilities = [w / total_weight for w in weights]

    return probabilities


def get_item_by_probability(skins: Sequence[Skin_model], sigma: int, math_exception: int, k: int):
    probabilities = calculate_probabilities(skins, sigma, math_exception)

    skins_random = random.choices(skins, weights=probabilities, k=k)
    return skins_random
