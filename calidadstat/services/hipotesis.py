"""Pruebas de hipótesis: una muestra y comparación de grupos."""
import numpy as np
from scipy import stats

from .descriptiva import caja, normalidad

ALFA = 0.05


def una_muestra(x, mu0, normal):
    n = len(x)
    if n < 3:
        raise ValueError("Se necesitan al menos 3 datos.")
    if np.ptp(x) == 0:
        raise ValueError("Todos los datos son iguales; la prueba no es aplicable.")
    media, sd = x.mean(), x.std(ddof=1)
    h = stats.t.ppf(0.975, n - 1) * sd / np.sqrt(n)
    if normal or n >= 30:
        est, p = stats.ttest_1samp(x, mu0)
        prueba, ic = "Prueba t de una muestra", [media - h, media + h]
    else:
        d = x - mu0
        if np.all(d == 0):
            raise ValueError("Todos los datos son iguales al valor objetivo.")
        res = stats.wilcoxon(d)
        est, p = res.statistic, res.pvalue
        prueba, ic = "Wilcoxon de rangos con signo (datos no normales y n < 30)", None
    return {
        "prueba": prueba, "h0": f"μ = {mu0:g}", "h1": f"μ ≠ {mu0:g}",
        "estadistico": est, "p": p, "rechaza": bool(p < ALFA),
        "media": media, "n": n, "ic95": ic, "mu0": mu0, "normal": bool(normal),
    }


def comparar_grupos(df, col, grupo):
    if grupo not in df.columns:
        raise ValueError(f"No existe la columna «{grupo}».")
    if col == grupo:
        raise ValueError("La columna de grupo debe ser distinta de la columna de medición.")
    d = df[[col, grupo]].dropna()
    etiquetas = d[grupo].astype(str)
    cuenta = etiquetas.value_counts()
    if len(cuenta) > 10:
        raise ValueError("La columna de grupo tiene demasiados valores distintos (máximo 10).")
    validos = sorted(g for g, c in cuenta.items() if c >= 3)
    if len(validos) < 2:
        raise ValueError("Se necesitan al menos 2 grupos con 3 o más datos cada uno.")
    datos = {g: d.loc[etiquetas == g, col].to_numpy(float) for g in validos}

    info, todos_normales = [], True
    for g, v in datos.items():
        nm = normalidad(v)
        ok = bool(nm and nm["normal"]) or len(v) >= 30
        todos_normales = todos_normales and ok
        info.append({
            "nombre": g, "n": len(v), "media": v.mean(), "desviacion": v.std(ddof=1),
            "mediana": np.median(v), "caja": caja(v), "normal_p": nm["p"] if nm else None,
        })

    arreglos = list(datos.values())
    try:
        lev_p = float(stats.levene(*arreglos, center="median").pvalue)
    except Exception:
        lev_p = float("nan")
    homogeneas = bool(np.isfinite(lev_p) and lev_p > ALFA)
    k = len(arreglos)

    if k == 2:
        if todos_normales:
            prueba = "Prueba t de Welch (2 muestras independientes)"
            r = stats.ttest_ind(arreglos[0], arreglos[1], equal_var=False)
            just = "Ambos grupos son aproximadamente normales (o tienen n ≥ 30); Welch no exige varianzas iguales."
        else:
            prueba = "U de Mann-Whitney"
            r = stats.mannwhitneyu(arreglos[0], arreglos[1], alternative="two-sided")
            just = "Algún grupo no es normal y tiene pocos datos, por eso se usa una prueba no paramétrica."
    else:
        if todos_normales and homogeneas:
            prueba = "ANOVA de un factor"
            r = stats.f_oneway(*arreglos)
            just = "Los grupos son aproximadamente normales y con varianzas similares (Levene)."
        else:
            prueba = "Kruskal-Wallis"
            r = stats.kruskal(*arreglos)
            just = "No se cumplen normalidad u homogeneidad de varianzas; se usa una prueba no paramétrica."

    return {
        "columna": col, "grupo": grupo, "grupos": info, "levene_p": lev_p,
        "prueba": prueba, "estadistico": r.statistic, "p": r.pvalue,
        "rechaza": bool(r.pvalue < ALFA), "justificacion": just,
        "descartados": int(len(cuenta) - len(validos)),
        "h0": "Todos los grupos tienen la misma media (o distribución).",
    }