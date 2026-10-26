"""Simulación de dos equipos: generación de datos, bondad de ajuste y comparación de medias."""
import numpy as np
import pandas as pd
from scipy import stats

from .descriptiva import descriptiva
from .interpretacion import f
from .marcas import ng, tp

ALFA = 0.05


def _positivo(p, clave, etiqueta):
    try:
        v = float(p[clave])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"Completa el parámetro «{etiqueta}» con un número.") from None
    if not np.isfinite(v):
        raise ValueError(f"El parámetro «{etiqueta}» no es válido.")
    return v


def generar(spec, n, rng):
    """Devuelve (datos, descripción, desviación teórica)."""
    dist, p = spec.get("dist"), spec.get("params") or {}
    if dist == "normal":
        mu, sigma = _positivo(p, "mu", "media μ"), _positivo(p, "sigma", "desviación σ")
        if sigma <= 0:
            raise ValueError("σ debe ser mayor que 0.")
        return rng.normal(mu, sigma, n), f"Normal(μ = {ng(mu)}, σ = {ng(sigma)})", sigma
    if dist == "gamma":
        a, b = _positivo(p, "alpha", "forma α"), _positivo(p, "beta", "escala β")
        if a <= 0 or b <= 0:
            raise ValueError("α y β deben ser mayores que 0.")
        # β se usa como parámetro de ESCALA: media = α·β, varianza = α·β²
        return rng.gamma(a, b, n), f"Gamma(α = {ng(a)}, β = {ng(b)})", np.sqrt(a) * b
    raise ValueError("Distribución no soportada (usa normal o gamma).")


def _chi2(x, dist, k):
    n = len(x)
    cortes = dist.ppf(np.linspace(0, 1, k + 1))[1:-1]
    obs = np.bincount(np.searchsorted(cortes, x, side="right"), minlength=k)
    esp = n / k
    est = float(((obs - esp) ** 2 / esp).sum())
    gl = k - 1 - 2  # dos parámetros estimados
    return est, gl, float(stats.chi2.sf(est, gl))


def bondad_ajuste(x):
    n = len(x)
    mu, sd = float(x.mean()), float(x.std(ddof=1))
    k = max(5, int(round(1 + 3.322 * np.log10(n))))
    k = min(k, n // 5)
    pruebas, gam = [], None
    sw = stats.shapiro(x)
    pruebas.append({"prueba": "Shapiro-Wilk", "modelo": "Normal", "estadistico": float(sw.statistic), "gl": None, "p": float(sw.pvalue)})
    ks = stats.kstest(x, "norm", args=(mu, sd))
    pruebas.append({"prueba": "Kolmogorov-Smirnov", "modelo": "Normal", "estadistico": float(ks.statistic), "gl": None, "p": float(ks.pvalue)})
    if k >= 4:
        e, gl, p = _chi2(x, stats.norm(mu, sd), k)
        pruebas.append({"prueba": f"Chi-cuadrado ({k} clases)", "modelo": "Normal", "estadistico": e, "gl": gl, "p": p})
    if np.all(x > 0):
        a, _, esc = stats.gamma.fit(x, floc=0)
        gam = (float(a), float(esc))
        ks = stats.kstest(x, "gamma", args=(a, 0, esc))
        pruebas.append({"prueba": "Kolmogorov-Smirnov", "modelo": "Gamma", "estadistico": float(ks.statistic), "gl": None, "p": float(ks.pvalue)})
        if k >= 4:
            e, gl, p = _chi2(x, stats.gamma(a, 0, esc), k)
            pruebas.append({"prueba": f"Chi-cuadrado ({k} clases)", "modelo": "Gamma", "estadistico": e, "gl": gl, "p": p})
    for r in pruebas:
        r["rechaza"] = bool(r["p"] < ALFA)
    return pruebas, (mu, sd), gam


def _veredicto(pruebas, modelo):
    ps = [r for r in pruebas if r["modelo"] == modelo]
    if not ps:
        return None
    return all(not r["rechaza"] for r in ps)


def analizar_grupo(x, nombre, desc):
    d = descriptiva(pd.Series(x), nombre)
    d.pop("qq", None)
    pruebas, (mu, sd), gam = bondad_ajuste(x)
    h = d["histograma"]
    ancho = float(h["bordes"][1] - h["bordes"][0])
    xs = np.linspace(h["bordes"][0], h["bordes"][-1], 120)
    curvas = {"x": xs, "normal": len(x) * ancho * stats.norm.pdf(xs, mu, sd)}
    if gam:
        curvas["gamma"] = len(x) * ancho * stats.gamma.pdf(xs, gam[0], 0, gam[1])
    return {"nombre": nombre, "descripcion": desc, "datos": np.round(x, 4), "descriptiva": d["resumen"],
            "histograma": h, "caja": d["caja"], "pruebas": pruebas, "curvas": curvas,
            "ajuste_normal": {"mu": mu, "sigma": sd}, "ajuste_gamma": ({"alpha": gam[0], "beta": gam[1]} if gam else None),
            "ok_normal": _veredicto(pruebas, "Normal"), "ok_gamma": _veredicto(pruebas, "Gamma")}


def comparar_medias(a, b, sa_teo, sb_teo, conf=0.95):
    na, nb = len(a), len(b)
    dif = float(a.mean() - b.mean())
    va, vb = a.var(ddof=1), b.var(ddof=1)
    alfa = 1 - conf
    filas = []

    def fila(metodo, est, gl, p, h):
        filas.append({"metodo": metodo, "estadistico": float(est), "gl": None if gl is None else float(gl), "p": float(p),
                      "ic": [dif - h, dif + h], "rechaza": bool(p < alfa)})

    se = np.sqrt(va / na + vb / nb)
    gl = se ** 4 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    fila("t de Student · Welch (varianzas distintas)", dif / se, gl, 2 * stats.t.sf(abs(dif / se), gl), stats.t.ppf(1 - alfa / 2, gl) * se)
    glp = na + nb - 2
    sp2 = ((na - 1) * va + (nb - 1) * vb) / glp
    sep = np.sqrt(sp2 * (1 / na + 1 / nb))
    fila("t de Student · varianzas iguales (agrupada)", dif / sep, glp, 2 * stats.t.sf(abs(dif / sep), glp), stats.t.ppf(1 - alfa / 2, glp) * sep)
    fila("Normal (Z) · desviaciones muestrales", dif / se, None, 2 * stats.norm.sf(abs(dif / se)), stats.norm.ppf(1 - alfa / 2) * se)
    se0 = np.sqrt(sa_teo ** 2 / na + sb_teo ** 2 / nb)
    fila("Normal (Z) · σ teóricas conocidas", dif / se0, None, 2 * stats.norm.sf(abs(dif / se0)), stats.norm.ppf(1 - alfa / 2) * se0)

    mw = stats.mannwhitneyu(a, b, alternative="two-sided")
    U = float(mw.statistic)
    hl = float(np.median((a[:, None] - b[None, :]).ravel()))
    lev = float(stats.levene(a, b, center="median").pvalue)
    F = va / vb
    pf = 2 * min(stats.f.cdf(F, na - 1, nb - 1), stats.f.sf(F, na - 1, nb - 1))
    return {"dif": dif, "medias": filas,
            "mann_whitney": {"U": U, "p": float(mw.pvalue), "prob_a_mayor": U / (na * nb), "hodges_lehmann": hl,
                             "mediana_a": float(np.median(a)), "mediana_b": float(np.median(b)), "rechaza": bool(mw.pvalue < ALFA)},
            "varianzas": {"f": float(F), "p_f": float(pf), "levene_p": lev}}


def interpretar(nombre, ga, gb, comp):
    h = []
    for g in (ga, gb):
        partes = []
        if g["ok_normal"] is not None:
            partes.append("no se rechaza la normalidad en ninguna prueba" if g["ok_normal"] else "alguna prueba rechaza la normalidad")
        if g["ok_gamma"] is not None:
            partes.append("no se rechaza el ajuste Gamma" if g["ok_gamma"] else "alguna prueba rechaza el ajuste Gamma")
        asim = g["descriptiva"]["asimetria"]
        h.append(f"Equipo {g['nombre']} ({g['descripcion']}): " + "; ".join(partes)
                 + f". Asimetría = {f(asim)}" + (" (sesgo a la derecha marcado)." if asim > 1 else "."))
    me = comp["medias"]
    decisiones = {r["rechaza"] for r in me}
    ps = ", ".join(f"{tp(r['p'])}" for r in me)
    dif = comp["dif"]
    if len(decisiones) == 1:
        rech = decisiones.pop()
        h.append(f"Las cuatro versiones de la prueba de medias (t Welch, t agrupada, Z muestral y Z con σ teóricas; {ps}) llegan a la misma conclusión: "
                 + (f"se rechaza H₀ (μA = μB); la diferencia observada fue {f(dif, 2)}." if rech else
                    f"no se rechaza H₀ (μA = μB) al 5 %; la diferencia observada de {f(dif, 2)} no es estadísticamente significativa."))
    else:
        h.append(f"Las pruebas de medias no coinciden ({ps}): la decisión es sensible al método, lo que sugiere un caso límite. Reporta todas y justifica cuál se ajusta mejor a los supuestos.")
    mw = comp["mann_whitney"]
    h.append(f"Mann-Whitney: U = {f(mw['U'], 1)}, {tp(mw['p'])} → " + ("se rechaza" if mw["rechaza"] else "no se rechaza")
             + f" que las distribuciones sean iguales. Probabilidad de que un dato de A supere a uno de B = {f(mw['prob_a_mayor'] * 100, 1)} % (0,5 = sin diferencia).")
    medias_rech = any(r["rechaza"] for r in me)
    if medias_rech != mw["rechaza"]:
        h.append("Mann-Whitney y las pruebas de medias difieren: comparan cosas distintas (medias frente a posición/forma de toda la distribución) "
                 "y reaccionan distinto ante asimetría, valores extremos y diferencias de dispersión.")
    lev = comp["varianzas"]["levene_p"]
    h.append(f"Homogeneidad de varianzas (Levene): {tp(lev)} → " + ("las varianzas difieren de forma significativa; la versión Welch/Z muestral es más apropiada que la agrupada." if lev < ALFA else "no hay evidencia de que las varianzas difieran."))
    if any(g["ok_normal"] is False for g in (ga, gb)):
        h.append("Como hay evidencia contra la normalidad en algún grupo, las pruebas t/Z se apoyan en el tamaño de muestra (Teorema Central del Límite); Mann-Whitney no exige normalidad.")
    return h


def simular(escenarios, n, semilla):
    if not 10 <= n <= 2000:
        raise ValueError("El tamaño de muestra debe estar entre 10 y 2000.")
    if not escenarios:
        raise ValueError("Define al menos un escenario.")
    if semilla is None:
        semilla = int(np.random.SeedSequence().entropy % 2_000_000_000)
    rng = np.random.default_rng(semilla)
    salida = []
    for i, e in enumerate(escenarios, 1):
        nombre = e.get("nombre", f"Escenario {i}")
        try:
            xa, da, sa = generar(e["a"], n, rng)
            xb, db, sb = generar(e["b"], n, rng)
        except ValueError as err:
            raise ValueError(f"{nombre}: {err}") from err
        ga, gb = analizar_grupo(xa, "A", da), analizar_grupo(xb, "B", db)
        comp = comparar_medias(xa, xb, sa, sb)
        salida.append({"nombre": nombre, "A": ga, "B": gb, "comparacion": comp,
                       "interpretacion": interpretar(nombre, ga, gb, comp)})
    return {"semilla": semilla, "n": n, "escenarios": salida}