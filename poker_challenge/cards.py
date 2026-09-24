"""Small, transparent five/seven-card evaluator. Larger tuples win."""

from collections import Counter
from itertools import combinations

RANKS = "23456789TJQKA"
SUITS = "cdhs"
DECK = tuple(rank + suit for rank in RANKS for suit in SUITS)


def rank_five(cards):
    if len(cards) != 5 or len(set(cards)) != 5 or any(c not in DECK for c in cards):
        raise ValueError("Expected five distinct cards, e.g. As or Td")
    ranks = sorted((RANKS.index(c[0]) + 2 for c in cards), reverse=True)
    groups = sorted(((n, r) for r, n in Counter(ranks).items()), reverse=True)
    unique = sorted(set(ranks))
    straight = 0
    if len(unique) == 5:
        if unique[-1] - unique[0] == 4:
            straight = unique[-1]
        elif unique == [2, 3, 4, 5, 14]:
            straight = 5
    flush = len({c[1] for c in cards}) == 1
    if flush and straight:
        return (8, straight)
    if groups[0][0] == 4:
        return (7, groups[0][1], groups[1][1])
    if [g[0] for g in groups] == [3, 2]:
        return (6, groups[0][1], groups[1][1])
    if flush:
        return (5, *ranks)
    if straight:
        return (4, straight)
    if groups[0][0] == 3:
        return (3, groups[0][1], *sorted((r for n, r in groups[1:]), reverse=True))
    if [g[0] for g in groups[:2]] == [2, 2]:
        return (2, *sorted((groups[0][1], groups[1][1]), reverse=True), groups[2][1])
    if groups[0][0] == 2:
        return (1, groups[0][1], *sorted((r for n, r in groups[1:]), reverse=True))
    return (0, *ranks)


def best_rank(cards):
    if not 5 <= len(cards) <= 7 or len(set(cards)) != len(cards):
        raise ValueError("Expected five to seven distinct cards")
    return max(rank_five(combo) for combo in combinations(cards, 5))
