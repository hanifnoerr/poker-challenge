"""Five-session evaluator for trusted, stateless Python functions."""

from dataclasses import asdict
from random import Random

from .engine import Hand, Rules


class AgentError(RuntimeError):
    def __init__(self, agent_index, message):
        super().__init__(f"Agent {agent_index}: {message}")
        self.agent_index = agent_index


def play_hand(agents, seed, button, rules=None, seat_to_agent=(0, 1)):
    hand = Hand(seed=seed, button=button, rules=rules)
    frames = []
    while not hand.done:
        agent_index = seat_to_agent[hand.actor]
        frames.append(hand.observation())
        try:
            action = agents[agent_index](hand.observation(), asdict(hand.rules))
        except Exception as exc:
            raise AgentError(agent_index, f"agent failed: {type(exc).__name__}: {str(exc)[:300]}") from exc
        try:
            hand.step(action)
        except ValueError as exc:
            raise AgentError(agent_index, str(exc)) from exc
    return {**hand.replay(), "frames": frames}


def run_match(agents, paired_deals=200, seed=42, rules=None, replay_sink=None):
    """Exactly five games; two seat assignments per deal, fresh hand each time.

    Only use trusted stateless functions. This runner does not isolate processes
    or enforce timeouts; arbitrary third-party submissions must not run here.
    """
    if len(agents) != 2:
        raise ValueError("A match requires two agents")
    if type(paired_deals) is not int or paired_deals < 1:
        raise ValueError("paired_deals must be a positive integer")
    rules = rules or Rules()
    rng = Random(seed)
    totals = [0, 0]
    games = []
    hands = 0
    for game in range(5):
        profit = [0, 0]
        for deal in range(paired_deals):
            deal_seed = rng.getrandbits(128)
            button = deal % 2
            for copy, mapping in enumerate(((0, 1), (1, 0))):
                try:
                    replay = play_hand(agents, deal_seed, button, rules, mapping)
                except AgentError as exc:
                    return {
                        "status": "forfeit", "winner": 1 - exc.agent_index,
                        "loser": exc.agent_index, "error": str(exc),
                        "games": games, "hands_completed": hands,
                        "failure_location": {"game": game + 1, "deal": deal + 1, "copy": copy},
                        "net_chips": None, "seed": seed, "rules": asdict(rules),
                    }
                for seat, agent_index in enumerate(mapping):
                    profit[agent_index] += replay["result"]["net_chips"][seat]
                hands += 1
                if replay_sink is not None:
                    replay_sink({"game": game + 1, "deal": deal + 1, "copy": copy,
                                 "seat_to_agent": list(mapping), **replay})
        games.append({"game": game + 1, "hands": paired_deals * 2, "net_chips": profit})
        totals = [totals[p] + profit[p] for p in (0, 1)]
    return {
        "status": "complete", "seed": seed, "rules": asdict(rules),
        "games": games, "hands_completed": hands, "net_chips": totals,
        "bb_per_100": [v / rules.big_blind * 100 / hands for v in totals],
        "winner": None if totals[0] == 0 else (0 if totals[0] > 0 else 1),
    }
