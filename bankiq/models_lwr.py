"""Locally Weighted (linear) Regression – implemented from scratch with NumPy.

For a query point x0, fit a weighted least-squares line using weights
    w_i = exp( -(x_i - x0)^2 / (2 tau^2) )          (Gaussian kernel, bandwidth tau)
and predict  y0 = [1, x0] . theta,  theta = (X^T W X)^-1 X^T W y.

Non-parametric: no global parameters are learned; every prediction re-fits locally.
Bandwidth tau controls bias/variance: small tau -> wiggly (low bias, high variance),
large tau -> approaches ordinary linear regression.
"""
from __future__ import annotations

import numpy as np


class LocallyWeightedRegression:
    def __init__(self, tau: float = 5.0, ridge: float = 1e-6):
        self.tau = tau
        self.ridge = ridge
        self.x_: np.ndarray | None = None
        self.y_: np.ndarray | None = None

    def fit(self, x: np.ndarray, y: np.ndarray) -> "LocallyWeightedRegression":
        self.x_ = np.asarray(x, dtype=float).ravel()
        self.y_ = np.asarray(y, dtype=float).ravel()
        return self

    def _predict_one(self, x0: float) -> float:
        w = np.exp(-((self.x_ - x0) ** 2) / (2 * self.tau ** 2))
        X = np.column_stack([np.ones_like(self.x_), self.x_])
        XtW = X.T * w                                   # (2, n)
        A = XtW @ X + self.ridge * np.eye(2)
        theta = np.linalg.solve(A, XtW @ self.y_)
        return float(theta[0] + theta[1] * x0)

    def predict(self, x: np.ndarray) -> np.ndarray:
        return np.array([self._predict_one(float(v)) for v in np.asarray(x, dtype=float).ravel()])


def rmse(a, b) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(np.sqrt(np.mean((a - b) ** 2)))
