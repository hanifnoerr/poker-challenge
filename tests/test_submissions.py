import tempfile
from pathlib import Path
import unittest

from poker_challenge.engine import Hand
from poker_challenge.submissions import ScriptAgent
from starter_bot import agent


class ScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "bot.py"
        self.observation = Hand().observation()
        self.config = {"big_blind": 2}

    def bot(self, source, timeout=3):
        self.path.write_text(source, encoding="utf-8")
        return ScriptAgent(self.path, timeout)

    def test_script_action_and_prints(self):
        bot = self.bot('print("debug")\ndef agent(o,c):\n print("more debug")\n return {"action":"call"}\n')
        self.assertEqual(bot(self.observation, self.config), {"action": "call"})

    def test_fresh_interpreter_per_decision(self):
        bot = self.bot('count=0\ndef agent(o,c):\n global count\n count+=1\n return {"action":"call","count":count}\n')
        self.assertEqual(bot(self.observation, self.config)["count"], 1)
        self.assertEqual(bot(self.observation, self.config)["count"], 1)

    def test_timeout(self):
        bot = self.bot('import time\ndef agent(o,c):\n time.sleep(5)\n', timeout=0.3)
        with self.assertRaisesRegex(ValueError, "exceeded"):
            bot(self.observation, self.config)

    def test_missing_function_and_crash(self):
        for source in ('x=1', 'def agent(o,c):\n raise RuntimeError("broken bot")'):
            with self.assertRaises(ValueError):
                self.bot(source)(self.observation, self.config)

    def test_starter_is_reproducible_and_legal(self):
        for seed in range(8):
            h = Hand(seed=seed)
            while not h.done:
                obs = h.observation()
                a = agent(obs, self.config)
                self.assertEqual(a, agent(obs, self.config))
                h.step(a)


if __name__ == "__main__":
    unittest.main()
