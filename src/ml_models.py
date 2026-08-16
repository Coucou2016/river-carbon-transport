"""ML model wrappers for S_sgs closure."""

from __future__ import annotations

import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


class NonNegativeMLP:
    """MLP with ReLU-style non-negative predictions for S_sgs."""

    def __init__(self, hidden_layers, max_iter, learning_rate_init, random_state):
        self.pipe = Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "mlp",
                    MLPRegressor(
                        hidden_layer_sizes=tuple(hidden_layers),
                        max_iter=max_iter,
                        learning_rate_init=learning_rate_init,
                        random_state=random_state,
                        early_stopping=True,
                    ),
                ),
            ]
        )

    def fit(self, X, y):
        self.pipe.fit(X, y)
        return self

    def predict(self, X):
        return np.maximum(self.pipe.predict(X), 0.0)
