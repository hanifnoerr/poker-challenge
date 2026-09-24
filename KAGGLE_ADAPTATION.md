# Adapting the Northeastern poker event for Kaggle

This is a proposed practice and competition format. It does not claim to reproduce the unknown real competition's rules or to have been accepted for Kaggle hosting.

## What the reference actually supplies

The [event page](https://buttered-lupin-75d.notion.site/Algorithmic-Poker-Event-hosted-by-ACM-at-Northeastern-in-Collaboration-with-Code4Community-Disrupt--1a1b5df6bd4180838523cf0743b96813) describes live multiplayer tables, elimination of low stacks on a timer, and removal for decisions exceeding ten seconds. It is a knockout event, not Swiss.

Its [Python bot template](https://github.com/akala47/acm_pokerbot) exposes private hole cards, board cards, pot, stack, and available actions. Its [poker application](https://github.com/SpaceRage/node-poker-app) uses a Node server, a browser frontend, WebSockets, and @chevtek/poker-engine. These are useful interface references. Code reuse needs a separate license and correctness check; neither repository has been copied into this project.

## Recommended first adaptation

| Decision | Proposal |
| --- | --- |
| Poker | Heads-up no-limit Texas Hold'em, virtual chips |
| Tournament | Exactly four Swiss-style rounds, no elimination |
| Pairing | One opponent per round; similar match points; avoid rematches |
| Five games | Five fixed-length sessions against that round's opponent |
| Pilot session length | 200 paired deals, each played in both seat assignments: 400 hands |
| Stack | 100 big blinds, reset each hand |
| Round winner | Higher aggregate net chip profit across all five sessions |
| Standings | Round points, opponent strength, then chip performance; full rules in COMPETITION_DESIGN.md |
| Agent submission | Python observation/action interface, executed by evaluator |
| Spectating | Recorded replays rather than participant-controlled live clients |

Heads-up gives each Swiss pairing an unambiguous opponent and zero-sum chip result. Multiplayer tables are closer to the reference and require different strategy, table grouping, seat balancing, and scoring. Switch to multiplayer if the real competition confirms that format.

Five games does not mean five individual hands or best-of-five in this proposal. Each session contains many hands; play all five and sum profit. Paired deals must run with independent agent state to prevent one copy revealing hidden cards in the other.

Round points make Swiss pairing straightforward, but they are not identical to ranking by total winnings. If the organizer confirms that raw winnings are the final ranking metric, revise the scoring and pairing together. The supplied promotional sentence does not resolve this.

## Kaggle integration

Implement the poker rules and deterministic replay in an environment, then expose an agent observation/action contract following [Kaggle Environments](https://github.com/Kaggle/kaggle-environments). Keep the four-round scheduler separate from the poker environment: the environment evaluates a game; the scheduler selects opponents and aggregates results.

Provide starter bots, a local runner, a training notebook usable on Kaggle, and a tournament runner. Running a notebook on Kaggle is distinct from having an official hosted simulation competition.

For official hosting, confirm custom environment onboarding, submitted-agent execution, Swiss scheduling, and final scoring with [Kaggle's hosting team](https://www.kaggle.com/c/about/host?dialog=docshostgetstarted). Do not assume a standard community competition provides these features.

## Next implementation milestone

A local, tested poker environment with two baseline agents and a five-session match runner. Then add the four-round scheduler and Kaggle notebook. Keep hand count, stacks, blinds, and session boundaries in explicit configuration so verified competition rules can replace the provisional values.

Still needed from the real organizer: poker variant, table size, meaning of game, stack/blind schedule, ranking metric, and submission/runtime contract. These are needed for faithful preparation, but not for a clearly labeled prototype.
