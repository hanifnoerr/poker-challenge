# Kaggle setup guide review

Reviewed 24 September 2026: https://www.kaggle.com/docs/competitions-setup

The guide covers self-service prediction competitions and judged hackathons.
Prediction scoring compares submissions against a hidden solution; its custom
Python metric interface receives solution, submission, and row identifiers.
Hackathons use a published rubric and judges. The guide does not document custom
simulation onboarding or a Swiss scheduler.

Our conclusion: this page does not establish that our poker format can be launched
through either self-service route. Keep the simulator and tournament scheduler
separate, and confirm the simulation hosting route with Kaggle. Do not replace
bot play with fabricated prediction files or presentation judging.

Local milestone completed: poker engine, baseline agents, five-session runner,
tests, and raw replay export. Still pending: Swiss scheduler, Kaggle environment
adapter, notebook, isolated workers, and official hosting confirmation.
