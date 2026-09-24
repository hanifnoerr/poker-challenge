"""Round-robin evaluation: every pair plays five games on each selected seed."""

from itertools import combinations
from .match import run_match


def run_tournament(bots, paired_deals, seed, repeats, progress=None, save_match=None):
    standings = {b["id"]: {"id": b["id"], "name": b["name"], "points": 0,
                 "wins": 0, "draws": 0, "losses": 0, "net_chips": 0,
                 "hands": 0, "forfeits": 0} for b in bots}
    matches = []
    for repeat in range(repeats):
        # Every pair uses the same deck schedule within a repetition.
        match_seed = (seed + repeat) % 2**32
        for a, b in combinations(bots, 2):
            if progress:
                progress(len(matches), [a["name"], b["name"]])
            result = run_match([a["agent"], b["agent"]], paired_deals, match_seed)
            result.update(agents=[a["name"], b["name"]], bot_ids=[a["id"], b["id"]])
            if save_match:
                save_match(result)
            matches.append(result)
            rows = [standings[a["id"]], standings[b["id"]]]
            for i, row in enumerate(rows):
                if result["winner"] is None:
                    row["points"] += 0.5
                    row["draws"] += 1
                elif result["winner"] == i:
                    row["points"] += 1
                    row["wins"] += 1
                else:
                    row["losses"] += 1
                if result["status"] == "complete":
                    row["net_chips"] += result["net_chips"][i]
                    row["hands"] += result["hands_completed"]
                elif result["loser"] == i:
                    row["forfeits"] += 1
    # Failed bots cannot win by benefiting from forfeits elsewhere.
    def score(row):
        return (row["forfeits"] == 0, row["points"], row["net_chips"])
    ordered = sorted(standings.values(), key=lambda r: r["id"])
    ordered.sort(key=score, reverse=True)
    for i, row in enumerate(ordered):
        row["rank"] = ordered[i-1]["rank"] if i and score(row) == score(ordered[i-1]) else i+1
        row["eligible"] = row["forfeits"] == 0
    return {"status": "complete", "standings": ordered, "matches": matches,
            "matches_completed": len(matches), "total_matches": len(matches),
            "paired_deals": paired_deals, "seed": seed, "repeats": repeats,
            "winner_ids": [r["id"] for r in ordered if r["rank"] == 1 and r["eligible"]]}
