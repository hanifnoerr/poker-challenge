import unittest

from poker_challenge.bots import calling_station, tight_aggressive
from poker_challenge.match import run_match


class MatchTests(unittest.TestCase):
    def test_exactly_five_games_and_zero_sum(self):
        result = run_match([tight_aggressive, calling_station], paired_deals=3)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(result["games"]), 5)
        self.assertEqual(result["hands_completed"], 30)
        self.assertEqual(sum(result["net_chips"]), 0)
        self.assertEqual(result["net_chips"][0], sum(g["net_chips"][0] for g in result["games"]))

    def test_identical_agents_cancel_each_paired_deal(self):
        records = []
        result = run_match([tight_aggressive] * 2, paired_deals=5, replay_sink=records.append)
        self.assertEqual(result["net_chips"], [0, 0])
        self.assertIsNone(result["winner"])
        for i in range(0, len(records), 2):
            a, b = records[i:i + 2]
            self.assertEqual(a["hole_cards"], b["hole_cards"])
            self.assertEqual(a["dealt_board"], b["dealt_board"])
            self.assertEqual(a["button"], b["button"])
            self.assertEqual(a["seat_to_agent"], [0, 1])
            self.assertEqual(b["seat_to_agent"], [1, 0])
            self.assertEqual(a["result"], b["result"])

    def test_seed_reproduces_match(self):
        bots = [tight_aggressive, calling_station]
        self.assertEqual(run_match(bots, 2, seed=9), run_match(bots, 2, seed=9))

    def test_invalid_agent_forfeits_without_fake_chip_result(self):
        result = run_match([lambda o, c: {"action": "cheat"}, calling_station], paired_deals=1)
        self.assertEqual(result["status"], "forfeit")
        self.assertEqual(result["winner"], 1)
        self.assertIsNone(result["net_chips"])

    def test_crashed_agent_forfeits(self):
        def broken(obs, config):
            raise RuntimeError("test crash")
        result = run_match([broken, calling_station], paired_deals=1)
        self.assertEqual((result["status"], result["loser"]), ("forfeit", 0))

    def test_observation_mutations_do_not_change_game(self):
        def mutator(obs, config):
            action = calling_station(obs, config)
            obs["stacks"][:] = [0, 0]
            obs["hole_cards"][:] = ["As", "As"]
            config["starting_stack"] = -1
            return action
        result = run_match([mutator, calling_station], paired_deals=3)
        self.assertEqual(result["net_chips"], [0, 0])

    def test_bad_match_parameters(self):
        for n in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                run_match([calling_station] * 2, paired_deals=n)


if __name__ == "__main__":
    unittest.main()
