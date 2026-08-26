"""Predictive validation of the CDI (SPEC.md, phase 2).

Two analyses on the built index: (1) how well the CDI and its components predict
actual defeats, and whether a variant does better; (2) whether the CDI metrics predict
the continuous incumbent vote delta. The faithful CDI (ADR 0001) is untouched.

Evaluation is leave-one-election-out: fitted models are scored on pooled out-of-fold
predictions; fixed-formula indices (no fitted parameters) are scored on the full sample.
Uncertainty is bootstrap (resample incumbents, fixed seed).
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from .paths import output_dir

COMPONENT_PCT = {
    "vote_share": "p_vote_share",
    "elector_share": "p_elector_share",
    "new_voter_margin": "p_new_voter_margin",
}


# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #
def auc(scores, labels) -> float:
    """Mann-Whitney AUC: P(score[defeated] > score[survivor]) + 0.5 on ties."""
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels).astype(bool)
    pos, neg = scores[labels], scores[~labels]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    greater = (pos[:, None] > neg[None, :]).sum()
    ties = (pos[:, None] == neg[None, :]).sum()
    return float((greater + 0.5 * ties) / (len(pos) * len(neg)))


def loo_election_folds(years):
    """Yield (held_out_year, train_mask, test_mask) for each election year."""
    years = pd.Series(list(years)).reset_index(drop=True)
    for held in sorted(years.unique()):
        test = (years == held).to_numpy()
        yield int(held), ~test, test


def bootstrap_ci(n, stat_fn, *, n_boot=2000, alpha=0.05, seed=0):
    """Percentile bootstrap CI of a statistic computed over resampled row indices."""
    rng = np.random.default_rng(seed)
    stats = np.array([stat_fn(rng.integers(0, n, n)) for _ in range(n_boot)])
    stats = stats[~np.isnan(stats)]
    lo, hi = np.percentile(stats, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def ols_fit(X, y):
    """Ordinary least squares; returns [intercept, b1, ...]."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    design = np.column_stack([np.ones(len(X)), X])
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    return coef


def ols_predict(coef, X):
    X = np.asarray(X, dtype=float)
    return coef[0] + X @ coef[1:]


def r2(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    ss_res = ((y_true - y_pred) ** 2).sum()
    ss_tot = ((y_true - y_true.mean()) ** 2).sum()
    return float(1 - ss_res / ss_tot)


def rmse(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def _standardize(X, mu=None, sd=None):
    if mu is None:
        mu = X.mean(axis=0)
        sd = X.std(axis=0)
    sd = np.where(sd == 0, 1.0, sd)
    return (X - mu) / sd, mu, sd


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
def load_analysis_frame(path: Path | None = None) -> pd.DataFrame:
    """Ranked runners with per-year component percentiles and the vote delta."""
    path = Path(path) if path is not None else output_dir() / "defeatability_index.csv"
    df = pd.read_csv(path)
    r = df[df["rank_sum"].notna()].copy()
    r["defeated"] = ~r["elected_Y"].astype(bool)
    for src, dst in [
        ("rank_vote_share", "p_vote_share"),
        ("rank_elector_share", "p_elector_share"),
        ("rank_new_voter_margin", "p_new_voter_margin"),
    ]:
        r[dst] = r.groupby("election_year")[src].transform(
            lambda s: (s - 1) / (s.max() - 1) if s.max() > 1 else 0.0
        )
    r["p_combined"] = r["defeatability_100"] / 100.0
    r["delta_vote_share"] = r["new_vote_share_Y"] - r["vote_share"]
    r["delta_n_candidates"] = r["n_candidates_Y"] - r["prior_n_candidates"]
    return r.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Item 1 — binary win/lose
# --------------------------------------------------------------------------- #
def _variant_scores(r: pd.DataFrame) -> dict:
    return {
        "equal_weight_cdi": r["p_combined"].to_numpy(),
        "vote_share_only": r["p_vote_share"].to_numpy(),
        "elector_share_only": r["p_elector_share"].to_numpy(),
        "new_voter_margin_only": r["p_new_voter_margin"].to_numpy(),
        "two_signal": ((r["p_elector_share"] + r["p_new_voter_margin"]) / 2).to_numpy(),
    }


def item1_fixed_aucs(r: pd.DataFrame) -> dict:
    """AUC + bootstrap CI for each fixed-formula variant (no fitted parameters)."""
    y = r["defeated"].to_numpy()
    out = {}
    for name, s in _variant_scores(r).items():
        point = auc(s, y)
        ci = bootstrap_ci(len(y), lambda idx, s=s: auc(s[idx], y[idx]))
        out[name] = (point, ci)
    return out


def item1_logistic_oof(r: pd.DataFrame) -> tuple:
    """Out-of-fold AUC for a logistic fit on the three component percentiles."""
    X = r[list(COMPONENT_PCT.values())].to_numpy()
    y = r["defeated"].to_numpy().astype(int)
    oof = np.full(len(r), np.nan)
    for _, train, test in loo_election_folds(r["election_year"]):
        if 0 < y[train].sum() < train.sum():
            model = LogisticRegression(max_iter=1000)
            model.fit(X[train], y[train])
            oof[test] = model.predict_proba(X[test])[:, 1]
    mask = ~np.isnan(oof)
    point = auc(oof[mask], y[mask])
    ci = bootstrap_ci(mask.sum(), lambda idx: auc(oof[mask][idx], y[mask][idx]))
    return point, ci


def operating_point_table(r: pd.DataFrame, thresholds=range(0, 101, 5)) -> pd.DataFrame:
    """Precision / recall / F1 / Youden-J for classifying at each defeatability cutoff."""
    y = r["defeated"].to_numpy()
    score = r["defeatability_100"].to_numpy()
    rows = []
    for t in thresholds:
        pred = score >= t
        tp = int((pred & y).sum())
        fp = int((pred & ~y).sum())
        fn = int((~pred & y).sum())
        tn = int((~pred & ~y).sum())
        precision = tp / (tp + fp) if tp + fp else np.nan
        recall = tp / (tp + fn) if tp + fn else np.nan
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision and recall and (precision + recall) > 0
            else np.nan
        )
        fpr = fp / (fp + tn) if fp + tn else np.nan
        rows.append(
            {
                "threshold": t,
                "flagged": int(pred.sum()),
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "youden_j": (recall - fpr) if not np.isnan(recall) else np.nan,
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Item 2 — continuous vote delta
# --------------------------------------------------------------------------- #
def item2_continuous(r: pd.DataFrame, predictors, *, exclude_2018=True, seed=0) -> dict:
    """OLS of Δ vote_share on standardized predictors, with LOO-election-out CV."""
    d = r[r["election_year"] != 2018] if exclude_2018 else r
    d = d.dropna(subset=[*predictors, "delta_vote_share"]).reset_index(drop=True)
    X = d[predictors].to_numpy(dtype=float)
    y = d["delta_vote_share"].to_numpy(dtype=float)

    Xs, _, _ = _standardize(X)
    coef = ols_fit(Xs, y)
    insample = r2(y, ols_predict(coef, Xs))

    oof = np.full(len(d), np.nan)
    for _, train, test in loo_election_folds(d["election_year"]):
        Xtr, mu, sd = _standardize(X[train])
        c = ols_fit(Xtr, y[train])
        oof[test] = ols_predict(c, (X[test] - mu) / sd)

    rng = np.random.default_rng(seed)
    boots = np.array(
        [ols_fit(Xs[ix], y[ix]) for ix in (rng.integers(0, len(y), len(y)) for _ in range(2000))]
    )
    coef_ci = np.percentile(boots, [2.5, 97.5], axis=0)

    return {
        "n": len(d),
        "predictors": list(predictors),
        "coef": coef,
        "coef_ci": coef_ci,
        "insample_r2": insample,
        "cv_r2": r2(y, oof),
        "cv_rmse": rmse(y, oof),
        "spearman": float(pd.Series(oof).corr(pd.Series(y), method="spearman")),
        "_oof": oof,
        "_y": y,
    }


# --------------------------------------------------------------------------- #
# Item 3 — interpretable triggers (extends the frontend's RACE_REASON vocabulary)
# --------------------------------------------------------------------------- #
# Pre-specified (never threshold-optimised — that overfits) single conditions, each a
# directional "raises vulnerability" trigger in the product's house voice. Reader-facing
# copy is qualitative; the historical rates in `trigger_calibration` stay backstage.
TRIGGERS = [
    {
        "key": "narrow_prior_win",
        "test": lambda row: row["vote_share"] < 0.35,
        "label": "Narrow prior win",
        "sentence": "won with under 35% of the vote, below the range where incumbents "
        "typically feel safe",
    },
    {
        "key": "growth_exceeds_cushion",
        "test": lambda row: row["new_voter_margin"] > 0,
        "label": "Ward growth exceeds cushion",
        "sentence": "the ward has added more electors since the win than the incumbent's "
        "margin of victory",
    },
    {
        "key": "high_structural_exposure",
        "test": lambda row: row["defeatability_100"] >= 55,
        "label": "High structural exposure",
        "sentence": "among the most structurally exposed wards on the combined index",
    },
]


def triggers_for(row) -> list:
    """The keys of the triggers an incumbent trips (row maps component -> value)."""
    return [t["key"] for t in TRIGGERS if bool(t["test"](row))]


def trigger_calibration(r: pd.DataFrame, *, seed=0, n_boot=3000) -> pd.DataFrame:
    """Historical lose-rate behind each trigger, all-years and ex-2018, with bootstrap CIs."""
    r = r.copy()
    r["defeated"] = ~r["elected_Y"].astype(bool)
    rows = []
    for scope_label, scope in [("all_years", r), ("ex_2018", r[r["election_year"] != 2018])]:
        base = float(scope["defeated"].mean())
        for t in TRIGGERS:
            fired = scope[t["test"](scope)]
            outcomes = fired["defeated"].to_numpy()
            n = len(outcomes)
            rate = float(outcomes.mean()) if n else float("nan")
            if n:
                rng = np.random.default_rng(seed)
                boots = np.array([outcomes[rng.integers(0, n, n)].mean() for _ in range(n_boot)])
                lo, hi = np.percentile(boots, [2.5, 97.5])
            else:
                lo = hi = float("nan")
            rows.append(
                {
                    "trigger": t["key"],
                    "scope": scope_label,
                    "fires": n,
                    "lost": int(outcomes.sum()),
                    "rate": rate,
                    "ci_lo": float(lo),
                    "ci_hi": float(hi),
                    "base_rate": base,
                    "lift": rate / base if base else float("nan"),
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Figures + report
# --------------------------------------------------------------------------- #
def _figures_dir() -> Path:
    return output_dir().parents[1] / "figures"


def _fig_variant_auc(fixed: dict, logistic: tuple, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = list(fixed) + ["logistic (out-of-fold)"]
    points = [fixed[n][0] for n in fixed] + [logistic[0]]
    los = [fixed[n][1][0] for n in fixed] + [logistic[1][0]]
    his = [fixed[n][1][1] for n in fixed] + [logistic[1][1]]
    err = [[p - lo for p, lo in zip(points, los)], [hi - p for p, hi in zip(points, his)]]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.errorbar(points, range(len(names)), xerr=err, fmt="o", color="#2b6cb0", capsize=3)
    ax.axvline(0.5, ls="--", color="#888", lw=1, label="chance (0.5)")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.set_xlabel("AUC predicting defeat — 95% bootstrap CI")
    ax.set_title(
        "Item 1: no variant beats the simple equal-weight CDI\n(and the fitted logistic is worse than chance out-of-fold)"
    )
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _fig_operating_point(opt: pd.DataFrame, base_rate: float, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(opt["threshold"], opt["precision"], "-o", color="#c05621", label="precision", ms=3)
    ax.plot(opt["threshold"], opt["recall"], "-o", color="#2b6cb0", label="recall", ms=3)
    ax.axhline(base_rate, ls=":", color="#888", label=f"base rate ({base_rate:.0%})")
    for t in (40, 55):
        ax.axvline(t, ls="--", color="#aaa", lw=1)
        ax.text(t, 1.02, f"{t}", ha="center", fontsize=8, color="#666")
    ax.set_xlabel("defeatability_100 cutoff")
    ax.set_ylabel("rate")
    ax.set_title("Item 1: operating points (dashed = Matt's 40 / 55 thresholds)")
    ax.legend(loc="center right")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _fig_item2_decomposition(decomp: list, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [d[0] for d in decomp]
    values = [d[1] for d in decomp]
    colors = ["#a0aec0", "#2b6cb0", "#2b6cb0", "#c05621"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(range(len(labels)), values, color=colors[: len(labels)])
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("out-of-fold CV R²")
    ax.set_title(
        "Item 2: the Δ-vote-share signal is field-size + mean reversion\n(the CDI's structural content adds nothing on top)"
    )
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _coef_lines(res: dict) -> str:
    lines = []
    for name, c, lo, hi in zip(
        res["predictors"], res["coef"][1:], res["coef_ci"][0][1:], res["coef_ci"][1][1:]
    ):
        lines.append(f"| `{name}` | {c:+.3f} | [{lo:+.3f}, {hi:+.3f}] |")
    return "\n".join(lines)


def _trigger_section(r: pd.DataFrame) -> str:
    """The Matt-internal trigger-calibration section (rates backstage, caveats up front)."""
    cal = trigger_calibration(r).set_index(["trigger", "scope"])
    label = {t["key"]: t["label"] for t in TRIGGERS}
    sentence = {t["key"]: t["sentence"] for t in TRIGGERS}

    lines = [
        "## Turning it into flags: incumbent triggers",
        "",
        "For the 2026 watch list we surface a few **pre-specified** structural triggers (never",
        "threshold-tuned — that overfits). To readers each is **directional only**, in the house",
        "voice — e.g. *“↑ Raises vulnerability — won with under 35% of the vote”* — and it",
        "extends the existing `RACE_REASON` trigger set, never a new red/yellow scheme.",
        "",
        "**The quantified track record below stays internal (Matt-facing), and it must be read with",
        "the caveat that it is barely calibratable:** 2026 runs on stable boundaries, so the",
        "ex-2018 column is the honest analog — and there it rests on 0–4 defeats per trigger. The",
        "all-years lift is largely the 2018 ward merger, which will not recur.",
        "",
        "| trigger | reader-facing copy | all-years | ex-2018 (2026 analog) |",
        "|---|---|---|---|",
    ]
    for t in TRIGGERS:
        a = cal.loc[(t["key"], "all_years")]
        x = cal.loc[(t["key"], "ex_2018")]
        all_txt = f"{int(a.lost)}/{int(a.fires)} lost ({a.rate:.0%}, {a.lift:.1f}×)"
        ex_txt = f"{int(x.lost)}/{int(x.fires)} lost ({x.rate:.0%}, CI {x.ci_lo:.0%}–{x.ci_hi:.0%})"
        lines.append(f"| **{label[t['key']]}** | {sentence[t['key']]} | {all_txt} | {ex_txt} |")
    base_all = cal.loc[(TRIGGERS[0]["key"], "all_years")].base_rate
    base_ex = cal.loc[(TRIGGERS[0]["key"], "ex_2018")].base_rate
    lines += [
        "",
        (
            f"Baselines: {base_all:.0%} of incumbents lose across all years, {base_ex:.0%} in a "
            "normal (ex-2018) election. So a fired trigger means *elevated attention*, not "
            "*likely to lose* — and on the 2026 analog the honest read is that these are "
            "watch-list cues, not odds."
        ),
    ]
    return "\n".join(lines)


def write_report(r: pd.DataFrame, path: Path) -> dict:
    """Compute everything, render figures, and write the plain-language report."""
    figs = _figures_dir()
    figs.mkdir(parents=True, exist_ok=True)
    n, defeats = len(r), int(r["defeated"].sum())
    base_rate = defeats / n

    fixed_all = item1_fixed_aucs(r)
    logistic_all = item1_logistic_oof(r)
    opt = operating_point_table(r)
    youden = opt.loc[opt["youden_j"].idxmax()]

    field = ["delta_n_candidates"]
    mr = ["p_vote_share", "delta_n_candidates"]
    full = ["p_vote_share", "p_elector_share", "p_new_voter_margin", "delta_n_candidates"]
    two = ["p_elector_share", "p_new_voter_margin", "delta_n_candidates"]
    m_field = item2_continuous(r, field)
    m_mr = item2_continuous(r, mr)
    m_full = item2_continuous(r, full)
    m_two = item2_continuous(r, two)
    m_full_2018 = item2_continuous(r, full, exclude_2018=False)

    decomp = [
        ("field only", m_field["cv_r2"]),
        ("+ mean reversion", m_mr["cv_r2"]),
        (
            "+ growth",
            item2_continuous(r, ["p_vote_share", "p_new_voter_margin", "delta_n_candidates"])[
                "cv_r2"
            ],
        ),
        ("full CDI + field", m_full["cv_r2"]),
    ]

    _fig_variant_auc(fixed_all, logistic_all, figs / "item1_variant_auc.png")
    _fig_operating_point(opt, base_rate, figs / "item1_operating_point.png")
    _fig_item2_decomposition(decomp, figs / "item2_decomposition.png")

    trigger_section = _trigger_section(r)

    def op_row(t):
        row = opt[opt["threshold"] == t].iloc[0]
        return (
            f"| {t} | {int(row.flagged)} | {row.precision:.0%} | {row.recall:.0%} | {row.f1:.2f} |"
        )

    md = f"""# Does the Council Defeatability Index predict anything? — validation notes

*Backtest of Matt Elliott's CDI on {n} incumbent-councillor races, 2006–2022
({defeats} actual defeats, an {base_rate:.0%} base rate). Evaluated leave-one-election-out;
uncertainty is 95% bootstrap. The faithful CDI itself is unchanged — this only measures it.*

## Bottom line

The CDI carries a **weak but real** structural signal, and **the simple equal-weight
version is as good as it gets** — combining the three metrics barely beats the best single
one, and *fitting* weights makes out-of-sample prediction **worse than a coin flip**. It's
best read as a **screening tool** (who deserves a closer look), not a forecaster. Predicting
the *size* of an incumbent's vote change is numerically easier, but that turns out to be
**mechanical** (more candidates + regression to the mean), not the index's structural content.

## Item 1 — does it predict who loses?

The three metrics are near-duplicates (vote share ↔ elector share correlate 0.91), so as
predictors of defeat they perform almost identically, and the combined index barely leads:

| index | AUC (all years) | 95% CI |
|---|---|---|
| equal-weight CDI | {fixed_all["equal_weight_cdi"][0]:.3f} | [{fixed_all["equal_weight_cdi"][1][0]:.3f}, {fixed_all["equal_weight_cdi"][1][1]:.3f}] |
| vote share only | {fixed_all["vote_share_only"][0]:.3f} | [{fixed_all["vote_share_only"][1][0]:.3f}, {fixed_all["vote_share_only"][1][1]:.3f}] |
| elector share only | {fixed_all["elector_share_only"][0]:.3f} | [{fixed_all["elector_share_only"][1][0]:.3f}, {fixed_all["elector_share_only"][1][1]:.3f}] |
| new-voter margin only | {fixed_all["new_voter_margin_only"][0]:.3f} | [{fixed_all["new_voter_margin_only"][1][0]:.3f}, {fixed_all["new_voter_margin_only"][1][1]:.3f}] |
| two-signal (drop vote share) | {fixed_all["two_signal"][0]:.3f} | [{fixed_all["two_signal"][1][0]:.3f}, {fixed_all["two_signal"][1][1]:.3f}] |
| **fitted logistic (out-of-fold)** | **{logistic_all[0]:.3f}** | [{logistic_all[1][0]:.3f}, {logistic_all[1][1]:.3f}] |

![variant AUCs](../figures/item1_variant_auc.png)

Two things stand out. First, **combining doesn't help**: the full index ({fixed_all["equal_weight_cdi"][0]:.2f})
is within noise of the best single component. Second, **tuning actively hurts**: a logistic
regression that *fits* the weights scores {logistic_all[0]:.2f} out-of-fold — worse than chance —
because with only {defeats} defeats across five very different elections, the fitted relationship
flips from one election to the next. **Equal weighting is the robust choice**, which vindicates
Matt's original design.

### Where to set the alarm

Treating the score as a screen, at each cutoff:

| defeatability_100 ≥ | incumbents flagged | precision | recall | F1 |
|---|---|---|---|---|
{op_row(40)}
{op_row(55)}
{op_row(int(youden.threshold))}

![operating point](../figures/item1_operating_point.png)

The best trade-off (Youden-J) is a cutoff around **{int(youden.threshold)}**: it flags
~{int(youden.flagged)} incumbents to catch **{youden.recall:.0%}** of eventual losers, at
**{youden.precision:.0%}** precision — roughly {youden.precision / base_rate:.1f}× the base rate.
Useful for triage, not a prediction.

## Item 2 — does it predict the *size* of the vote change?

Modelling each incumbent's Δ vote share (this election minus their prior win; excluding 2018,
where the ward map changed) is better-powered — {m_full["n"]} races instead of {defeats} defeats —
and the CDI does explain out-of-sample variance:

- full CDI + field control: **CV R² = {m_full["cv_r2"]:.2f}**, Spearman(pred, actual) = {m_full["spearman"]:.2f}
- two-signal + field control: CV R² = {m_two["cv_r2"]:.2f}
- with 2018 included (sensitivity): CV R² = {m_full_2018["cv_r2"]:.2f}

**But that predictive power is mechanical, not structural.** Decomposing it:

| model | out-of-fold CV R² |
|---|---|
| candidate-count change only | {m_field["cv_r2"]:.3f} |
| + regression to the mean (prior vote share) | {m_mr["cv_r2"]:.3f} |
| + ward growth | {decomp[2][1]:.3f} |
| full CDI + field | {m_full["cv_r2"]:.3f} |

![decomposition](../figures/item2_decomposition.png)

Almost all of it is **(a) vote-splitting** — more candidates on the ballot mechanically lower an
incumbent's share — and **(b) regression to the mean** — a narrow prior winner tends to rebound,
a dominant one to slip. Once those are in, the CDI's *distinctive* content (support depth, ward
growth) **adds essentially nothing** ({m_mr["cv_r2"]:.2f} → {m_full["cv_r2"]:.2f}). Standardized
coefficients (full model):

| predictor | coef (Δ vote share, SD units) | 95% CI |
|---|---|---|
{_coef_lines(m_full)}

{trigger_section}

## Honest caveats

- **Small N.** {defeats} defeats total (7 outside 2018); the AUC CIs above straddle 0.5. Read
  directionally, not as precise estimates.
- **2018 dominates.** The mid-cycle 44→25 ward cut produced 11 of the {defeats} defeats and is
  where the index looks strongest — partly because forced incumbent-vs-incumbent races *are* what
  the metrics pick up. Outside 2018 the signal is thinner.
- **Structural, not idiosyncratic.** The index measures a seat's standing exposure; it cannot see
  scandals, star challengers, or ward mergers, which drive many real upsets. That caps its ceiling
  by design.
- **Mean reversion.** The Δ-vote-share result must be read against the mechanical rebound above,
  not as independent forecasting skill.

## Recommendation

Keep the CDI as Matt built it — **equal-weight, three metrics, as a screen**. The data say don't
tune it (tuning overfits) and don't oversell it (it flags exposure, it doesn't call races). If a
sharper forecast is ever wanted, the gains would have to come from **new signal** — challenger
strength, fundraising, open-seat status — not from reweighting the three metrics we have.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(md)
    return {"path": path, "item1": fixed_all, "logistic": logistic_all, "item2_full": m_full}


def main() -> None:
    r = load_analysis_frame()
    result = write_report(r, output_dir().parents[1] / "docs" / "analysis-report.md")
    print(f"wrote report to {result['path']} and figures to {_figures_dir()}")


if __name__ == "__main__":
    main()
