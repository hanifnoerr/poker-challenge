"""Run trusted local submissions with a per-decision wall-clock deadline."""

import json
from pathlib import Path
import subprocess
import sys


class ScriptAgent:
    def __init__(self, path, timeout=3):
        self.path = Path(path).resolve()
        self.timeout = timeout
        if not self.path.is_file() or self.path.suffix.lower() != ".py":
            raise ValueError("Expected an existing Python bot file")

    def __call__(self, observation, configuration):
        worker = Path(__file__).with_name("script_worker.py")
        try:
            process = subprocess.run(
                [sys.executable, "-I", str(worker), str(self.path)],
                input=json.dumps({"observation": observation, "configuration": configuration}),
                capture_output=True, text=True, encoding="utf-8", timeout=self.timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError(f"Decision exceeded {self.timeout:g} seconds") from exc
        if process.returncode:
            lines = process.stderr.strip().splitlines()
            raise ValueError(lines[-1][:300] if lines else "Bot process exited without an action")
        if len(process.stdout) > 4096:
            raise ValueError("Bot response too large")
        try:
            return json.loads(process.stdout)
        except json.JSONDecodeError as exc:
            raise ValueError("Bot did not return a JSON-compatible action") from exc
