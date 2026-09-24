import argparse
import json
from contextlib import ExitStack
from pathlib import Path

from .bots import BASELINES
from .engine import Rules
from .match import run_match


def main():
    parser = argparse.ArgumentParser(description="Run a local five-game heads-up poker match")
    parser.add_argument("--bot-a", choices=BASELINES, default="tight_aggressive")
    parser.add_argument("--bot-b", choices=BASELINES, default="calling_station")
    parser.add_argument("--paired-deals", type=int, default=200, help="Paired deals per game (default: 200)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--stack", type=int, default=200)
    parser.add_argument("--small-blind", type=int, default=1)
    parser.add_argument("--big-blind", type=int, default=2)
    parser.add_argument("--output", type=Path, default=Path("outputs/match.json"))
    parser.add_argument("--replays", type=Path, help="Optional completed-hand JSONL file; contains private cards")
    args = parser.parse_args()
    try:
        rules = Rules(args.stack, args.small_blind, args.big_blind)
        if args.paired_deals < 1:
            raise ValueError("paired-deals must be positive")
        if args.replays and args.replays.resolve() == args.output.resolve():
            raise ValueError("Result and replay paths must differ")
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        sink = None
        if args.replays:
            args.replays.parent.mkdir(parents=True, exist_ok=True)
            stream = stack.enter_context(args.replays.open("w", encoding="utf-8"))
            sink = lambda record: stream.write(json.dumps(record) + "\n")
        result = run_match([BASELINES[args.bot_a], BASELINES[args.bot_b]],
                           args.paired_deals, args.seed, rules, sink)
    result["agents"] = [args.bot_a, args.bot_b]
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{result['status']}: {result['hands_completed']} hands across {len(result['games'])} completed games")
    print(f"Net chips: {result['net_chips']}; winner: {result['winner']} (0=bot A, 1=bot B, None=draw)")
    print(f"Results: {args.output.resolve()}")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
