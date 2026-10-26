"""Calculadora de distribuciones y distribuciones muestrales."""
import numpy as np
from scipy import stats

# id: (nombre, discreta, [(parámetro, etiqueta, valor por defecto)])
DEFS = {
    "normal": ("Normal", False, [("mu", "Media (μ)", 0), ("sigma", "Desviación estándar (σ)", 1)]),
    "uniforme": ("Uniforme continua", False, [("a", "Mínimo (a)", 0), ("b", "Máximo (b)", 1)]),
    "exponencial": ("Exponencial", False, [("lam", "Tasa (λ)", 1)]),
    "t": ("t de Student", False, [("df", "Grados de libertad", 10)]),
    "chi2": ("Chi-cuadrado", False, [("df", "Grados de libertad", 5)]),
    "binomial": ("Binomial", True, [("n", "Ensayos (n)", 10), ("p", "Prob. de éxito (p)", 0.5)]),
    "poisson": ("Poisson", True, [("lam", "Tasa media (λ)", 4)]),
    "geometrica": ("Geométrica", True, [("p", "Prob. de éxito (p)", 0.3)]),
}


def catalogo():
    return [
        {"id": k, "nombre": v[0], "discreta": v[1],
         "params": [{"id": i, "etiqueta": e, "defecto": d} for i, e, d in v[2]]}
        for k, v in DEFS.items()
    ]


def congelar(dist, par):
    if dist not in DEFS:
        raise ValueError("Distribución no soportada.")
    try:
        v = {k: float(par[k]) for k, _, _ in DEFS[dist][2]}
    except (KeyError, TypeError, ValueError):
        raise ValueError("Completa todos los parámetros con números válidos.") from None
    if dist == "normal":
        if v["sigma"] <= 0:
            raise ValueError("σ debe ser mayor que 0.")
        return stats.norm(v["mu"], v["sigma"])
    if dist == "uniforme":
        if v["b"] <= v["a"]:
            raise ValueError("b debe ser mayor que a.")
        return stats.uniform(v["a"], v["b"] - v["a"])
    if dist == "exponencial":
        if v["lam"] <= 0:
            raise ValueError("λ debe ser mayor que 0.")
        return stats.expon(scale=1 / v["lam"])
    if dist in ("t", "chi2"):
        if v["df"] <= 0:
            raise ValueError("Los grados de libertad deben ser mayores que 0.")
        return stats.t(v["df"]) if dist == "t" else stats.chi2(v["df"])
    if dist == "binomial":
        if v["n"] < 1 or v["n"] != int(v["n"]):
            raise ValueError("n debe ser un entero mayor o igual a 1.")
        if not 0 <= v["p"] <= 1:
            raise ValueError("p debe estar entre 0 y 1.")
        return stats.binom(int(v["n"]), v["p"])
    if dist == "poisson":
        if v["lam"] <= 0:
            raise ValueError("λ debe ser mayor que 0.")
        return stats.poisson(v["lam"])
    if not 0 < v["p"] <= 1:
        raise ValueError("p debe estar en (0, 1].")
    return stats.geom(v["p"])


def _n(v):
    return f"{v:g}"


def calcular(dist, par, modo, x=None, a=None, b=None, prob=None):
    d = congelar(dist, par)
    disc = DEFS[dist][1]
    inf = float("inf")
    if modo in ("menor", "mayor", "igual"):
        if x is None:
            raise ValueError("Escribe el valor de x.")
        if disc and x != int(x):
            raise ValueError("En distribuciones discretas x debe ser un número entero.")
    if modo == "menor":
        valor = d.cdf(x)
        etiqueta = f"P(X ≤ {_n(x)})" if disc else f"P(X < {_n(x)})"
        lo, hi = -inf, x
    elif modo == "mayor":
        valor, etiqueta = d.sf(x), f"P(X > {_n(x)})"
        lo, hi = (x + 1 if disc else x), inf
    elif modo == "entre":
        if a is None or b is None:
            raise ValueError("Escribe los valores a y b.")
        if a > b:
            raise ValueError("a debe ser menor o igual que b.")
        if disc and (a != int(a) or b != int(b)):
            raise ValueError("En distribuciones discretas a y b deben ser enteros.")
        valor = d.cdf(b) - (d.cdf(a - 1) if disc else d.cdf(a))
        etiqueta, lo, hi = f"P({_n(a)} ≤ X ≤ {_n(b)})", a, b
    elif modo == "igual":
        valor = d.pmf(x) if disc else 0.0
        etiqueta, lo, hi = f"P(X = {_n(x)})", x, x
    elif modo == "percentil":
        if prob is None or not 0 < prob < 1:
            raise ValueError("La probabilidad debe estar entre 0 y 1 (sin incluirlos).")
        valor = d.ppf(prob)
        etiqueta, lo, hi = f"x tal que P(X ≤ x) = {_n(prob)}", -inf, valor
    else:
        raise ValueError("Modo de cálculo no válido.")

    if disc:
        k0, k1 = int(d.ppf(0.0005)), int(d.ppf(0.9995))
        ks = np.arange(k0, min(k1, k0 + 300) + 1)
        grafico = {"x": ks, "y": d.pmf(ks), "region": (ks >= lo) & (ks <= hi)}
    else:
        lo_g, hi_g = d.ppf(0.0005), d.ppf(0.9995)
        pad = 0.08 * (hi_g - lo_g)
        xs = np.linspace(0 if dist in ("exponencial", "chi2") else lo_g - pad, hi_g + pad, 400)
        ys = d.pdf(xs)
        m = (xs >= lo) & (xs <= hi)
        grafico = {"x": xs, "y": ys, "region_x": xs[m], "region_y": ys[m]}
    return {
        "etiqueta": etiqueta, "valor": float(valor), "media": d.mean(), "varianza": d.var(),
        "desviacion": d.std(), "discreta": disc, "grafico": grafico,
    }


def muestral(dist, par, n, repeticiones):
    if not 1 <= n <= 500:
        raise ValueError("El tamaño de muestra n debe estar entre 1 y 500.")
    if not 100 <= repeticiones <= 5000:
        raise ValueError("El número de muestras debe estar entre 100 y 5000.")
    d = congelar(dist, par)
    mu, sigma = d.mean(), d.std()
    if not (np.isfinite(mu) and np.isfinite(sigma)):
        raise ValueError("Con esos parámetros la distribución no tiene media o varianza finitas.")
    datos = d.rvs(size=(repeticiones, n), random_state=np.random.default_rng(42))
    medias = datos.mean(axis=1)
    dens, bordes = np.histogram(medias, bins=30, density=True)
    se = sigma / np.sqrt(n)
    xs = np.linspace(mu - 4 * se, mu + 4 * se, 200)
    return {
        "centros": (bordes[:-1] + bordes[1:]) / 2, "densidad": dens, "ancho": bordes[1] - bordes[0],
        "curva": {"x": xs, "y": stats.norm.pdf(xs, mu, se)},
        "media_medias": medias.mean(), "desv_medias": medias.std(ddof=1),
        "mu": mu, "sigma": sigma, "error_estandar": se, "n": n, "repeticiones": repeticiones,
    }