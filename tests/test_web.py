import json
from http.server import ThreadingHTTPServer
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from poker_challenge.web import Arena, handler_for


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.arena = Arena(self.temp.name)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(self.arena))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path, data=None, token=True):
        headers = {"X-Arena-Token": self.arena.token} if token else {}
        req = Request(self.base + path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
        return urlopen(req, timeout=10)

    def test_home_static_and_bots(self):
        with self.request("/") as response:
            self.assertIn("Poker Lab", response.read().decode())
        with self.request("/api/bots") as response:
            self.assertEqual(len(json.load(response)), 3)
        with self.request("/starter_bot.py") as response:
            self.assertIn("def agent", response.read().decode())

    def test_post_requires_token(self):
        with self.assertRaises(HTTPError) as exc:
            self.request("/api/bots", {"name": "test", "source": "x=1"}, token=False)
        self.assertEqual(exc.exception.code, 403)

    def test_upload_syntax_and_trust(self):
        with self.request("/api/bots", {"name": "test", "source": 'def agent(o,c):\n return {"action":"fold"}'}) as response:
            bot = json.load(response)
        self.assertEqual(len(bot["sha256"]), 64)
        with self.assertRaises(HTTPError) as exc:
            self.request("/api/matches", {"bot_a":bot["id"], "bot_b":"calling_station", "paired_deals":1})
        self.assertEqual(exc.exception.code, 400)
        with self.assertRaises(HTTPError):
            self.request("/api/bots", {"name": "bad", "source": "def ???"})

    def test_match_results_replays_and_persistence(self):
        with self.request("/api/matches", {"bot_a":"calling_station", "bot_b":"tight_aggressive", "paired_deals":1}) as response:
            job = json.load(response)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            with self.request("/api/matches/" + job["id"]) as response:
                result = json.load(response)
            if result["status"] != "running":
                break
            time.sleep(0.02)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["hands_completed"], 10)
        self.assertEqual(len(result["games"]), 5)
        with self.request("/api/matches/" + job["id"] + "/replays") as response:
            records = json.load(response)
        self.assertEqual(len(records), 10)
        self.assertEqual(len(records[0]["frames"]), len(records[0]["actions"]))
        self.assertEqual(Arena(self.temp.name).matches()[0]["id"], job["id"])

    def test_invalid_input(self):
        for data in ({"bot_a":"../secret", "bot_b":"starter"}, {"paired_deals":201}, []):
            with self.assertRaises(HTTPError) as exc:
                self.request("/api/matches", data)
            self.assertEqual(exc.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
