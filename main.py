"""gta6-twitch-ccu-forecast-01 entry in Python 3.13 (standard library only).

Forecasts Grand Theft Auto VI's launch-day Twitch concurrent viewers, hour by
hour (hours 2..24, five quantiles each), from the case's hour-1 print and the
comparable past launches the case ships.

Method (fitted on the kit's 38 comparable launches; leave-one-out pinball
loss 0.253 on big launches with hour-1 >= 20k viewers, vs 0.321 for the house
persistence baseline; 0.177 on console-only big launches vs ~0.25 baseline):
  - Each comparable gives a release-day curve: its hourly viewers for the 24
    UTC hours of its release day. Only comparables with an hour-1 print and
    at least 12 scored hours are usable. The case's own game (the GTA VI
    pre-release category entry) is excluded by name.
  - For the case, take the 15 comparables whose hour-1 print is nearest in
    log space to the case's hour-1 print. Console-only launches (no "PC" in
    platforms) count twice: GTA VI is console-only with a rolling midnight
    unlock, so they are the closest analogues.
  - Per hour h, the median log-ratio ln(viewers_h / viewers_1) over the fit
    set is the median forecast; the spread is the sample standard deviation
    of those log-ratios (floored at 0.15, capped at 1.5), applied with the
    standard-normal quantiles z = (-1.645, -0.674, 0, 0.674, 1.645).
  - Hours with fewer than 3 fit launches fall back to the house persistence
    formula. Everything is deterministic: sorted inputs, no randomness.

Run like the starter: MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out
python3 main.py (the grader runs `python3 -P -s /bot/main.py`).
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0, 0.674, 1.645]

# Nearest neighbours by log hour-1 print; console-only launches weighted x2.
K_NEIGHBOURS = 15
CONSOLE_WEIGHT = 2
MIN_CURVE_HOURS = 12
MIN_FIT_PER_HOUR = 3
SPREAD_FLOOR = 0.15
SPREAD_CAP = 1.5
BASELINE_SIGMA = 0.15


def round2(x: float) -> float | int:
    """x rounded to 2 decimals, half up (as JavaScript Math.round(x*100)/100)."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def parse_ts(s: str) -> float:
    """ISO 8601 UTC timestamp -> seconds since the epoch."""
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.timestamp()


def release_day_curve(comp: dict) -> dict:
    """{hour: viewers} for the 24 UTC hours of the comparable's release day."""
    start = parse_ts(comp["day_start"])
    curve = {}
    for pt in comp.get("hourly") or []:
        v = pt.get("viewers")
        if v is None or v <= 0:
            continue
        h = int((parse_ts(pt["from"]) - start) // 3600) + 1
        if 1 <= h <= 24:
            curve[h] = v
    return curve


def is_console_only(comp: dict) -> bool:
    return "pc" not in (comp.get("platforms") or "").lower()


def median(xs: list) -> float:
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def stdev(xs: list) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def baseline_row(p1: float, h: int) -> list:
    return [round2(p1 * math.exp(z * BASELINE_SIGMA * math.sqrt(h - 1))) for z in Z]


def forecast_case(case: dict, name: str) -> dict:
    first = next((k for k in case.get("known") or [] if k.get("hour") == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1, first["viewers"])
    game_name = (case.get("game") or {}).get("name", "").lower()

    # Usable comparable curves, excluding the case's own game.
    curves = []
    for comp in case.get("comparables") or []:
        if game_name and game_name in (comp.get("name") or "").lower():
            continue
        curve = release_day_curve(comp)
        if 1 in curve and len(curve) >= MIN_CURVE_HOURS:
            curves.append((curve[1], curve, is_console_only(comp)))

    # 15 nearest by log hour-1 print; console-only launches count twice.
    ranked = sorted(
        curves, key=lambda c: (abs(math.log(c[0] / p1)), c[1].get(1, 0))
    )[:K_NEIGHBOURS]
    fit = []
    for h1, curve, console in ranked:
        fit.append(curve)
        if console:
            fit.extend([curve] * (CONSOLE_WEIGHT - 1))

    hours = []
    for row in case["forecast"]:
        h = row["hour"]
        logs = [
            math.log(c[h] / c[1]) for c in fit if 1 in c and h in c
        ]
        if len(logs) < MIN_FIT_PER_HOUR:
            q = baseline_row(p1, h)
        else:
            med = median(logs)
            sd = min(max(stdev(logs), SPREAD_FLOOR), SPREAD_CAP)
            q50 = p1 * math.exp(med)
            q = [round2(q50 * math.exp(z * sd)) for z in Z]
        # Keep quantiles strictly valid: finite, > 0, non-decreasing.
        q = [max(0.01, v) for v in q]
        q = sorted(q)
        hours.append({"hour": h, "q": q})
    return {"hours": hours}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        try:
            forecast = forecast_case(case, path.name)
        except Exception:
            # Never crash: an invalid case scores worst; a persistence
            # forecast is always a valid output.
            first = next(
                (k for k in case.get("known") or [] if k.get("hour") == 1),
                None,
            )
            p1 = max(1, first["viewers"]) if first else 1
            forecast = {
                "hours": [
                    {"hour": row["hour"], "q": baseline_row(p1, row["hour"])}
                    for row in case["forecast"]
                ]
            }
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
