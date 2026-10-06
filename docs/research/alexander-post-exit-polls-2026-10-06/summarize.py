"""Tabulate the post-exit scenario fits as Markdown and ``results.csv``."""

import csv
import json
from pathlib import Path

HERE = Path(__file__).parent
ORDER = ["baseline"] + [
    f"{group}-n{k}"
    for group in ("head-to-head", "control", "alexander-6pct", "alexander-3pct", "alexander-1pct")
    for k in (1, 2, 3)
]


def pct(x: float) -> str:
    return f"{100 * x:.1f}"


rows = []
for label in ORDER:
    path = HERE / "scenarios" / f"{label}.json"
    if not path.exists():
        continue
    r = json.loads(path.read_text())
    assert r["qualified"] and r["diagnostics"]["divergences"] == 0
    margin = r["chow_minus_bradford_points"]
    alex = r["election_day_full_ballot"]["alexander"]
    now = r["alexander_current_named_support"]
    rows.append(
        {
            "scenario": label,
            "polls_added": r["poll_count"],
            "chow_win": r["win_probability"]["chow"],
            "bradford_win": r["win_probability"]["bradford"],
            "alexander_win": r["win_probability"]["alexander"],
            "bradford_win_chain_se": r["bradford_win_chain_se"],
            "margin_median": margin["median"],
            "margin_lower": margin["lower"],
            "margin_upper": margin["upper"],
            "alexander_election_median": alex["median"],
            "alexander_election_lower": alex["lower"],
            "alexander_election_upper": alex["upper"],
            "alexander_now_median": now["median"],
            "retried": r["retried"],
            "worst_r_hat": r["diagnostics"]["worst_r_hat"],
            "min_ess": r["diagnostics"]["min_ess"],
        }
    )

with (HERE / "results.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(
    "| Scenario | Chow win | Bradford win | Chow − Bradford, pts (80%) "
    "| Alexander on election day, % (80%) | Alexander now, % |"
)
print("| --- | ---: | ---: | ---: | ---: | ---: |")
for row in rows:
    print(
        f"| {row['scenario']} | {pct(row['chow_win'])} | {pct(row['bradford_win'])} "
        f"| {row['margin_median']:+.1f} ({row['margin_lower']:+.1f} to {row['margin_upper']:+.1f}) "
        f"| {pct(row['alexander_election_median'])} "
        f"({pct(row['alexander_election_lower'])}–{pct(row['alexander_election_upper'])}) "
        f"| {pct(row['alexander_now_median'])} |"
    )
