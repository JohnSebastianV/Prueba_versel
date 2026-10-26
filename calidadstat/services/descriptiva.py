"""Estadística descriptiva, normalidad y datos base para los gráficos."""
import numpy as np
from scipy import stats

from .util import muestrear


def histograma(x):
    bordes = np.histogram_bin_edges(x, bins="auto")
    if len(bordes) - 1 > 40:
        bordes = np.histogram_bin_edges(x, bins=40)
    conteos, bordes = np.histogram(x, bins=bordes)
    return {"conteos": conteos, "bordes": bordes}


def caja(x):
    q1, med, q3 = np.percentile(x, [25, 50, 75])
    iqr = q3 - q1
    inf, sup = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    dentro = x[(x >= inf) & (x <= sup)]
    fuera = x[(x < inf) | (x > sup)]
    return {
        "q1": q1, "mediana": med, "q3": q3,
        "bigote_inf": dentro.min(), "bigote_sup": dentro.max(),
        "media": x.mean(), "atipicos": fuera[:200], "n_atipicos": len(fuera),
    }


def normalidad(x):
    n = len(x)
    if n < 3 or np.ptp(x) == 0:
        return None
    m = x if n <= 5000 else np.random.default_rng(1).choice(x, 5000, replace=False)
    w, p = stats.shapiro(m)
    return {"prueba": "Shapiro-Wilk", "estadistico": w, "p": p, "normal": bool(p > 0.05), "n_usado": len(m)}


def qq(x):
    if len(x) < 3 or np.ptp(x) == 0:
        return None
    (osm, osr), (pendiente, intercepto, _) = stats.probplot(x, dist="norm")
    return {
        "teorico": muestrear(osm, 1500), "muestra": muestrear(osr, 1500),
        "pendiente": pendiente, "intercepto": intercepto,
    }


def descriptiva(s, columna):
    x = s.to_numpy(dtype=float)
    n = len(x)
    if n < 3:
        raise ValueError("Se necesitan al menos 3 datos válidos para el análisis descriptivo.")
    media, sd = x.mean(), x.std(ddof=1)
    q1, q3 = np.percentile(x, [25, 75])
    vc = s.round(6).value_counts()
    moda = float(vc[vc == vc.iloc[0]].index.min()) if vc.iloc[0] > 1 else None
    h = stats.t.ppf(0.975, n - 1) * sd / np.sqrt(n)
    cj = caja(x)
    resumen = {
        "n": n, "media": media, "mediana": np.median(x), "moda": moda,
        "desviacion": sd, "varianza": sd ** 2, "minimo": x.min(), "maximo": x.max(),
        "rango": np.ptp(x), "q1": q1, "q3": q3, "iqr": q3 - q1,
        "cv": (sd / abs(media) * 100) if media != 0 else None,
        "asimetria": stats.skew(x, bias=False), "curtosis": stats.kurtosis(x, bias=False),
        "error_estandar": sd / np.sqrt(n), "ic95": [media - h, media + h],
        "n_atipicos": cj["n_atipicos"],
    }
    return {
        "columna": columna, "resumen": resumen, "histograma": histograma(x),
        "caja": cj, "normalidad": normalidad(x), "qq": qq(x),
    }