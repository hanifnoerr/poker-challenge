"""Stateless starter agents, not competitive poker strategies.

Each returns {"action": "fold"|"check"|"call"|"raise", "amount": raise_to}.
The amount on a raise is the total contribution on this betting street.
"""

from .cards import RANKS, best_rank


def calling_station(observation, configuration):
    legal = observation["legal_actions"]
    return {"action": "check" if "check" in legal else "call"}


def tight_aggressive(observation, configuration):
    legal = observation["legal_actions"]
    hole = observation["hole_cards"]
    values = sorted((RANKS.index(c[0]) + 2 for c in hole), reverse=True)
    if observation["street"] == "preflop":
        strong = values[0] == values[1] or values[1] >= 11
        playable = strong or values[0] >= 12 or (hole[0][1] == hole[1][1] and values[1] >= 7)
    else:
        category = best_rank(hole + observation["board"])[0]
        strong = category >= 2
        playable = category >= 1
    if strong and "raise" in legal:
        bounds = legal["raise"]
        target = max(bounds["min_to"], observation["street_contributions"][observation["seat"]]
                     + observation["to_call"] + max(configuration["big_blind"], observation["pot"] // 2))
        return {"action": "raise", "amount": min(target, bounds["max_to"])}
    if "check" in legal:
        return {"action": "check"}
    if playable and observation["to_call"] <= max(configuration["big_blind"], observation["pot"] // 3):
        return {"action": "call"}
    return {"action": "fold"}


BASELINES = {"calling_station": calling_station, "tight_aggressive": tight_aggressive}
