"""Analysis primitives: AUC, LOO-election folds, bootstrap CI, OLS."""

import numpy as np
import pandas as pd

from defeatability_index.analysis import (
    auc,
    bootstrap_ci,
    loo_election_folds,
    ols_fit,
    ols_predict,
    triggers_for,
)


def test_auc_perfect_reversed_and_ties():
    assert auc([0.1, 0.2, 0.3, 0.4], [0, 0, 1, 1]) == 1.0
    assert auc([0.4, 0.3, 0.2, 0.1], [0, 0, 1, 1]) == 0.0
    assert auc([1, 1, 1, 1], [0, 0, 1, 1]) == 0.5  # all tied -> chance


def test_auc_matches_sklearn():
    from sklearn.metrics import roc_auc_score

    rng = np.random.default_rng(0)
    scores = rng.random(60)
    labels = (rng.random(60) > 0.6).astype(int)
    assert abs(auc(scores, labels) - roc_auc_score(labels, scores)) < 1e-9


def test_loo_election_folds_holds_out_each_year():
    years = pd.Series([2006, 2006, 2010, 2014])
    folds = list(loo_election_folds(years))

    assert [held for held, _, _ in folds] == [2006, 2010, 2014]
    _, train, test = folds[0]
    assert list(test) == [True, True, False, False]
    assert list(train) == [False, False, True, True]


def test_bootstrap_ci_reproducible_and_brackets_estimate():
    vals = np.arange(100.0)

    def mean_of(idx):
        return vals[idx].mean()

    ci1 = bootstrap_ci(len(vals), mean_of, seed=42, n_boot=500)
    ci2 = bootstrap_ci(len(vals), mean_of, seed=42, n_boot=500)

    assert ci1 == ci2  # deterministic under a fixed seed
    assert ci1[0] < vals.mean() < ci1[1]


def test_ols_recovers_known_coefficients():
    rng = np.random.default_rng(0)
    X = rng.random((200, 2))
    y = 2.0 + 3.0 * X[:, 0] - 1.0 * X[:, 1]

    coef = ols_fit(X, y)

    assert np.allclose(coef, [2.0, 3.0, -1.0], atol=1e-8)  # [intercept, b1, b2]
    assert np.allclose(ols_predict(coef, X), y, atol=1e-8)


def test_triggers_for_fires_all_and_none():
    hot = {"vote_share": 0.30, "new_voter_margin": 5000, "defeatability_100": 70}
    assert set(triggers_for(hot)) == {
        "narrow_prior_win",
        "growth_exceeds_cushion",
        "high_structural_exposure",
    }
    cold = {"vote_share": 0.60, "new_voter_margin": -5000, "defeatability_100": 20}
    assert triggers_for(cold) == []


def test_triggers_for_boundaries_are_strict():
    # 0.35 is not < 0.35; margin 0 is not > 0; 55 does satisfy >= 55.
    edge = {"vote_share": 0.35, "new_voter_margin": 0, "defeatability_100": 55}
    assert triggers_for(edge) == ["high_structural_exposure"]
