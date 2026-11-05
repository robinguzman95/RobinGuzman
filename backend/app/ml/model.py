"""Modelos, evaluación walk-forward y predicción del próximo sorteo."""

from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.backtest.montecarlo import baseline
from app.games import Game
from app.ingest.records import DrawRecord
from app.ml.features import FEATURE_NAMES, dataset, feature_tensor, presence

MODELS = {
    "gb": "Gradient boosting (tipo LightGBM)",
    "logit": "Regresión logística",
}
MIN_TRAIN_FROM = 20  # los primeros sorteos no tienen historia suficiente para las variables
RETRAIN_EVERY = 25
EPS = 1e-6


def make_model(kind: str):
    if kind == "gb":
        return HistGradientBoostingClassifier(
            learning_rate=0.05, max_iter=150, max_leaf_nodes=15, min_samples_leaf=40,
            l2_regularization=1.0, random_state=0,
        )
    if kind == "logit":
        return make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=2000))
    raise ValueError(f"modelo desconocido {kind!r}")


def _fit(kind: str, feats: np.ndarray, p: np.ndarray, upto: int):
    x, y = dataset(feats, p, range(MIN_TRAIN_FROM, upto))
    model = make_model(kind)
    model.fit(x, y)
    return model


def _proba(model, feats_t: np.ndarray) -> np.ndarray:
    return np.clip(model.predict_proba(feats_t)[:, 1], EPS, 1 - EPS)


def _logloss(prob: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Log-loss por sorteo (promedio sobre balotas)."""
    return -(y * np.log(prob) + (1 - y) * np.log(1 - prob)).mean(axis=1)


@dataclass
class UnitEval:
    unit: str  # "main" o "extra"
    kind: str
    n_test: int
    k: int  # balotas que salen por sorteo
    b: int  # balotas posibles
    logloss_model: float
    logloss_base: float
    brier_model: float
    brier_base: float
    skill: float  # 1 − LL_modelo / LL_base: > 0 = mejor que "todas iguales"
    delta_ci: tuple[float, float]  # IC 95 % (bootstrap) de LL_base − LL_modelo por sorteo
    avg_hits: float  # aciertos de sus K favoritas por sorteo
    base_mean: float
    base_p5: float
    base_p95: float
    p_value: float
    calibration: list[dict] = field(default_factory=list)  # deciles: prob. media vs frecuencia real


def walk_forward(records: list[DrawRecord], game: type[Game], kind: str = "gb", unit: str = "main",
                 start: int | None = None, retrain_every: int = RETRAIN_EVERY, seed: int = 0) -> UnitEval:
    """Reentrena cada `retrain_every` sorteos con TODO lo anterior y predice el bloque siguiente."""
    p = presence(records, game, unit)
    t_total, b = p.shape
    k = int(p[0].sum())
    start = start if start is not None else max(100, t_total // 2)
    if start >= t_total:
        raise ValueError("no hay sorteos para evaluar")
    feats = feature_tensor(p)
    probs = np.zeros((t_total - start, b))
    for block in range(start, t_total, retrain_every):
        model = _fit(kind, feats, p, block)
        end = min(block + retrain_every, t_total)
        for t in range(block, end):
            probs[t - start] = _proba(model, feats[t])
    y = p[start:].astype(float)
    base = np.full_like(probs, k / b)
    ll_m, ll_b = _logloss(probs, y), _logloss(base, y)
    br_m = ((probs - y) ** 2).mean()
    br_b = ((base - y) ** 2).mean()

    rng = np.random.default_rng(seed)
    diff = ll_b - ll_m
    boots = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(2000)]
    ci = (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5)))

    top = np.argsort(-probs, axis=1)[:, :k]
    hits = np.take_along_axis(y, top, axis=1).sum(axis=1)
    if unit == "main":
        base_dist = baseline(game, len(hits), seed=seed)
        mean, p5, p95, pv = base_dist.mean, base_dist.p5, base_dist.p95, base_dist.p_value(float(hits.mean()))
    else:  # una sola balota extra: aciertos ~ Binomial(n, 1/b)
        sims = rng.binomial(len(hits), 1 / b, 10_000) / len(hits)
        mean, p5, p95 = float(sims.mean()), float(np.percentile(sims, 5)), float(np.percentile(sims, 95))
        pv = float((1 + (sims >= hits.mean() - 1e-12).sum()) / (len(sims) + 1))

    order = np.argsort(probs.reshape(-1))
    flat_p, flat_y = probs.reshape(-1)[order], y.reshape(-1)[order]
    calib = [{"predicted": float(cp.mean()), "observed": float(cy.mean()), "n": int(len(cp))}
             for cp, cy in zip(np.array_split(flat_p, 10), np.array_split(flat_y, 10))]
    return UnitEval(unit, kind, len(hits), k, b, float(ll_m.mean()), float(ll_b.mean()), float(br_m), float(br_b),
                    float(1 - ll_m.mean() / ll_b.mean()), ci, float(hits.mean()), mean, p5, p95, pv, calib)


@dataclass(frozen=True)
class NextDraw:
    unit: str
    kind: str
    trained_on: int
    probabilities: list[float]  # por balota, en el orden de all_balls (o 1..extra_max)
    base: float
    importances: dict[str, float]


def predict_next(records: list[DrawRecord], game: type[Game], kind: str = "gb", unit: str = "main") -> NextDraw:
    p = presence(records, game, unit)
    feats = feature_tensor(p)
    model = _fit(kind, feats, p, len(p))
    prob = _proba(model, feats[len(p)])
    imp: dict[str, float] = {}
    if kind == "logit":
        coef = model[-1].coef_[0]
        imp = {n: float(abs(c)) for n, c in zip(FEATURE_NAMES, coef)}
    return NextDraw(unit, kind, len(p) - MIN_TRAIN_FROM, [float(x) for x in prob], float(p[0].sum() / p.shape[1]), imp)
