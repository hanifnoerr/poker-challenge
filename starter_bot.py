"""Educational poker baseline.

Change agent() to build your bot.
Only the Python standard library and poker_challenge SDK are needed.
"""

import hashlib
import json
import random

from poker_challenge.cards import DECK, RANKS, best_rank


def agent(observation, configuration):
    # Reproducible randomness from information the player is allowed to see.
    encoded = json.dumps(observation, sort_keys=True).encode()
    rng = random.Random(int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big"))
    hole = observation["hole_cards"]
    board = observation["board"]
    legal = observation["legal_actions"]
    in_position = observation["seat"] == observation["button"]
    if not board:
        # A deliberately simple preflop estimate, not a calibrated equity model.
        hi, lo = sorted((RANKS.index(c[0]) + 2 for c in hole), reverse=True)
        equity = 0.28 + (hi + lo - 4) / 55
        equity += 0.16 if hi == lo else 0
        equity += 0.035 if hole[0][1] == hole[1][1] else 0
        equity += 0.025 if hi - lo == 1 else 0
        equity = min(0.90, equity)
    else:
        # Sample a uniformly random opponent hand and missing board cards.
        # This ignores the opponent's betting range: a useful baseline to improve.
        unseen = [card for card in DECK if card not in hole + board]
        wins = 0
        samples = 32
        for _ in range(samples):
            draw = rng.sample(unseen, 2 + 5 - len(board))
            complete_board = board + draw[2:]
            ours = best_rank(hole + complete_board)
            theirs = best_rank(draw[:2] + complete_board)
            wins += 1 if ours > theirs else 0.5 if ours == theirs else 0
        equity = wins / samples
    call = observation["to_call"]
    pot = observation["pot"]
    pot_odds = call / (pot + call) if call else 0
    bluff = in_position and call == 0 and rng.random() < 0.06
    if "raise" in legal and (equity > (0.67 if in_position else 0.72) or bluff):
        limits = legal["raise"]
        # Raise roughly half a pot; bounds also enforce the effective stack.
        target = observation["street_contributions"][observation["seat"]] + call
        target += max(configuration["big_blind"], (pot + call) // 2)
        return {"action": "raise", "amount": max(limits["min_to"], min(target, limits["max_to"]))}
    if "check" in legal:
        return {"action": "check"}
    # A margin makes this baseline cautious about noisy equity estimates.
    if equity > pot_odds + 0.08:
        return {"action": "call"}
    return {"action": "fold"}
