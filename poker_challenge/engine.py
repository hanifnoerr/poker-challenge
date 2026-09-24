"""Heads-up no-limit Hold'em with fixed starting stacks and no rake.

Raises are capped at the effective stack: chips an opponent cannot match never
enter the pot. This is equivalent to returning an unmatched overbet immediately.
Deck layout fixes two cards per seat followed by five board cards; no burns.
"""

from dataclasses import asdict, dataclass
from random import Random

from .cards import DECK, best_rank


@dataclass(frozen=True)
class Rules:
    starting_stack: int = 200
    small_blind: int = 1
    big_blind: int = 2

    def __post_init__(self):
        values = (self.starting_stack, self.small_blind, self.big_blind)
        if any(type(v) is not int for v in values):
            raise ValueError("Stacks and blinds must be integers")
        if not 0 < self.small_blind < self.big_blind <= self.starting_stack:
            raise ValueError("Require 0 < small blind < big blind <= starting stack")


class Hand:
    def __init__(self, seed=0, button=0, rules=None, deck=None):
        self.rules = rules or Rules()
        if button not in (0, 1):
            raise ValueError("Button must be seat 0 or 1")
        self.button = button
        cards = list(DECK if deck is None else deck)
        if len(cards) != 52 or set(cards) != set(DECK):
            raise ValueError("Deck must contain all 52 unique cards")
        if deck is None:
            Random(seed).shuffle(cards)
        self._hole = [cards[:2], cards[2:4]]
        self._board = cards[4:9]
        self.board = []
        self.street = "preflop"
        self.stacks = [self.rules.starting_stack] * 2
        self.committed = [0, 0]
        self.contributions = [0, 0]
        self.current_bet = self.rules.big_blind
        self.last_raise = self.rules.big_blind
        self.history = []
        self.done = False
        self.result = None
        self.actor = button
        self._pay(button, self.rules.small_blind)
        self._pay(1 - button, self.rules.big_blind)
        self.pending = {p for p in (0, 1) if self.stacks[p] > 0}

    @property
    def pot(self):
        return sum(self.contributions)

    def _pay(self, seat, amount):
        self.stacks[seat] -= amount
        self.committed[seat] += amount
        self.contributions[seat] += amount

    def legal_actions(self):
        if self.done:
            return {}
        p = self.actor
        owed = self.current_bet - self.committed[p]
        legal = {"fold": {}}
        legal["call" if owed else "check"] = {"amount": min(owed, self.stacks[p])}
        maximum = min(self.committed[p] + self.stacks[p],
                      self.committed[1 - p] + self.stacks[1 - p])
        if maximum > self.current_bet and self.stacks[1 - p] > 0:
            full_minimum = self.current_bet + self.last_raise
            legal["raise"] = {
                "min_to": min(full_minimum, maximum),
                "max_to": maximum,
                "short_all_in_only": maximum < full_minimum,
            }
        return legal

    def observation(self):
        """Fresh player-visible values only; no seed, deck, or opponent cards."""
        if self.done:
            raise ValueError("A finished hand has no acting-player observation")
        p = self.actor
        return {
            "seat": p, "button": self.button, "street": self.street,
            "hole_cards": list(self._hole[p]), "board": list(self.board),
            "stacks": list(self.stacks), "pot": self.pot,
            "street_contributions": list(self.committed),
            "to_call": min(self.current_bet - self.committed[p], self.stacks[p]),
            "legal_actions": self.legal_actions(),
            "history": [dict(event) for event in self.history],
        }

    def step(self, action):
        if self.done:
            raise ValueError("Hand already finished")
        if not isinstance(action, dict) or not isinstance(action.get("action"), str):
            raise ValueError("Action must be a dictionary with an action string")
        kind = action["action"]
        legal = self.legal_actions()
        if kind not in legal:
            raise ValueError(f"Illegal action {kind!r}")
        p = self.actor
        event = {"seat": p, "street": self.street, "action": kind}
        if kind == "raise":
            target = action.get("amount")
            bounds = legal[kind]
            if type(target) is not int or not bounds["min_to"] <= target <= bounds["max_to"]:
                raise ValueError("Raise amount must be an integer total within legal bounds")
            increment = target - self.current_bet
            self._pay(p, target - self.committed[p])
            self.current_bet = target
            self.last_raise = max(self.last_raise, increment)
            self.pending = {1 - p}
            event["amount"] = target
        elif kind in ("call", "check"):
            amount = legal[kind]["amount"]
            self._pay(p, amount)
            self.pending.discard(p)
            event["amount"] = amount
        self.history.append(event)
        if kind == "fold":
            self._finish([1 - p], "fold")
            return
        self.pending = {q for q in self.pending if self.stacks[q] > 0}
        # A lone live player only acts if still facing a bet; never bets into an all-in.
        live = [q for q in (0, 1) if self.stacks[q] > 0]
        if len(live) < 2 and all(self.committed[q] == self.current_bet for q in live):
            self._showdown()
        elif not self.pending:
            self._next_street()
        else:
            self.actor = 1 - p

    def _next_street(self):
        if self.street == "river":
            self._showdown()
            return
        street, count = {"preflop": ("flop", 3), "flop": ("turn", 4),
                         "turn": ("river", 5)}[self.street]
        self.street = street
        self.board = self._board[:count]
        self.committed = [0, 0]
        self.current_bet = 0
        self.last_raise = self.rules.big_blind
        self.pending = {0, 1}
        self.actor = 1 - self.button

    def _showdown(self):
        self.board = list(self._board)
        ranks = [best_rank(hole + self.board) for hole in self._hole]
        winners = [p for p in (0, 1) if ranks[p] == max(ranks)]
        self._finish(winners, "showdown")

    def _finish(self, winners, reason):
        # Refund any unmatched contribution (including the excess big blind on a fold).
        matched = min(self.contributions)
        refunds = [amount - matched for amount in self.contributions]
        for p in (0, 1):
            self.stacks[p] += refunds[p]
        contested = 2 * matched
        for p in winners:
            self.stacks[p] += contested // len(winners)
        # Equal integer contributions make the heads-up split pot even.
        self.result = {
            "reason": reason, "winners": winners, "contested_pot": contested,
            "refunds": refunds, "final_stacks": list(self.stacks),
            "net_chips": [s - self.rules.starting_stack for s in self.stacks],
        }
        self.done = True
        self.actor = None
        assert sum(self.stacks) == 2 * self.rules.starting_stack

    def replay(self):
        """Privileged completed-hand record. Never passed to agents."""
        if not self.done:
            raise ValueError("Replay is available only after completion")
        return {
            "rules": asdict(self.rules), "button": self.button,
            "hole_cards": [list(h) for h in self._hole],
            "dealt_board": list(self._board), "board": list(self.board),
            "actions": [dict(event) for event in self.history], "result": self.result,
        }
