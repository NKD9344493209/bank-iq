"""Run every Bank IQ experiment end-to-end:  python -m bankiq.experiments.run_all

Order matters only for speed (classification trains the featurizer that ensembles reuse).
Outputs: results/*.json, results/figures/*.png, models/*.joblib
"""
from __future__ import annotations

import sys
import time

from . import classification, clustering, eda, ensembles, pca_lwr, regression

STEPS = [("eda", eda.run), ("classification", classification.run), ("ensembles", ensembles.run),
         ("regression", regression.run), ("clustering", clustering.run), ("pca_lwr", pca_lwr.run)]


def main(only: list[str] | None = None):
    t0 = time.time()
    for name, fn in STEPS:
        if only and name not in only:
            continue
        print(f"\n=== {name} ===")
        t = time.time(); fn(); print(f"=== {name} done in {time.time() - t:.0f}s")
    print(f"\nall done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
