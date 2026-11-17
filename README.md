[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Rhcuan69/gta6-twitch-ccu-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Rhcuan69/gta6-twitch-ccu-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

# GTA VI launch-day Twitch viewers — hourly forecast

Entry for the make.fun bounty
[Forecast GTA VI's launch-day Twitch viewers hour by hour](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)
(`gta6-twitch-ccu-forecast-01`, $250): a program that reads one case
(Twitch's concurrent viewers in the "Grand Theft Auto VI" category up to
the end of the first hour of release day, 2026-11-19 UTC) and forecasts
hours 2–24 as five quantiles each (0.05, 0.25, 0.5, 0.75, 0.95), scored
by mean pinball loss on the log scale.

## Model (`main.py`, Python 3.13, standard library only, no network, deterministic)

A kernel-weighted ratio curve over the case's comparable past launches:

- Each comparable gives a release-day curve: its hourly Twitch viewers
  for the 24 UTC hours of its release day. Only comparables with an
  hour-1 print and at least 12 scored hours are usable; the case's own
  game (the GTA VI pre-release category entry) is excluded by name.
- Every usable comparable contributes, weighted by how close its hour-1
  print is to the case's: a Gaussian kernel on the log distance,
  exp(-d^2 / 2) with d = |ln(h1 / p1)|. There is no hard neighbour
  cutoff, so the fit degrades smoothly when the target sits outside the
  comparables' range (as GTA VI's launch likely will). Console-only
  launches (no "PC" in platforms) count twice: GTA VI is console-only
  with a rolling midnight unlock, so they are the closest analogues.
- Per hour h, the weighted median log-ratio `ln(viewers_h / viewers_1)`
  over the fit set, shrunk 0.9 toward persistence, is the median
  forecast; the spread is the weighted standard deviation of those
  log-ratios (floored at 0.15, capped at 1.5), applied with the
  standard-normal quantiles z = (-1.645, -0.674, 0, 0.674, 1.645).
- Hours with fewer than 3 fit launches fall back to the house
  persistence formula.

## Why this, and what was tried

Leave-one-out backtest on the kit's 38 comparable launches, scored with
the official pinball loss (mean over launches):

| model | big launches (hour-1 ≥ 20k) | huge launches (hour-1 ≥ 100k) | all 37 usable |
|---|---|---|---|
| house baseline (flat at hour-1 print) | 0.3214 | 0.2611 | 0.9297 |
| round 1 (nearest 15, console x2) | 0.2532 | 0.2226 | 0.6165 |
| **this entry (kernel σ=1.0, console x2, shrink 0.9)** | **0.2522** | **0.2140** | **0.4168** |

The huge-launch column is the one that matters most: GTA VI's hour-1
print will likely be the largest ever, far above the biggest comparable
(God of War Ragnarok, 270k). A hard top-15 cutoff treats the 15th and
16th neighbours identically and ignores how far the target sits from
them; the Gaussian kernel weights every comparable by its log distance,
so the fit follows the target's scale smoothly and still behaves
sensibly when the target extrapolates beyond all comparables. Shrinking
the median centre 0.9 toward persistence helps big and huge launches a
little (0.2532 → 0.2522, 0.2226 → 0.2140) and never hurt a subset.
Empirical quantiles and asymmetric spreads were both worse than the
normal-quantile spread, and spread multipliers 0.8 / 1.2 were both
slightly worse than 1.0, so the spread stays the weighted residual
standard deviation with a 0.15 floor.

Small launches (hour-1 under 20k) are still forecast poorly by every
model tried (baseline 2.57, this entry 0.96–1.80): their hour-1 print
carries almost no information about the day's peak. That does not
matter here — the final case is a mega-launch.

## Local testing

- `python3 main.py` with `MAKEFUN_INPUT_DIR` / `MAKEFUN_OUTPUT_DIR` set
  (defaults `/input` and `/output`). Runs the 4 practice cases in ~0.2 s
  total (~0.05 s per case, cap 8 s). Two runs on the same case are
  byte-identical.
- The practice cases have no answers in the kit (the server grades them),
  so the numbers above come from a leave-one-out backtest over the
  comparable launches shipped in the cases, run through `main.py` itself.
