"""One decision per fresh interpreter. Process boundary, NOT a security sandbox."""

import contextlib
import json
from pathlib import Path
import runpy
import sys

# Support -I invocation by absolute file path on Windows and Unix.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    request = json.loads(sys.stdin.read())
    # User print statements must not contaminate the decision protocol.
    with open(__import__("os").devnull, "w") as quiet:
        with contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
            namespace = runpy.run_path(sys.argv[1], run_name="poker_submission")
            fn = namespace.get("agent")
            if not callable(fn):
                raise ValueError("Submission must define agent(observation, configuration)")
            result = fn(request["observation"], request["configuration"])
    response = json.dumps(result)
    if len(response) > 4096:
        raise ValueError("Action response exceeds 4096 characters")
    sys.stdout.write(response)


if __name__ == "__main__":
    main()
