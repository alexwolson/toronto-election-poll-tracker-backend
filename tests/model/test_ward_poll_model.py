import numpy as np
import pytest

from backend.model.ward_poll_model import fit


def test_discrepancy_learning_and_joint_predictions_are_not_binomial_precision():
    p = np.array([0.55, 0.30, 0.15])
    narrow = [(str(i), p, np.array([0.54, 0.31, 0.15])) for i in range(6)]
    wide = [(str(i), p, np.array([0.30, 0.40, 0.30])) for i in range(6)]
    small, large = fit(narrow).predict(p), fit(wide).predict(p)
    assert np.allclose(large.sum(axis=1), 1)
    assert np.all((large >= 0) & (large <= 1))
    assert np.quantile(large[:, 0], 0.9) - np.quantile(large[:, 0], 0.1) > 2 * (
        np.quantile(small[:, 0], 0.9) - np.quantile(small[:, 0], 0.1)
    )
    # This is a predictive discrepancy distribution, not correction toward supplied outcomes.
    assert np.mean(large[:, 0]) == pytest.approx(p[0], abs=0.005)
    assert np.array_equal(large, fit(wide).predict(p))


def test_missing_candidates_are_not_created_and_zero_readings_fail_closed():
    p = np.array([0.6, 0.4])
    fitted = fit([(str(i), p, np.array([0.5, 0.5])) for i in range(6)])
    assert fitted.predict(p).shape[1] == 2
    with pytest.raises(ValueError, match="positive named shares"):
        fitted.predict(np.array([0.6, 0.4, 0]))
