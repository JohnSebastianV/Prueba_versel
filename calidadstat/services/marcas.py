"""Estudio comparativo de grupos (p. ej. marcas de un producto): cajas, especificaciones,
desempeño global, intervalos de confianza, comparación de varianzas y prueba de proporción."""
import numpy as np
import pandas as pd
from scipy import stats

from .descriptiva import caja, normalidad
from .interpretacion import f, fp
from .util import etiquetas_grupo


def tp(p):
    """p-valor para texto: 'p < 0,001' o 'p = 0,123'."""
    return "p < 0,001" if p < 0.001 else f"p = {f(p, 3)}"


def ng(v):
    """Número compacto en español: 400 -> '400', 2.7 -> '2,7'."""
    return f"{v:g}".replace(".", ",")


def _etq(nombre, g):
    try:
        float(g)
        return f"{nombre.strip().capitalize()} {g}"
    except ValueError:
        return f"«{g}»"


def _num(d, col, rol):
    if not col or col not in d.columns:
        raise ValueError(f"Elige la columna para «{rol}».")
    if pd.api.types.is_bool_dtype(d[col]) or not pd.api.types.is_numeric_dtype(d[col]):
        raise ValueError(f"La columna «{col}» no es numérica.")
    return col


def _x(d, g, col):
    return d.loc[d["_g"] == g, col].dropna().to_numpy(float)


def _minimo(x, g, col, n=3):
    if len(x) < n:
        raise ValueError(f"El grupo «{g}» tiene menos de {n} datos válidos en «{col}».")
    return x


# ---------------------------------------------------------------- a)
def seccion_a(d, orden, ng_, col, lim, lim2):
    _num(d, col, "variable de emisión")
    filas = []
    for g in orden:
        x = _minimo(_x(d, g, col), g, col)
        q1, med, q3 = np.percentile(x, [25, 50, 75])
        fila = {"grupo": g, "n": len(x), "media": x.mean(), "mediana": med, "desviacion": x.std(ddof=1),
                "iqr": q3 - q1, "minimo": x.min(), "maximo": x.max(), "caja": caja(x),
                "pct_limite": float((x <= lim).mean() * 100) if lim is not None else None,
                "pct_norma": float((x <= lim2).mean() * 100) if lim2 is not None else None}
        filas.append(fila)
    mejor = min(filas, key=lambda r: (r["mediana"], r["media"]))
    peor = max(filas, key=lambda r: r["mediana"])
    ordenados = sorted(filas, key=lambda r: r["mediana"])
    txt = [
        f"{_etq(ng_, mejor['grupo'])} es la que emite menos «{col}»: mediana {f(mejor['mediana'])} y media {f(mejor['media'])}. "
        "Orden por mediana (de menor a mayor): "
        + ", ".join(f"{_etq(ng_, r['grupo'])} ({f(r['mediana'], 1)})" for r in ordenados) + "."
    ]
    if min(filas, key=lambda r: r["media"])["grupo"] != mejor["grupo"]:
        txt.append("Ojo: la media más baja corresponde a otro grupo; se priorizó la mediana porque es menos sensible a valores extremos.")
    menor_iqr = min(filas, key=lambda r: r["iqr"])
    mayor_iqr = max(filas, key=lambda r: r["iqr"])
    txt.append(f"La caja más angosta (menor dispersión, IQR = {f(menor_iqr['iqr'])}) es la de {_etq(ng_, menor_iqr['grupo'])}; "
               f"la más ancha (IQR = {f(mayor_iqr['iqr'])}) es la de {_etq(ng_, mayor_iqr['grupo'])}, es decir, la menos consistente.")
    if lim is not None:
        sobre = [r for r in filas if r["caja"]["q3"] > lim]
        if sobre:
            txt.append(f"El tercer cuartil supera el límite de {ng(lim)} en: " + ", ".join(_etq(ng_, r["grupo"]) for r in sobre)
                       + ". Esto significa que más del 25 % de sus datos excede ese límite.")
        else:
            txt.append(f"Ningún grupo tiene su tercer cuartil por encima de {ng(lim)}.")
        cumple = [r for r in filas if r["pct_limite"] == 100]
        if cumple:
            txt.append("Cumplen el límite en el 100 % de sus datos: " + ", ".join(_etq(ng_, r["grupo"]) for r in cumple) + ".")
    atip = [r for r in filas if r["caja"]["n_atipicos"]]
    if atip:
        txt.append("Hay valores atípicos (criterio 1,5 × IQR) en: "
                   + ", ".join(f"{_etq(ng_, r['grupo'])} ({r['caja']['n_atipicos']})" for r in atip) + ".")
    return {"columna": col, "limite": lim, "limite2": lim2, "tabla": filas, "mejor": mejor["grupo"],
            "peor": peor["grupo"], "texto": txt}


# ---------------------------------------------------------------- b)
def seccion_b(d, orden, ng_, col, objetivo, tol):
    _num(d, col, "variable con especificación")
    if objetivo is None or tol is None:
        raise ValueError("Escribe el valor objetivo y la tolerancia (±).")
    if tol <= 0:
        raise ValueError("La tolerancia debe ser mayor que 0.")
    lsl, usl = round(objetivo - tol, 9), round(objetivo + tol, 9)
    filas = []
    for g in orden:
        x = _minimo(_x(d, g, col), g, col)
        mu, s = x.mean(), x.std(ddof=1)
        if s == 0:
            raise ValueError(f"El grupo «{g}» no tiene variabilidad en «{col}».")
        filas.append({
            "grupo": g, "n": len(x), "media": mu, "desviacion": s, "desv_objetivo": mu - objetivo,
            "pct_cumple": float(((x >= lsl) & (x <= usl)).mean() * 100),
            "pct_bajo": float((x < lsl).mean() * 100), "pct_sobre": float((x > usl).mean() * 100),
            "cp": (usl - lsl) / (6 * s), "cpk": min(usl - mu, mu - lsl) / (3 * s),
            "cpm": (usl - lsl) / (6 * np.sqrt(s ** 2 + (mu - objetivo) ** 2)),
        })
    mejor = max(filas, key=lambda r: (r["pct_cumple"], r["cpk"]))
    otro_cpk = max(filas, key=lambda r: r["cpk"])
    ordenados = sorted(filas, key=lambda r: -r["pct_cumple"])
    txt = [
        f"Especificación de «{col}»: {ng(objetivo)} ± {ng(tol)} → [{ng(lsl)} ; {ng(usl)}]. "
        f"{_etq(ng_, mejor['grupo'])} es la que mejor cumple: {f(mejor['pct_cumple'], 1)} % de sus datos dentro de especificación "
        f"(Cpk = {f(mejor['cpk'])}, media {f(mejor['media'])}, desviación {f(mejor['desviacion'])}).",
        "Porcentaje de cumplimiento por grupo: "
        + ", ".join(f"{_etq(ng_, r['grupo'])} ({f(r['pct_cumple'], 1)} %)" for r in ordenados) + ".",
    ]
    if otro_cpk["grupo"] != mejor["grupo"]:
        txt.append(f"Por Cpk, el mejor sería {_etq(ng_, otro_cpk['grupo'])} ({f(otro_cpk['cpk'])}); el criterio principal fue el % de cumplimiento observado.")
    bajos = [r for r in filas if r["cpk"] < 1.0]
    if bajos:
        txt.append("Con Cpk < 1,00 (proceso no capaz): " + ", ".join(_etq(ng_, r["grupo"]) for r in bajos) + ".")
    return {"columna": col, "objetivo": objetivo, "tolerancia": tol, "lsl": lsl, "usl": usl,
            "tabla": filas, "mejor": mejor["grupo"], "texto": txt}


# ---------------------------------------------------------------- c)
def seccion_c(d, orden, ng_, a, b, extras):
    criterios = []  # (id, nombre, sentido, {grupo: valor})
    if a:
        criterios.append(("media_a", f"Media de {a['columna']}", "menor", {r["grupo"]: r["media"] for r in a["tabla"]}))
        if a["limite"] is not None:
            criterios.append(("pct_a", f"% que cumple {a['columna']} ≤ {ng(a['limite'])}", "mayor",
                              {r["grupo"]: r["pct_limite"] for r in a["tabla"]}))
    if b:
        criterios.append(("pct_b", f"% dentro de especificación ({b['columna']})", "mayor", {r["grupo"]: r["pct_cumple"] for r in b["tabla"]}))
        criterios.append(("cpk_b", f"Cpk de {b['columna']}", "mayor", {r["grupo"]: r["cpk"] for r in b["tabla"]}))
    for col, sentido in extras:
        _num(d, col, "variable adicional")
        vals = {}
        for g in orden:
            x = _minimo(_x(d, g, col), g, col)
            vals[g] = float(x.mean())
        criterios.append((f"extra_{col}", f"Media de {col}", sentido, vals))
    if not criterios:
        raise ValueError("No hay criterios para comparar: configura al menos una variable.")
    rangos = {g: {} for g in orden}
    for cid, _, sentido, vals in criterios:
        v = np.array([vals[g] for g in orden], float)
        r = stats.rankdata(v if sentido == "menor" else -v, method="average")
        for g, ri in zip(orden, r):
            rangos[g][cid] = float(ri)
    filas = []
    for g in orden:
        filas.append({"grupo": g, "valores": {cid: vals[g] for cid, _, _, vals in criterios},
                      "rangos": rangos[g], "total": float(sum(rangos[g].values())),
                      "primeros": int(sum(1 for v in rangos[g].values() if v == 1.0))})
    minimo = min(r["total"] for r in filas)
    empatados = [r for r in filas if abs(r["total"] - minimo) < 1e-9]
    mejor = empatados[0]
    txt = ["Se ordenó cada grupo en cada criterio (1 = mejor) y se sumaron los rangos con igual peso; gana la menor suma."]
    if len(empatados) == 1:
        txt.append(f"{_etq(ng_, mejor['grupo'])} obtiene la menor suma ({f(mejor['total'], 1)} de un máximo posible de "
                   f"{len(criterios) * len(orden)}) y es primero en {mejor['primeros']} de {len(criterios)} criterios.")
    else:
        txt.append("Hay empate en la menor suma entre: " + ", ".join(_etq(ng_, r["grupo"]) for r in empatados)
                   + ". Desempata con el criterio que consideres más importante para el negocio.")
    ult = max(filas, key=lambda r: r["total"])
    txt.append(f"El menor desempeño global es el de {_etq(ng_, ult['grupo'])} (suma {f(ult['total'], 1)}).")
    txt.append("Este método pondera todos los criterios por igual; si alguno es más crítico (p. ej. seguridad por emisiones), "
               "el resultado podría cambiar.")
    return {"criterios": [{"id": c[0], "nombre": c[1], "sentido": c[2]} for c in criterios],
            "tabla": filas, "mejor": mejor["grupo"], "empate": len(empatados) > 1, "texto": txt}


# ---------------------------------------------------------------- d)
def seccion_d(d, g, ng_, col_bil, col_menor, limite, conf):
    alfa = 1 - conf
    out = {"grupo": g, "etiqueta": _etq(ng_, g), "conf": conf}
    txt = []
    if col_bil:
        _num(d, col_bil, "variable con especificación")
        x = _minimo(_x(d, g, col_bil), g, col_bil)
        n, m, s2 = len(x), x.mean(), x.var(ddof=1)
        h = stats.t.ppf(1 - alfa / 2, n - 1) * np.sqrt(s2 / n)
        v_inf = (n - 1) * s2 / stats.chi2.ppf(1 - alfa / 2, n - 1)
        v_sup = (n - 1) * s2 / stats.chi2.ppf(alfa / 2, n - 1)
        out["media"] = {"columna": col_bil, "n": n, "estimado": m, "inferior": m - h, "superior": m + h}
        out["varianza"] = {"columna": col_bil, "estimado": s2, "inferior": v_inf, "superior": v_sup,
                           "sd_inf": np.sqrt(v_inf), "sd_sup": np.sqrt(v_sup)}
        txt.append(f"Con {f(conf * 100, 0)} % de confianza, la media de «{col_bil}» de {out['etiqueta']} está entre {f(m - h, 4)} y {f(m + h, 4)}.")
        txt.append(f"La varianza está entre {f(v_inf, 4)} y {f(v_sup, 4)} (desviación estándar entre {f(np.sqrt(v_inf), 4)} y {f(np.sqrt(v_sup), 4)}).")
        out["supuesto"] = "Estos intervalos suponen que los datos provienen de una población aproximadamente normal (el de la varianza es muy sensible a ello)."
    if col_menor and limite is not None:
        _num(d, col_menor, "variable de emisión")
        x = _minimo(_x(d, g, col_menor), g, col_menor)
        n = len(x)
        k = int((x <= limite).sum())
        ph = k / n
        z = stats.norm.ppf(1 - alfa / 2)
        se = np.sqrt(ph * (1 - ph) / n)
        wald = [max(0.0, ph - z * se), min(1.0, ph + z * se)]
        centro = (ph + z * z / (2 * n)) / (1 + z * z / n)
        med = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / (1 + z * z / n)
        wilson = [max(0.0, centro - med), min(1.0, centro + med)]
        ex = stats.binomtest(k, n).proportion_ci(confidence_level=conf, method="exact")
        out["proporcion"] = {"columna": col_menor, "limite": limite, "n": n, "exitos": k, "estimado": ph,
                             "wald": wald, "wilson": wilson, "exacto": [float(ex.low), float(ex.high)]}
        txt.append(f"Proporción de unidades con «{col_menor}» ≤ {ng(limite)}: {f(ph * 100, 2)} % ({k} de {n}). "
                   f"IC {f(conf * 100, 0)} % (Wilson): {f(wilson[0] * 100, 2)} % a {f(wilson[1] * 100, 2)} %.")
        if ph in (0.0, 1.0):
            txt.append("Como la proporción observada es 0 o 1, el intervalo de Wald colapsa a un solo punto (no es confiable); "
                       "usa el de Wilson o el exacto.")
    if not txt:
        raise ValueError("Configura una variable con especificación o una variable de emisión con su límite.")
    out["texto"] = txt
    return out


# ---------------------------------------------------------------- e)
def seccion_e(d, g1, g2, ng_, col, conf):
    if g1 == g2:
        raise ValueError("Elige dos grupos distintos para comparar la variabilidad.")
    _num(d, col, "variable a comparar")
    alfa = 1 - conf
    x1 = _minimo(_x(d, g1, col), g1, col)
    x2 = _minimo(_x(d, g2, col), g2, col)
    n1, n2 = len(x1), len(x2)
    v1, v2 = x1.var(ddof=1), x2.var(ddof=1)
    if v2 == 0:
        raise ValueError("Uno de los grupos no tiene variabilidad.")
    F = v1 / v2
    d1, d2 = n1 - 1, n2 - 1
    cdf = stats.f.cdf(F, d1, d2)
    p = 2 * min(cdf, 1 - cdf)
    ic = [F / stats.f.ppf(1 - alfa / 2, d1, d2), F / stats.f.ppf(alfa / 2, d1, d2)]
    lev = float(stats.levene(x1, x2, center="median").pvalue)
    n1_, n2_ = normalidad(x1), normalidad(x2)
    rechaza = bool(p < alfa)
    e1, e2 = _etq(ng_, g1), _etq(ng_, g2)
    txt = [f"Prueba F de razón de varianzas (H₀: σ₁² = σ₂²; H₁: σ₁² ≠ σ₂²): F = {f(F, 3)} con {d1} y {d2} g.l., {tp(p)}. "
           f"{'Se rechaza H₀' if rechaza else 'No se rechaza H₀'} al {f(alfa * 100, 0)} %: "
           + (f"hay evidencia de que la variabilidad de «{col}» es distinta entre {e1} (s = {f(np.sqrt(v1), 4)}) y {e2} (s = {f(np.sqrt(v2), 4)})."
              if rechaza else "no hay evidencia suficiente de que la variabilidad difiera entre los dos grupos."),
           f"El IC {f(conf * 100, 0)} % para σ₁²/σ₂² es [{f(ic[0], 3)} ; {f(ic[1], 3)}]; "
           + ("no contiene al 1, consistente con la decisión." if not (ic[0] <= 1 <= ic[1]) else "contiene al 1, consistente con la decisión."),
           f"Como verificación robusta (no exige normalidad), la prueba de Levene da {tp(lev)}."]
    if (n1_ and not n1_["normal"]) or (n2_ and not n2_["normal"]):
        txt.append("Advertencia: Shapiro-Wilk rechaza la normalidad en algún grupo; la prueba F es sensible a eso, así que apóyate más en Levene.")
    return {"columna": col, "g1": g1, "g2": g2, "n1": n1, "n2": n2, "s1": np.sqrt(v1), "s2": np.sqrt(v2),
            "var1": v1, "var2": v2, "f": F, "gl1": d1, "gl2": d2, "p": p, "ic": ic, "conf": conf,
            "levene_p": lev, "rechaza": rechaza, "normal1": n1_, "normal2": n2_, "texto": txt}


# ---------------------------------------------------------------- f)
def seccion_f(d, g, ng_, col, limite, p0, alt, conf):
    _num(d, col, "variable de emisión")
    if limite is None:
        raise ValueError("Escribe el límite de especificación de la variable de emisión.")
    if p0 is None or not 0 < p0 < 1:
        raise ValueError("La proporción afirmada debe estar entre 0 y 1 (por ejemplo 0,80).")
    if alt not in ("distinto", "menor", "mayor"):
        raise ValueError("Alternativa no válida.")
    alfa = 1 - conf
    x = _minimo(_x(d, g, col), g, col)
    n = len(x)
    k = int((x <= limite).sum())
    ph = k / n
    z = (ph - p0) / np.sqrt(p0 * (1 - p0) / n)
    if alt == "distinto":
        pz, h1, ba = 2 * stats.norm.sf(abs(z)), f"p ≠ {ng(p0)}", "two-sided"
    elif alt == "menor":
        pz, h1, ba = stats.norm.cdf(z), f"p < {ng(p0)}", "less"
    else:
        pz, h1, ba = stats.norm.sf(z), f"p > {ng(p0)}", "greater"
    pe = float(stats.binomtest(k, n, p0, alternative=ba).pvalue)
    rechaza = bool(pz < alfa)
    etq = _etq(ng_, g)
    txt = [f"{etq}: {k} de {n} unidades cumplen «{col}» ≤ {ng(limite)} (p̂ = {f(ph * 100, 2)} %). "
           f"Prueba Z de una proporción (H₀: p = {ng(p0)}; H₁: {h1}): z = {f(z, 3)}, {tp(pz)}. "
           f"{'Se rechaza H₀' if rechaza else 'No se rechaza H₀'} al {f(alfa * 100, 0)} %.",
           f"Prueba binomial exacta: {tp(pe)}."]
    if rechaza:
        if ph > p0:
            txt.append(f"Los datos no respaldan la afirmación como está planteada: la proporción observada ({f(ph * 100, 1)} %) es "
                       f"mayor que la afirmada ({f(p0 * 100, 0)} %); el fabricante estaría subestimando su cumplimiento.")
        else:
            txt.append(f"Los datos contradicen la afirmación: la proporción observada ({f(ph * 100, 1)} %) es menor que la afirmada ({f(p0 * 100, 0)} %).")
    else:
        txt.append("Los datos son compatibles con la afirmación del fabricante.")
    if n * p0 < 10 or n * (1 - p0) < 10:
        txt.append("Advertencia: no se cumple n·p₀ ≥ 10 y n·(1−p₀) ≥ 10; la aproximación normal es débil, usa la prueba exacta.")
    return {"grupo": g, "etiqueta": etq, "columna": col, "limite": limite, "n": n, "exitos": k, "p0": p0, "alternativa": alt,
            "h1": h1, "phat": ph, "z": z, "p_z": pz, "p_exacto": pe, "rechaza": rechaza, "alfa": alfa, "texto": txt}


# ---------------------------------------------------------------- orquestador
def analizar(df, grupo, col_menor, limite, limite2, col_bil, objetivo, tol, extras, conf, sel, g1, g2, p0, alt):
    if grupo not in df.columns:
        raise ValueError("Elige la columna que identifica los grupos (p. ej. la marca).")
    if not 0.5 < conf < 1:
        raise ValueError("El nivel de confianza debe estar entre 0,5 y 1.")
    lab, orden = etiquetas_grupo(df[grupo])
    d = df.copy()
    d["_g"] = lab
    excluidas = int(d["_g"].isna().sum())
    d = d[d["_g"].notna()]
    if len(orden) < 2:
        raise ValueError("La columna de grupo debe tener al menos 2 valores distintos.")
    if len(orden) > 12:
        raise ValueError("La columna de grupo tiene demasiados valores distintos (máximo 12).")
    ng_ = grupo
    res = {"grupo_col": grupo, "grupos": orden, "n_total": len(d), "avisos": []}
    if excluidas:
        res["avisos"].append(f"Se excluyeron {excluidas} filas sin valor en «{grupo}».")
    errores = {}

    def correr(nombre, fn):
        try:
            res[nombre] = fn()
        except ValueError as e:
            errores[nombre] = str(e)

    if col_menor:
        correr("a", lambda: seccion_a(d, orden, ng_, col_menor, limite, limite2))
    if col_bil:
        correr("b", lambda: seccion_b(d, orden, ng_, col_bil, objetivo, tol))
    if "a" in res or "b" in res or extras:
        correr("c", lambda: seccion_c(d, orden, ng_, res.get("a"), res.get("b"), extras))
    mejor = (res.get("c") or {}).get("mejor") or (res.get("a") or {}).get("mejor") or orden[0]
    elegido = sel if sel in orden else mejor
    res["grupo_analizado"] = elegido
    if col_bil or (col_menor and limite is not None):
        correr("d", lambda: seccion_d(d, elegido, ng_, col_bil, col_menor, limite, conf))
    if col_bil:
        a1 = g1 if g1 in orden else orden[0]
        a2 = g2 if g2 in orden else orden[1]
        correr("e", lambda: seccion_e(d, a1, a2, ng_, col_bil, conf))
    if col_menor and limite is not None:
        correr("f", lambda: seccion_f(d, elegido, ng_, col_menor, limite, p0, alt, conf))
    res["errores"] = errores
    return res