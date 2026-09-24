# Poker Bot Challenge — competition proposal

Status: draft for discussion, not a deployed competition. Target: a Kaggle-style poker bot environment for competition preparation and possible Kaggle hosting. The supplied announcement specifies four Swiss-style rounds and five games per round. The actual competition's detailed rules remain unknown. Heads-up no-limit Texas Hold'em is a proposed adaptation, not a verified rule. Kaggle platform support for this exact format is unconfirmed.

## Participant experience

Teams build an agent, test it locally against starter bots, submit a version, and watch match replays and standings. A practice period precedes the official tournament. Freeze one validated submission per team before round one; use that version for all four rounds. Practice results do not count toward final standings.

Use virtual chips. Entry fees, prizes, dates, team size, and expected participant count remain organizer decisions.

## Proposed poker format

- Heads-up no-limit Texas Hold'em; two agents per match.
- Blinds: 1/2 chips; each player starts every hand with 200 chips (100 big blinds). No rake or antes. Stacks reset each hand so a bot cannot be eliminated from a match by one hand.
- A Swiss round is a full match, not one poker hand.
- Each round pairs a bot with one opponent for five games. Proposed definition: one game is a fixed-length session of 200 paired deals, played twice with agent seats swapped (400 hands). This gives 2,000 hands per round and 8,000 across four rounds. These counts define our adaptation only; the real event's meaning of game is still unknown. Benchmark runtime and outcome variance before fixing the published workload; these counts do not guarantee statistical separation.
- Each paired deal fixes cards to seats and the board. Play both copies in separate isolated sessions with no shared agent memory, logs, seed, or access to the other copy. Match history must not leak the paired cards.
- The engine owns shuffling, hidden cards, betting validation, settlement, and accounting. Agents see their own hole cards and public game information only.
- Match result: aggregate net chip profit across all five games. Positive profit wins, zero draws, negative loses. Play all five games; do not stop at three wins. Store integer chip totals as the authoritative result.

The engine specification must settle heads-up button/blind action order, minimum raises, short all-ins and reopening, unmatched bet returns, split pots and odd chips, and showdown information before implementation is accepted.

## Exactly four Swiss-style rounds

Everyone remains eligible for all four rounds; there is no elimination or additional final.

1. Round one: pair using a published deterministic shuffle of the frozen entrant list and a recorded draw seed.
2. Rounds two through four: pair entrants with similar current match points, avoiding repeat opponents whenever a complete pairing without repeats exists. Pairing is global, not a greedy adjacent-list operation. Minimize repeats first, then total point gaps, with deterministic entrant-ID tie resolution. This is a custom Swiss-style rule, not a claim of compliance with a federation system.
3. Award 1 point for a match win, 0.5 for a draw, and 0 for a loss.
4. With an odd field, award one bye worth 1 point: choose the lowest-ranked eligible entrant who has not previously received a bye. A bye has no chip result. Require at least five entrants for this proposed policy; define a different small-field format if necessary.
5. Rank by match points, then opponent strength (sum of final match points of actual opponents; a bye contributes zero), then aggregate big blinds won per 100 actually played hands. If still tied, share the rank; use entrant ID only for stable display order. A prize-split policy is required if prizes are offered.
6. Complete and validate every result before pairing the next round. Save the exact pairing, submission hashes, engine version, configuration, and seed references for an audit.

Four rounds provide only four opponents per entrant. Larger fields can have multiple undefeated entrants and noisy rankings. Publish the tie rules prominently; do not imply that this format always identifies a unique strongest bot. Byes can also affect opponent-strength comparisons under the simple rule above.

## Submission contract

Proposed initial interface: Python agent(observation, configuration) returning a structured action.

Observation includes own hole cards, visible board, acting seat, button, stacks, pot, current street, public betting history, amount to call, and exact legal action bounds. It excludes opponent hole cards unless legitimately revealed, future cards, deck order, and engine random state.

Actions: fold, check, call, or raise-to with an integer total contribution for the current street. The engine supplies min/max raise-to bounds and explicit short-all-in legality. Publish machine-readable schemas and legal example actions.

Before launch, fix runtime version, allowed packages, submission size, CPU/memory/output limits, action timeout, and total match budget using benchmark results. Validation must use the same runtime as official evaluation.

An invalid action, timeout, or agent crash forfeits the match for that agent. If both fail, record a double forfeit with zero points each. Forfeits carry no invented chip profit. Organizer infrastructure failures invalidate the affected attempt and trigger a controlled rerun of the whole match; retain attempt records and count one accepted result only.

## Minimum system

For Kaggle hosting, first agree with Kaggle which services their platform provides. The list below defines required capabilities, not a commitment to build a separate website or duplicate Kaggle infrastructure. The custom poker environment, starter agents, tests, and rules can be developed locally while integration details are resolved.

- Poker engine and participant SDK: deterministic local play, schemas, example bots, hand histories, replay data.
- Tournament service: entrant registration, submission freezing, four-round pairing, result validation, standings, and audit export.
- Evaluation workers: execute each untrusted agent separately with no network, no host secrets or filesystem access, and enforced resource limits. A Python subprocess alone is not a sandbox.
- Website: overview, rules, getting started, submission status, round pairings, leaderboard, and replay viewer.
- Organizer controls: close submissions, validate the field, start each round, investigate failures, rerun invalid attempts, and publish final results.

Keep private evaluation seeds and detailed replays inaccessible to active agents. Publish spectator replays only after the relevant matches finish. Separate public replays from privileged debugging logs.

## Build and acceptance plan

1. Confirm participant type, poker format, and expected field size. Confirm custom simulation hosting and exactly four Swiss rounds with Kaggle through its hosting inquiry route. Verify the rules fit these choices.
2. Implement the poker engine and local SDK. Verify hand ranking, betting edge cases, chip conservation, observation privacy, and deterministic replay with meaningful automated tests.
3. Implement the tournament runner. Verify exactly four rounds, one appearance per entrant per round including byes, no avoidable rematches, correct standings, odd fields, tied scores, and resumable accepted results.
4. Run a complete local pilot using baseline agents. Measure runtime and result variability before fixing hand counts and compute limits.
5. Integrate with the hosting and evaluation services agreed with Kaggle. Verify submission-to-result flow, timeouts, crashes, resource limits, and replay permissions before accepting outside code.
6. Publish the finalized rules, schedule, starter kit, and organizer runbook. Deploy only after hosting and operating arrangements are selected.

## References and limits

- [Northeastern ACM event](https://buttered-lupin-75d.notion.site/Algorithmic-Poker-Event-hosted-by-ACM-at-Northeastern-in-Collaboration-with-Code4Community-Disrupt--1a1b5df6bd4180838523cf0743b96813), read in the browser: uses multiplayer tables with timed elimination, not the four-round Swiss format.

- Inspiration: [Kaggriculture](https://www.kaggle.com/competitions/kaggriculture/overview) and [Orbit Wars](https://www.kaggle.com/c/orbit-wars). Their full rules were not available through the fetched overview pages; the rules above are our proposal, not a reproduction of their evaluation formats.
- [Official Kaggle Environments repository](https://github.com/Kaggle/kaggle-environments) documents observation/action agents, evaluation, and replay rendering. It is a useful integration reference; it does not establish permission or support for hosting our custom competition on Kaggle.
- Kaggle-hosted custom simulation support and Swiss scheduling need confirmation before committing to that hosting route.
- [Kaggle hosting inquiry](https://www.kaggle.com/c/about/host?dialog=docshostgetstarted) explicitly advertises simulation competitions with custom game environments. The public material checked does not establish self-service access to custom Swiss scheduling, pricing, or acceptance of this proposal.
