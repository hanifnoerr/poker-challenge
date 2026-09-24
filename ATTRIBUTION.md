# Baseline inspiration

The original `starter_bot.py` implementation in this project is inspired by the
general strategy concepts described in
[aatmaj28/Algorithmic-Poker-Hackathon](https://github.com/aatmaj28/Algorithmic-Poker-Hackathon)
by Aatmaj Salunke and Yaksh Shah: hand evaluation, pot odds, position, variable
bet sizing, stack awareness, and selective bluffing.

On 24 September 2026, GitHub reported no repository license. We have not copied
its source, images, documentation, or dependencies. This is an independent
educational implementation, not their bot, an official port, or an endorsement.
Its performance does not inherit the reference project's reported event results.

Our baseline uses a simple preflop heuristic and 32 postflop Monte Carlo samples
against a uniformly random opponent hand. It is intentionally small and has no
opponent range model or cross-hand learning. Improve these choices experimentally.
