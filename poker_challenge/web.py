"""Loopback-only local practice website. Run: python -m poker_challenge.web."""

import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from urllib.parse import urlparse
import uuid

from .bots import BASELINES
from .match import run_match
from .submissions import ScriptAgent
from .tournament import run_tournament

ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).with_name("static")


class Arena:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.bots_dir = self.directory / "bots"
        self.matches_dir = self.directory / "matches"
        self.bots_dir.mkdir(parents=True, exist_ok=True)
        self.matches_dir.mkdir(parents=True, exist_ok=True)
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.jobs = {}
        self.tournament_jobs = {}
        self.tournaments_dir = self.directory / "tournaments"
        self.tournaments_dir.mkdir(parents=True, exist_ok=True)

    def tournaments(self):
        return sorted((json.loads(p.read_text(encoding="utf-8"))
                       for p in self.tournaments_dir.glob("*.json")),
                      key=lambda r: r["created_at"], reverse=True)

    def start_tournament(self, data):
        ids = data.get("bot_ids")
        count, seed, repeats = data.get("paired_deals", 5), data.get("seed", 42), data.get("repeats", 3)
        if not isinstance(ids, list) or not 2 <= len(ids) <= 16 or any(not isinstance(i, str) for i in ids):
            raise ValueError("Select 2–16 bots")
        if len(set(ids)) != len(ids):
            raise ValueError("Each bot can enter once")
        if type(count) is not int or not 1 <= count <= 200:
            raise ValueError("Paired deals must be between 1 and 200")
        if type(seed) is not int or not 0 <= seed < 2**32:
            raise ValueError("Invalid seed")
        if type(repeats) is not int or not 1 <= repeats <= 10:
            raise ValueError("Seed repetitions must be between 1 and 10")
        catalog = {b["id"]: b for b in self.bots()}
        if any(i not in catalog for i in ids):
            raise ValueError("Unknown bot")
        bots = [{**catalog[i], "agent": self.resolve(i)} for i in sorted(ids)]
        if any(isinstance(b["agent"], ScriptAgent) for b in bots) and data.get("trust_scripts") is not True:
            raise ValueError("Confirm that you trust the uploaded scripts before running")
        if not self.lock.acquire(blocking=False):
            raise ValueError("Another match or tournament is running")
        identity = uuid.uuid4().hex
        job = {"id": identity, "status": "running", "matches_completed": 0,
               "total_matches": len(bots) * (len(bots)-1) // 2 * repeats, "current_pair": []}
        self.tournament_jobs[identity] = job
        threading.Thread(target=self._run_tournament, args=(identity, bots, count, seed, repeats), daemon=True).start()
        return dict(job)

    def _run_tournament(self, identity, bots, count, seed, repeats):
        try:
            def progress(completed, pair):
                self.tournament_jobs[identity].update(matches_completed=completed, current_pair=pair)
            result = run_tournament(bots, count, seed, repeats, progress=progress)
            result.update(id=identity, created_at=datetime.now(timezone.utc).isoformat(),
                          entrants=[{k: v for k, v in b.items() if k != "agent"} for b in bots])
            (self.tournaments_dir / f"{identity}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            self.tournament_jobs[identity] = result
        except Exception as exc:
            self.tournament_jobs[identity] = {"id": identity, "status": "error", "error": str(exc)[:300]}
        finally:
            self.lock.release()

    def bots(self):
        bots = [{"id": k, "name": k.replace("_", " ").title(), "type": "built-in"} for k in BASELINES]
        bots.append({"id": "starter", "name": "Equity Starter", "type": "built-in"})
        bots.extend(json.loads(p.read_text(encoding="utf-8")) for p in sorted(self.bots_dir.glob("*.json")))
        return bots

    def add_bot(self, name, source):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:
            raise ValueError("Bot name must be 1–60 characters")
        if not isinstance(source, str) or not 1 <= len(source.encode("utf-8")) <= 100_000:
            raise ValueError("Upload a Python file under 100 KB")
        compile(source, "submission.py", "exec")  # Syntax check only; no execution.
        identity = uuid.uuid4().hex
        meta = {"id": identity, "name": name.strip(), "type": "uploaded",
                "sha256": hashlib.sha256(source.encode()).hexdigest()}
        (self.bots_dir / f"{identity}.py").write_text(source, encoding="utf-8")
        (self.bots_dir / f"{identity}.json").write_text(json.dumps(meta), encoding="utf-8")
        return meta

    def resolve(self, identity):
        if identity in BASELINES:
            return BASELINES[identity]
        if identity == "starter":
            # Our own stateless baseline can run cheaply in-process.
            from starter_bot import agent
            return agent
        if identity not in {bot["id"] for bot in self.bots()}:
            raise ValueError("Unknown bot")
        return ScriptAgent(self.bots_dir / f"{identity}.py")

    def start(self, data):
        count = data.get("paired_deals", 5)
        seed = data.get("seed", 42)
        if type(count) is not int or not 1 <= count <= 200:
            raise ValueError("Paired deals must be an integer from 1 to 200")
        if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
            raise ValueError("Seed must be an integer from 0 to 4294967295")
        ids = [data.get("bot_a"), data.get("bot_b")]
        if any(not isinstance(i, str) for i in ids):
            raise ValueError("Select two bots")
        agents = [self.resolve(i) for i in ids]
        if any(isinstance(a, ScriptAgent) for a in agents) and data.get("trust_scripts") is not True:
            raise ValueError("Confirm that you trust the uploaded scripts before running")
        if not self.lock.acquire(blocking=False):
            raise ValueError("A match is already running; wait for it to finish")
        identity = uuid.uuid4().hex
        names = {b["id"]: b["name"] for b in self.bots()}
        self.jobs[identity] = {"id": identity, "status": "running", "hands_completed": 0,
                               "total_hands": count * 10, "agents": [names[i] for i in ids]}
        threading.Thread(target=self._run, args=(identity, agents, ids, count, seed), daemon=True).start()
        return dict(self.jobs[identity])

    def _run(self, identity, agents, ids, count, seed):
        folder = self.matches_dir / identity
        folder.mkdir()
        try:
            with (folder / "hands.jsonl").open("w", encoding="utf-8") as output:
                def sink(record):
                    output.write(json.dumps(record) + "\n")
                    self.jobs[identity]["hands_completed"] += 1
                result = run_match(agents, count, seed, replay_sink=sink)
            result.update(id=identity, agents=self.jobs[identity]["agents"], bot_ids=ids,
                          created_at=datetime.now(timezone.utc).isoformat(), paired_deals=count)
            (folder / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            self.jobs[identity] = result
        except Exception as exc:
            self.jobs[identity] = {"id": identity, "status": "error", "error": str(exc)[:300]}
        finally:
            self.lock.release()

    def matches(self):
        return sorted((json.loads(p.read_text(encoding="utf-8"))
                       for p in self.matches_dir.glob("*/result.json")),
                      key=lambda result: result["created_at"], reverse=True)


def handler_for(arena):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def respond(self, body, status=200, content_type="application/json"):
            if content_type == "application/json":
                body = json.dumps(body).encode()
            elif isinstance(body, str):
                body = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

        def do_GET(self):
            if not self.valid_host():
                return self.respond({"error": "Localhost access only"}, 403)
            path = urlparse(self.path).path
            if path == "/":
                page = (STATIC / "index.html").read_text(encoding="utf-8").replace("TOKEN_PLACEHOLDER", arena.token)
                return self.respond(page, content_type="text/html; charset=utf-8")
            if path in ("/app.js", "/style.css"):
                return self.respond((STATIC / path[1:]).read_bytes(), content_type="text/javascript" if path.endswith("js") else "text/css")
            if path == "/starter_bot.py":
                return self.respond((ROOT / "starter_bot.py").read_bytes(), content_type="text/plain; charset=utf-8")
            if path == "/api/bots":
                return self.respond(arena.bots())
            if path == "/api/matches":
                return self.respond(arena.matches())
            if path == "/api/tournaments":
                return self.respond(arena.tournaments())
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[:2] == ["api", "tournaments"]:
                known = {r["id"]: r for r in arena.tournaments()}
                result = arena.tournament_jobs.get(parts[2], known.get(parts[2]))
                return self.respond(result if result else {"error": "Tournament not found"}, 200 if result else 404)
            if len(parts) in (3, 4) and parts[:2] == ["api", "matches"]:
                identity = parts[2]
                # Never turn an arbitrary request path into a filesystem path.
                known = {m["id"]: m for m in arena.matches()}
                if identity not in known and identity not in arena.jobs:
                    return self.respond({"error": "Match not found"}, 404)
                if len(parts) == 4 and parts[3] == "replays":
                    if identity not in known:
                        return self.respond({"error": "Replay is available after completion"}, 409)
                    records = (arena.matches_dir / identity / "hands.jsonl").read_text(encoding="utf-8")
                    return self.respond([json.loads(line) for line in records.splitlines()])
                if len(parts) == 3:
                    return self.respond(arena.jobs.get(identity, known.get(identity)))
            return self.respond({"error": "Not found"}, 404)

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 150_000:
                    raise ValueError("Request is empty or too large")
                body = self.rfile.read(length)
                if not self.valid_host() or self.headers.get("X-Arena-Token") != arena.token:
                    return self.respond({"error": "Open the local arena page to make this request"}, 403)
                data = json.loads(body)
                if not isinstance(data, dict):
                    raise ValueError("Expected a JSON object")
                path = urlparse(self.path).path
                if path == "/api/bots":
                    return self.respond(arena.add_bot(data.get("name"), data.get("source")), 201)
                if path == "/api/matches":
                    return self.respond(arena.start(data), 202)
                if path == "/api/tournaments":
                    return self.respond(arena.start_tournament(data), 202)
                return self.respond({"error": "Not found"}, 404)
            except (ValueError, SyntaxError, UnicodeDecodeError) as exc:
                return self.respond({"error": str(exc)[:300]}, 400)
    return Handler


def main():
    parser = argparse.ArgumentParser(description="Local Poker Lab website (trusted scripts only)")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".local")
    args = parser.parse_args()
    arena = Arena(args.data_dir)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(arena))
    print(f"Poker Lab: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping local server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
