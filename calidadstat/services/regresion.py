"""Correlación y regresión lineal simple."""
import numpy as np
from scipy import stats

from .descriptiva import normalidad
from .util import muestrear


def correlaciones(df, cols):
    cols = list(cols)[:12]
    if len(cols) < 2:
        raise ValueError("Se necesitan al menos dos columnas numéricas.")
    m = df[cols].corr(method="pearson")
    pares = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = m.iloc[i, j]
            if np.isfinite(r):
                pares.append({"a": cols[i], "b": cols[j], "r": float(r)})
    pares.sort(key=lambda p: -abs(p["r"]))
    return {"columnas": cols, "matriz": m.to_numpy(), "principales": pares[:5]}


def regresion_simple(df, x, y):
    if not x or not y:
        raise ValueError("Elige las columnas X e Y.")
    if x == y:
        raise ValueError("Elige dos columnas distintas para X e Y.")
    for c in (x, y):
        if c not in df.columns:
            raise ValueError(f"No existe la columna «{c}».")
    d = df[[x, y]].dropna()
    n = len(d)
    if n < 3:
        raise ValueError("Se necesitan al menos 3 pares de datos.")
    xv, yv = d[x].to_numpy(float), d[y].to_numpy(float)
    if np.ptp(xv) == 0 or np.ptp(yv) == 0:
        raise ValueError("Una de las variables es constante: no se puede ajustar la regresión.")
    res = stats.linregress(xv, yv)
    b, a = res.slope, res.intercept
    ajust = a + b * xv
    resid = yv - ajust
    t = stats.t.ppf(0.975, n - 2)
    rho, p_s = stats.spearmanr(xv, yv)
    xs = np.linspace(xv.min(), xv.max(), 50)
    idx = np.linspace(0, n - 1, min(n, 2000)).astype(int)
    return {
        "x": x, "y": y, "n": n, "pendiente": b, "intercepto": a, "r": res.rvalue,
        "r2": res.rvalue ** 2, "p": res.pvalue, "ic95_pendiente": [b - t * res.stderr, b + t * res.stderr],
        "error_residual": float(np.sqrt(np.sum(resid ** 2) / (n - 2))),
        "spearman": rho, "p_spearman": p_s,
        "puntos": {"x": xv[idx], "y": yv[idx]}, "recta": {"x": xs, "y": a + b * xs},
        "residuos": {"ajustados": muestrear(ajust, 2000), "valores": muestrear(resid, 2000)},
        "normalidad_residuos": normalidad(resid),
    }