# Poker Lab

A local poker-bot arena you can clone, run, and share with friends. Upload a Python
strategy, play a five-game heads-up match, compare winnings, and step through hand
replays in your browser. No hosting subscription, account, Node.js, or third-party
Python dependencies are required.

## Get started

Use **Python 3.11** for the tested runtime:

```sh
git clone https://github.com/hanifnoerr/poker-challenge.git
cd poker-challenge
python -m venv .venv
```

Activate with `.venv\Scripts\Activate.ps1` on Windows PowerShell, or
`source .venv/bin/activate` on macOS/Linux. Then:

```sh
python -m pip install -r requirements.txt
python -m poker_challenge.web
```

Open **http://127.0.0.1:8000**. Stop with Ctrl+C. If the port is busy, use
`python -m poker_challenge.web --port 8001`. Some systems use `python3`.
`requirements.txt` intentionally lists no packages: everything uses the standard library.

Alternatively, with Conda:

```sh
conda env create -f environment.yml
conda activate poker-challenge
python -m poker_challenge.web
```

If the environment already exists, just activate it.

## Play with a friend

1. Both of you clone this repository and use the same Git commit and Python version.
2. Download the starter from the website or copy `starter_bot.py` under a new name.
3. Edit `agent(observation, configuration)` and upload the `.py` file through the site.
4. Select your bot and a baseline. Begin with five paired deals per game (50 hands).
5. Exchange scripts. The host uploads both, checks the local trust acknowledgement,
   and runs a match. Share the result JSON or completed match folder.

Each laptop runs its own website. GitHub distributes the code; it does not execute
matches or synchronize uploads. This is not a Kaggle-hosted competition or public
remote submission service.

## Features

- Automatic round-robin tournaments: select 2–16 bots and play every pairing
  across 1–10 successive seeds, with five games per match. The default uses three
  seeds. Every pair receives the same deal schedule for each seed.
- Tournament leaderboard ordered by match points (win 1, draw 0.5), then net chips.
  Exact ties share a rank. Any bot that forfeits is ineligible to win. Forfeited
  matches contribute points but no fabricated chips. Results rank this field on
  these deals, not a universally strongest strategy.
- Saved tournament results and per-pair scores with JSON export. Tournament mode
  does not save hand replays; run an individual matchup to inspect its hands.

- Calling Station, Tight Aggressive, and Equity Starter baselines.
- Local Python uploads with syntax checks and source SHA-256 identifiers.
- Exactly five games per match, configurable deal count and seed.
- Background execution, per-game profit, total chips, and BB/100.
- Saved history, downloadable result JSON, and a visual hand replay viewer.
- Uploaded scripts run in a fresh interpreter for each decision, with a three-second
  wall-clock limit including startup and imports.

Uploads and website results live under `.local/`; CLI results under `outputs/`.
Both are ignored by Git. Replays reveal both players' cards and the full dealt board;
do not provide them to active bots.

## Bot interface

```python
def agent(observation, configuration):
    if "check" in observation["legal_actions"]:
        return {"action": "check"}
    return {"action": "call"}
```

| Observation field | Meaning |
| --- | --- |
| `hole_cards`, `board` | Your cards and visible community cards, e.g. `As`, `Td` |
| `seat`, `button`, `street` | Seat 0/1, dealer button, betting street |
| `stacks`, `pot` | Chips behind for each seat and the pot |
| `street_contributions`, `to_call` | Current-street contributions and call cost |
| `legal_actions` | Allowed actions; raise bounds are `min_to` and `max_to` |
| `history` | Public actions in this hand |

Configuration contains `starting_stack`, `small_blind`, and `big_blind`. Return
fold, check, call, or `{"action": "raise", "amount": N}`. A raise's amount is the
**total contribution on this street**, not additional chips. The engine supplies
legal short-all-in bounds. Observations omit opponent cards, future cards, deck
order, and deal seeds.

Use the standard library or `poker_challenge` SDK for reproducible single-file bots.
Mutable globals do not survive decisions in uploaded bots. Use the supplied hand
history; no persistent user-data interface is implemented. Avoid file storage,
network calls, and background processes.

## Baseline

`starter_bot.py` is an original educational implementation: preflop heuristic,
postflop Monte Carlo equity against random opponent cards, pot odds, position,
pot-relative bet sizing, and occasional bluffs. Its randomness is deterministic
from visible observations. It is not an optimal or calibrated strategy.

## Rules

- Heads-up no-limit Texas Hold'em, virtual chips, no rake or antes.
- Default blinds 1/2 and 200-chip (100 BB) stacks, reset every hand.
- Button/small blind acts first preflop; the other seat acts first postflop.
- Bets are capped at the effective stack; unmatched contributions are refunded.
  Equal-stack heads-up play needs no side pots and split contested pots are even.
- Each paired deal is played twice with bots swapped, preserving cards and button.
  The CLI defaults to 200 paired deals per game: 400 hands, or 2,000 per match.
  The website defaults to five paired deals per game for quick practice.
- All five games count. Positive aggregate chip profit wins; zero is a draw.
  This is not best-of-five. Small samples can be dominated by card variance.
- Invalid actions, exceptions, or uploaded-bot timeouts forfeit the match without
  fabricated chip scores. The runner stops at the first failure; double-failure
  adjudication is not implemented.
- Deck convention: two cards for seat 0, two for seat 1, then five board cards;
  no burns. Fix runtime, Git commit, scripts, workload, and seed to reproduce.

A deterministic deal seed does not make arbitrary submitted code deterministic.
Use the same machine for official comparisons and test multiple seeds. These are
our practice rules, not verified rules of another event.

## Execution boundary

**Only run scripts you trust.** Separate processes and timeouts are operational
controls, not a security sandbox. A script runs with your permissions and can
access your files/network or spawn child processes. There is no memory limit or
descendant-process containment. Do not expose this server through public interfaces,
tunnels, or port forwarding. It deliberately binds only to loopback. Public hosting
requires a separate, properly isolated worker system.

## Tests and CLI

```sh
python -m unittest discover -s tests -v
python -m poker_challenge --seed 42 --replays outputs/hands.jsonl
```

Tests cover ranking, betting, all-ins, payouts, observation privacy, chip
conservation, paired deals, script execution/timeouts, and web flows. Run these
tests locally; no GitHub Actions workflow is configured.

The CLI selects the two simple built-in bots; use the website for uploads and Equity
Starter. `--help` lists options. Existing CLI output paths are overwritten.
