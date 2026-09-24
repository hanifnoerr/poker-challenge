import unittest

from poker_challenge.cards import best_rank, rank_five


class RankingTests(unittest.TestCase):
    def test_categories_in_order(self):
        examples = ["As Kd 9h 7c 3s", "As Ad 9h 7c 3s", "As Ad 9h 9c 3s",
                    "As Ad Ah 7c 3s", "As 2d 3h 4c 5s", "As Js 9s 7s 3s",
                    "As Ad Ah 7c 7s", "As Ad Ah Ac 3s", "9s Ts Js Qs Ks"]
        values = [rank_five(e.split()) for e in examples]
        self.assertEqual([v[0] for v in values], list(range(9)))
        self.assertEqual(values, sorted(values))

    def test_wheel_loses_to_six_high(self):
        self.assertLess(rank_five("As 2d 3h 4c 5s".split()), rank_five("2s 3d 4h 5c 6s".split()))

    def test_two_trips_choose_higher_full_house(self):
        self.assertEqual(best_rank("As Ad Ah Ks Kd Kh 2c".split()), (6, 14, 13))

    def test_three_pairs_select_best_two_and_kicker(self):
        self.assertEqual(best_rank("As Ad Ks Kd Qs Qd 2c".split()), (2, 14, 13, 12))

    def test_flush_uses_all_kickers(self):
        self.assertGreater(best_rank("As Js 9s 7s 4s".split()), best_rank("Ah Jh 9h 7h 3h".split()))

    def test_board_can_play(self):
        board = "Ts Js Qs Ks As".split()
        self.assertEqual(best_rank(board + ["2c", "3d"]), best_rank(board + ["9h", "9d"]))

    def test_invalid_cards(self):
        for cards in (["As"] * 5, "As Kd Qh Jc XX".split(), ["As", "Kd"]):
            with self.assertRaises(ValueError):
                best_rank(cards)
