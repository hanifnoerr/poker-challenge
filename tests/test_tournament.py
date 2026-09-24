import unittest
from unittest.mock import patch

from poker_challenge.bots import calling_station
from poker_challenge.tournament import run_tournament


class TournamentTests(unittest.TestCase):
    def bots(self, count=3):
        return [{"id": str(i), "name": f"Bot {i}", "agent": calling_station} for i in range(count)]

    def test_all_pairs_multiple_seeds_and_ties(self):
        result = run_tournament(self.bots(), 1, 42, 2)
        self.assertEqual(result["total_matches"], 6)
        for seed in (42, 43):
            matches = [m for m in result["matches"] if m["seed"] == seed]
            self.assertEqual({tuple(m["bot_ids"]) for m in matches}, {("0", "1"), ("0", "2"), ("1", "2")})
            self.assertTrue(all(len(m["games"]) == 5 for m in matches))
        self.assertEqual(len(result["winner_ids"]), 3)
        self.assertTrue(all(r["rank"] == 1 and r["points"] == 2 for r in result["standings"]))

    def test_forfeit_cannot_win_and_no_fake_chips(self):
        bots = self.bots()
        bots[0]["agent"] = lambda o, c: {"action": "invalid"}
        result = run_tournament(bots, 1, 42, 1)
        failed = next(r for r in result["standings"] if r["id"] == "0")
        self.assertEqual(failed["forfeits"], 2)
        self.assertFalse(failed["eligible"])
        self.assertEqual(failed["net_chips"], 0)
        self.assertNotIn("0", result["winner_ids"])

    def test_net_chips_break_equal_points(self):
        results = [dict(status="complete", winner=w, net_chips=c, hands_completed=10)
                   for w, c in [(0,[10,-10]), (1,[-2,2]), (0,[3,-3])]]
        with patch('poker_challenge.tournament.run_match', side_effect=results):
            result = run_tournament(self.bots(), 1, 1, 1)
        self.assertEqual(result["winner_ids"], ["0"])
        self.assertEqual([r["net_chips"] for r in result["standings"]], [8,-1,-7])
