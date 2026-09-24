import json
import random
import unittest

from poker_challenge.cards import DECK
from poker_challenge.engine import Hand, Rules


def fixed_deck(prefix):
    cards = prefix.split()
    return cards + [c for c in DECK if c not in cards]


def finish_by_calling(hand):
    while not hand.done:
        hand.step({"action": "check" if "check" in hand.legal_actions() else "call"})


class EngineTests(unittest.TestCase):
    def test_blinds_and_preflop_option(self):
        h = Hand()
        self.assertEqual(h.stacks, [199, 198])
        self.assertEqual(h.actor, 0)
        self.assertEqual(h.observation()["to_call"], 1)
        self.assertEqual(h.legal_actions()["raise"]["min_to"], 4)
        h.step({"action": "call"})
        self.assertEqual(h.actor, 1)
        self.assertEqual(h.street, "preflop")
        h.step({"action": "check"})
        self.assertEqual((h.street, h.actor, h.pot), ("flop", 1, 4))
        self.assertEqual(len(h.board), 3)

    def test_fold_refunds_unmatched_blind(self):
        h = Hand()
        h.step({"action": "fold"})
        self.assertEqual(h.result["net_chips"], [-1, 1])
        self.assertEqual(h.result["refunds"], [0, 1])
        self.assertEqual(h.board, [])

    def test_raise_to_and_minimum_reraise(self):
        h = Hand()
        h.step({"action": "raise", "amount": 10})
        self.assertEqual(h.stacks, [190, 198])
        self.assertEqual(h.legal_actions()["raise"]["min_to"], 18)
        h.step({"action": "raise", "amount": 18})
        h.step({"action": "call"})
        self.assertEqual(h.pot, 36)
        self.assertEqual(h.committed, [0, 0])
        self.assertEqual(h.legal_actions()["raise"]["min_to"], 2)

    def test_invalid_action_does_not_mutate(self):
        h = Hand()
        before = h.observation()
        for action in (None, {}, {"action": []}, {"action": "check"},
                       {"action": "raise", "amount": 3}, {"action": "raise", "amount": 201},
                       {"action": "raise", "amount": 4.0}, {"action": "raise", "amount": True}):
            with self.assertRaises(ValueError):
                h.step(action)
            self.assertEqual(before, h.observation())

    def test_all_in_runs_out_and_awards_best_hand(self):
        h = Hand(deck=fixed_deck("As Ad Ks Kd 2c 3h 7d 9s Jc"))
        h.step({"action": "raise", "amount": 200})
        self.assertNotIn("raise", h.legal_actions())
        h.step({"action": "call"})
        self.assertTrue(h.done)
        self.assertEqual(len(h.board), 5)
        self.assertEqual(h.result["net_chips"], [200, -200])

    def test_short_all_in_raise_then_call(self):
        h = Hand(rules=Rules(starting_stack=5))
        h.step({"action": "raise", "amount": 4})
        self.assertEqual(h.legal_actions()["raise"], {"min_to": 5, "max_to": 5, "short_all_in_only": True})
        h.step({"action": "raise", "amount": 5})
        self.assertNotIn("raise", h.legal_actions())
        h.step({"action": "call"})
        self.assertTrue(h.done)

    def test_all_in_big_blind_needs_only_call(self):
        h = Hand(rules=Rules(starting_stack=2))
        h.step({"action": "call"})
        self.assertTrue(h.done)
        self.assertEqual(sum(h.result["final_stacks"]), 4)

    def test_split_pot(self):
        h = Hand(deck=fixed_deck("2c 3d 9h 9d Ts Js Qs Ks As"))
        finish_by_calling(h)
        self.assertEqual(h.result["winners"], [0, 1])
        self.assertEqual(h.result["net_chips"], [0, 0])

    def test_observation_has_only_visible_cards_and_is_detached(self):
        h = Hand(deck=fixed_deck("As Ad Ks Kd 2c 3h 7d 9s Jc"))
        obs = h.observation()
        self.assertEqual(obs["hole_cards"], ["As", "Ad"])
        for hidden in ["Ks", "Kd", "2c", "3h", "7d", "9s", "Jc", "seed", "deck"]:
            self.assertNotIn(hidden, json.dumps(obs))
        obs["stacks"][0] = -999
        obs["hole_cards"][0] = "Ks"
        self.assertEqual(h.stacks[0], 199)
        self.assertEqual(h.observation()["hole_cards"], ["As", "Ad"])
        with self.assertRaises(ValueError):
            h.replay()

    def test_street_action_order_and_history_is_detached(self):
        h = Hand(button=1)
        h.step({"action": "call"})
        h.step({"action": "check"})
        for street, count in [("flop", 3), ("turn", 4), ("river", 5)]:
            self.assertEqual((h.street, len(h.board), h.actor), (street, count, 0))
            obs = h.observation()
            obs["history"][0]["action"] = "corrupted"
            self.assertEqual(h.history[0]["action"], "call")
            h.step({"action": "check"})
            h.step({"action": "check"})
        self.assertTrue(h.done)

    def test_seed_reproduces_hand(self):
        a, b = Hand(seed=918), Hand(seed=918)
        finish_by_calling(a)
        finish_by_calling(b)
        self.assertEqual(a.replay(), b.replay())

    def test_random_legal_games_conserve_chips_and_terminate(self):
        rng = random.Random(12)
        for seed in range(300):
            h = Hand(seed=seed, button=seed % 2, rules=Rules(starting_stack=seed % 99 + 2))
            count = 0
            while not h.done:
                self.assertEqual(sum(h.stacks) + h.pot, h.rules.starting_stack * 2)
                self.assertGreaterEqual(min(h.stacks), 0)
                legal = h.legal_actions()
                kind = rng.choice(list(legal))
                action = {"action": kind}
                if kind == "raise":
                    action["amount"] = rng.randint(legal[kind]["min_to"], legal[kind]["max_to"])
                h.step(action)
                count += 1
                self.assertLess(count, 500)
            self.assertEqual(sum(h.result["net_chips"]), 0)
            self.assertGreaterEqual(min(h.stacks), 0)

    def test_rules_validation(self):
        for kwargs in ({"starting_stack": 1}, {"big_blind": 1}, {"small_blind": 0}, {"starting_stack": 2.0}):
            with self.assertRaises(ValueError):
                Rules(**kwargs)
