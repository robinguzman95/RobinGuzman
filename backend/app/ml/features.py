"""Variables de entrada del modelo. Para predecir el sorteo t solo se usan los sorteos < t.

Unidad: la balota (en ColorLoto, el par número-color) o la balota extra (superbalota).
Para cada sorteo t y cada balota b:
- frec_10, frec_25, frec_50, frec_100: fracción de los últimos w sorteos en que salió b;
- frec_total: fracción de todos los sorteos anteriores;
- hueco: log(1 + sorteos desde la última vez que salió), tope 200;
- salio_antes: 1 si salió en el sorteo t − 1.
"""

import numpy as np

from app.analysis.frequency import all_balls
from app.games import Game
from app.ingest.records import DrawRecord

WINDOWS = (10, 25, 50, 100)
FEATURE_NAMES = [f"frec_{w}" for w in WINDOWS] + ["frec_total", "hueco", "salio_antes"]


def presence(records: list[DrawRecord], game: type[Game], unit: str = "main") -> np.ndarray:
    """Matriz T × B (bool): P[t, b] = la balota b salió en el sorteo t (orden por número)."""
    recs = sorted(records, key=lambda r: r.draw_number)
    if unit == "extra":
        if not game.extra_max:
            raise ValueError(f"{game.name} no tiene balota extra")
        p = np.zeros((len(recs), game.extra_max), dtype=bool)
        for t, r in enumerate(recs):
            p[t, r.extra - 1] = True
        return p
    balls = all_balls(game)
    idx = {b: i for i, b in enumerate(balls)}
    p = np.zeros((len(recs), len(balls)), dtype=bool)
    for t, r in enumerate(recs):
        for b in r.ticket.balls():
            p[t, idx[b]] = True
    return p


def feature_tensor(p: np.ndarray) -> np.ndarray:
    """Tensor (T + 1) × B × F: fila t = variables para predecir el sorteo t usando p[:t].
    La fila T sirve para predecir el próximo sorteo (aún no jugado)."""
    t_total, b = p.shape
    cs = np.vstack([np.zeros((1, b)), np.cumsum(p, axis=0)])  # cs[t] = salidas en p[:t]
    rows = np.arange(t_total + 1)
    # Valor sin historia: la probabilidad teórica K/B (regla del juego), NO el promedio de p,
    # que incluiría sorteos futuros (fuga de información detectada por las pruebas).
    base = float(p[0].sum()) / b if t_total else 0.0
    feats = []
    for w in WINDOWS:
        lo = np.maximum(rows - w, 0)
        n = np.maximum(rows - lo, 1)
        f = (cs[rows] - cs[lo]) / n[:, None]
        f[0] = base
        feats.append(f)
    total = cs[rows] / np.maximum(rows, 1)[:, None]
    total[0] = base
    feats.append(total)
    gap = np.zeros((t_total + 1, b))
    last = np.full(b, -1)
    for t in range(t_total + 1):
        gap[t] = np.where(last >= 0, t - 1 - last, t)
        if t < t_total:
            last = np.where(p[t], t, last)
    feats.append(np.log1p(np.minimum(gap, 200)))
    prev = np.vstack([np.zeros((1, b)), p.astype(float)])
    feats.append(prev)
    return np.stack(feats, axis=2)


def dataset(feats: np.ndarray, p: np.ndarray, ts: range) -> tuple[np.ndarray, np.ndarray]:
    """Filas (sorteo, balota) para los sorteos `ts`: X (len·B × F), y (len·B)."""
    x = feats[list(ts)].reshape(-1, feats.shape[2])
    y = p[list(ts)].reshape(-1).astype(int)
    return x, y
