"""Utilidades comunes."""
import math

import numpy as np
import pandas as pd


def a_json(o):
    """Convierte tipos de numpy/pandas a tipos JSON; NaN e infinitos pasan a None."""
    if isinstance(o, dict):
        return {str(k): a_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [a_json(v) for v in o]
    if isinstance(o, np.ndarray):
        return a_json(o.tolist())
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        return f if math.isfinite(f) else None
    if isinstance(o, pd.Timestamp):
        return o.isoformat()
    return o


def a_float(valor):
    """Texto opcional -> float o None. Acepta coma decimal."""
    if valor is None:
        return None
    texto = str(valor).strip().replace(",", ".")
    if texto == "":
        return None
    try:
        v = float(texto)
    except ValueError:
        raise ValueError(f"«{valor}» no es un número válido.") from None
    if not math.isfinite(v):
        raise ValueError(f"«{valor}» no es un número válido.")
    return v


def muestrear(x, maximo):
    """Reduce un arreglo a 'maximo' puntos equiespaciados (para gráficos)."""
    x = np.asarray(x)
    if len(x) <= maximo:
        return x
    return x[np.linspace(0, len(x) - 1, maximo).astype(int)]


def etiqueta(v):
    """Valor de una celda -> texto limpio (1.0 -> '1')."""
    if isinstance(v, (bool, np.bool_)):
        return str(v)
    if isinstance(v, (int, float, np.integer, np.floating)):
        return str(int(v)) if float(v).is_integer() else f"{v:g}"
    return str(v).strip()


def etiquetas_grupo(serie):
    """Serie -> (Serie de textos con None donde falta, lista de grupos ordenados)."""
    lab = serie.map(lambda v: None if pd.isna(v) else etiqueta(v)).astype(object)
    orden = list(pd.unique(lab.dropna()))
    try:
        orden.sort(key=float)
    except ValueError:
        orden.sort()
    return lab, orden