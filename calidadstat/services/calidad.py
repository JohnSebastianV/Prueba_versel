"""Control estadístico de procesos: cartas I-MR y X̄-R, índices de capacidad."""
import numpy as np
from scipy import stats

from .descriptiva import histograma
from .lectura import serie_ordenada

MAX_PUNTOS = 5000
# n: (d2, A2, D3, D4)
CONST = {
    2: (1.128, 1.880, 0.0, 3.267), 3: (1.693, 1.023, 0.0, 2.574), 4: (2.059, 0.729, 0.0, 2.282),
    5: (2.326, 0.577, 0.0, 2.114), 6: (2.534, 0.483, 0.0, 2.004), 7: (2.704, 0.419, 0.076, 1.924),
    8: (2.847, 0.373, 0.136, 1.864), 9: (2.970, 0.337, 0.184, 1.816), 10: (3.078, 0.308, 0.223, 1.777),
}


def _rachas(valores, cl, largo=8):
    """Índices de puntos en rachas de 'largo' o más puntos consecutivos del mismo lado de la línea central."""
    signo = np.sign(valores - cl)
    marcados, inicio = set(), 0
    for i in range(1, len(signo) + 1):
        if i == len(signo) or signo[i] != signo[inicio]:
            if signo[inicio] != 0 and i - inicio >= largo:
                marcados.update(range(inicio, i))
            inicio = i
    return sorted(marcados)


def _linea(nombre, valores, etiquetas, cl, ucl, lcl, rachas=True):
    valores = np.asarray(valores, float)
    fuera = np.where((valores > ucl) | (valores < lcl))[0]
    return {
        "nombre": nombre, "x": list(range(1, len(valores) + 1)), "valores": valores,
        "etiquetas": etiquetas, "cl": cl, "ucl": ucl, "lcl": lcl, "fuera": fuera,
        "racha8": _rachas(valores, cl) if rachas else [],
    }


def _carta(x, etiquetas, n_sub):
    if n_sub is None or n_sub <= 1:
        if len(x) < 5:
            raise ValueError("Se necesitan al menos 5 mediciones para una carta de control.")
        mr = np.abs(np.diff(x))
        mrbar = float(mr.mean())
        if mrbar == 0:
            raise ValueError("Todas las mediciones son iguales: no hay variabilidad que graficar.")
        sigma = mrbar / 1.128
        cl = float(x.mean())
        princ = _linea("Carta de individuos (I)", x, etiquetas, cl, cl + 3 * sigma, cl - 3 * sigma)
        sec = _linea("Carta de rango móvil (MR)", mr, etiquetas[1:], mrbar, 3.267 * mrbar, 0.0, rachas=False)
        return "I-MR", princ, sec, sigma
    if n_sub not in CONST:
        raise ValueError("El tamaño de subgrupo debe estar entre 2 y 10.")
    k = len(x) // n_sub
    if k < 5:
        raise ValueError(f"Con subgrupos de {n_sub} se necesitan al menos {5 * n_sub} mediciones.")
    sub = x[: k * n_sub].reshape(k, n_sub)
    xb, r = sub.mean(axis=1), np.ptp(sub, axis=1)
    d2, a2, d3, d4 = CONST[n_sub]
    xbb, rbar = float(xb.mean()), float(r.mean())
    if rbar == 0:
        raise ValueError("Los rangos de todos los subgrupos son cero: no hay variabilidad que graficar.")
    et = etiquetas[: k * n_sub : n_sub]
    princ = _linea(f"Carta de medias (X̄, n = {n_sub})", xb, et, xbb, xbb + a2 * rbar, xbb - a2 * rbar)
    sec = _linea("Carta de rangos (R)", r, et, rbar, d4 * rbar, d3 * rbar, rachas=False)
    return "X̄-R", princ, sec, rbar / d2


def capacidad(x, sigma_w, lsl, usl):
    if lsl is None and usl is None:
        return None
    if lsl is not None and usl is not None and lsl >= usl:
        raise ValueError("El límite inferior (LSL) debe ser menor que el superior (USL).")
    mu, s_tot = float(x.mean()), float(x.std(ddof=1))
    if s_tot == 0 or sigma_w == 0:
        raise ValueError("No hay variabilidad: no se pueden calcular los índices de capacidad.")

    def indices(sig):
        cu = (usl - mu) / (3 * sig) if usl is not None else None
        cl_ = (mu - lsl) / (3 * sig) if lsl is not None else None
        ck = min(v for v in (cu, cl_) if v is not None)
        cp = (usl - lsl) / (6 * sig) if (usl is not None and lsl is not None) else None
        return cp, ck, cu, cl_

    cp, cpk, cpu, cpl = indices(sigma_w)
    pp, ppk, _, _ = indices(s_tot)
    fuera_mask = np.zeros(len(x), bool)
    ppm = 0.0
    if lsl is not None:
        fuera_mask |= x < lsl
        ppm += stats.norm.cdf(lsl, mu, s_tot)
    if usl is not None:
        fuera_mask |= x > usl
        ppm += stats.norm.sf(usl, mu, s_tot)
    clase = (
        "Excelente" if cpk >= 1.67 else "Capaz" if cpk >= 1.33
        else "Marginalmente capaz" if cpk >= 1.0 else "No capaz"
    )
    return {
        "cp": cp, "cpk": cpk, "cpu": cpu, "cpl": cpl, "pp": pp, "ppk": ppk,
        "fuera_obs_pct": float(fuera_mask.mean() * 100), "ppm_esperado": ppm * 1e6,
        "clasificacion": clase, "descentrado": bool(cp is not None and cp - cpk > 0.25),
    }


def analisis_calidad(df, columna, orden, lsl, usl, objetivo, n_sub):
    x, etiquetas, usado = serie_ordenada(df, columna, orden)
    avisos = []
    if not usado:
        avisos.append("No se eligió columna de orden: se usó el orden original de las filas como secuencia en el tiempo.")
    if len(x) > MAX_PUNTOS:
        x, etiquetas = x[-MAX_PUNTOS:], etiquetas[-MAX_PUNTOS:]
        avisos.append(f"Se analizaron solo las últimas {MAX_PUNTOS} mediciones.")
    if len(x) < 20:
        avisos.append("Hay menos de 20 mediciones: la carta y los índices son poco confiables (se recomiendan 100 o más).")
    tipo, princ, sec, sigma_w = _carta(x, etiquetas, n_sub)
    cap = capacidad(x, sigma_w, lsl, usl)
    estable = len(princ["fuera"]) == 0 and len(sec["fuera"]) == 0
    if cap and not estable:
        avisos.append("El proceso tiene puntos fuera de control: los índices de capacidad solo son orientativos hasta eliminar las causas especiales.")
    return {
        "columna": columna, "n": len(x), "orden_usado": usado, "tipo_carta": tipo,
        "principal": princ, "secundaria": sec, "sigma_within": sigma_w,
        "media": float(x.mean()), "desviacion_total": float(x.std(ddof=1)),
        "lsl": lsl, "usl": usl, "objetivo": objetivo, "capacidad": cap, "estable": estable,
        "histograma": histograma(x), "avisos": avisos,
    }