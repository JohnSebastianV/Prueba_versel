"""Lectura, limpieza y perfilado de archivos CSV/Excel."""
import io
import warnings

import numpy as np
import pandas as pd
from .util import etiquetas_grupo

MAX_FILAS = 200_000


def leer_archivo(nombre, contenido):
    n = (nombre or "").lower()
    if n.endswith((".csv", ".txt")):
        texto = None
        for enc in ("utf-8-sig", "latin-1"):
            try:
                texto = contenido.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        try:
            # sep=None detecta coma, punto y coma o tabulación
            df = pd.read_csv(io.StringIO(texto), sep=None, engine="python")
        except Exception:
            try:
                df = pd.read_csv(io.StringIO(texto))
            except Exception as e:
                raise ValueError(
                    "No se pudo leer el CSV. Revisa que tenga encabezados en la primera fila "
                    "y un separador consistente."
                ) from e
    elif n.endswith((".xlsx", ".xlsm")):
        try:
            df = pd.read_excel(io.BytesIO(contenido), engine="openpyxl")
        except Exception as e:
            raise ValueError(
                "No se pudo leer el Excel. Usa una sola tabla en la primera hoja, "
                "con encabezados en la primera fila."
            ) from e
    else:
        raise ValueError("Formato no soportado. Usa .csv o .xlsx.")
    if df.empty:
        raise ValueError("El archivo no tiene datos.")
    return df


def _a_fecha(txt):
    """txt: Serie de textos sin nulos. Devuelve Serie datetime o None si no son fechas."""
    if txt.str.contains(r"[-/:]", regex=True).mean() < 0.9:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if pd.to_datetime(txt.head(50), errors="coerce", format="mixed").notna().mean() < 0.9:
            return None
        f = pd.to_datetime(txt, errors="coerce", format="mixed")
    if f.notna().mean() < 0.9 or not pd.api.types.is_datetime64_any_dtype(f):
        return None
    return f


def limpiar(df):
    """Limpia el DataFrame y devuelve (df, avisos) describiendo lo que se corrigió."""
    avisos = []
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    sin_nombre = [c for c in df.columns if c.startswith("Unnamed:") and df[c].isna().all()]
    if sin_nombre:
        df = df.drop(columns=sin_nombre)
        avisos.append(f"Se ignoraron {len(sin_nombre)} columnas vacías sin nombre.")

    if df.columns.duplicated().any():
        vistos, nuevos = {}, []
        for c in df.columns:
            vistos[c] = vistos.get(c, 0) + 1
            nuevos.append(c if vistos[c] == 1 else f"{c}_{vistos[c]}")
        df.columns = nuevos
        avisos.append("Había columnas con el mismo nombre; se les agregó un sufijo.")

    antes = len(df)
    df = df.dropna(how="all").reset_index(drop=True)
    if len(df) < antes:
        avisos.append(f"Se eliminaron {antes - len(df)} filas completamente vacías.")
    if len(df) > MAX_FILAS:
        df = df.head(MAX_FILAS)
        avisos.append(f"El archivo es muy grande: se usaron solo las primeras {MAX_FILAS:,} filas.")
    if df.empty or df.shape[1] == 0:
        raise ValueError("El archivo no tiene datos utilizables.")

    for col in df.columns:
        s = df[col]
        if not (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)):
            continue
        mask = s.notna()
        if not mask.any():
            continue
        txt = s[mask].astype(str).str.strip()

        # Texto numérico (acepta coma decimal: "500,3")
        conv = pd.to_numeric(txt.str.replace(",", ".", regex=False), errors="coerce")
        if conv.notna().mean() >= 0.9:
            nuevo = pd.Series(np.nan, index=df.index, dtype=float)
            nuevo.loc[conv.index] = conv.to_numpy()
            invalidos = int(conv.isna().sum())
            df[col] = nuevo
            if invalidos:
                avisos.append(f"En «{col}» se ignoraron {invalidos} valores que no eran numéricos.")
            continue

        # Fechas escritas como texto
        f = _a_fecha(txt)
        if f is not None:
            nuevo = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
            nuevo.loc[f.index] = f.to_numpy()
            df[col] = nuevo
            continue

        nuevo = s.copy()
        nuevo[mask] = txt
        df[col] = nuevo
    return df, avisos


def tipo_columna(s):
    """numerica | codigo | indice | binaria | categorica | fecha | texto | constante | vacia"""
    validos = s.dropna()
    n = len(validos)
    if n == 0:
        return "vacia"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "fecha"
    u = validos.nunique()
    if pd.api.types.is_bool_dtype(s):
        return "binaria"
    if pd.api.types.is_numeric_dtype(s):
        if u == 1:
            return "constante"
        if u == 2:
            return "binaria"
        entero = bool((validos % 1 == 0).all())
        if entero and n >= 5 and validos.is_monotonic_increasing:
            return "indice"  # contador/ID, p. ej. el número de muestra
        if entero and u <= 10 and n >= 20:
            return "codigo"  # entero con pocos valores: sirve como grupo (marca 1-5) o como conteo
        return "numerica"
    if u == 1:
        return "constante"
    if u == 2:
        return "binaria"
    if u <= max(20, int(0.05 * n)):
        return "categorica"
    return "texto"


def serie_numerica(df, col):
    if not col or col not in df.columns:
        raise ValueError("Elige una columna válida.")
    s = df[col]
    if pd.api.types.is_bool_dtype(s) or not pd.api.types.is_numeric_dtype(s):
        raise ValueError(f"La columna «{col}» no es numérica.")
    s = s.dropna().astype(float)
    if len(s) < 3:
        raise ValueError(f"La columna «{col}» tiene menos de 3 datos válidos.")
    return s


def serie_ordenada(df, col, orden):
    """Valores de 'col' ordenados por 'orden' (si existe). Devuelve (valores, etiquetas, usó_orden)."""
    for c in (col, orden):
        if c and c not in df.columns:
            raise ValueError(f"No existe la columna «{c}».")
    if not pd.api.types.is_numeric_dtype(df[col]) or pd.api.types.is_bool_dtype(df[col]):
        raise ValueError(f"La columna «{col}» no es numérica.")
    cols = [col] + ([orden] if orden and orden != col else [])
    d = df[cols].dropna(subset=[col])
    usado = len(cols) == 2
    if usado:
        d = d.sort_values(orden, kind="mergesort")
        o = d[orden]
        if pd.api.types.is_datetime64_any_dtype(o):
            etiquetas = o.dt.strftime("%Y-%m-%d %H:%M").fillna("").tolist()
        else:
            etiquetas = [str(v) for v in o]
    else:
        etiquetas = [str(i + 1) for i in range(len(d))]
    return d[col].to_numpy(float), etiquetas, usado


def perfil(df, avisos):
    avisos = list(avisos)
    tipos = {c: tipo_columna(df[c]) for c in df.columns}
    n = len(df)
    columnas = []
    for c in df.columns:
        s = df[c]
        validos = int(s.notna().sum())
        ejemplo = next((str(v) for v in s.dropna().head(1)), "")
        columnas.append({
            "nombre": c, "tipo": tipos[c], "validos": validos,
            "faltantes": n - validos, "unicos": int(s.nunique(dropna=True)), "ejemplo": ejemplo,
        })
        if validos and (n - validos) / n > 0.2:
            avisos.append(f"La columna «{c}» tiene {round(100 * (n - validos) / n)} % de valores faltantes.")

    prev = df.head(8)
    vista = {
        "columnas": list(df.columns),
        "filas": [["" if pd.isna(v) else str(v) for v in fila] for fila in prev.itertuples(index=False, name=None)],
    }

    puras = [c for c, t in tipos.items() if t == "numerica"]
    codigos = [c for c, t in tipos.items() if t == "codigo"]
    numericas = puras + codigos  # las numéricas "puras" van primero
    grupos = [c for c, t in tipos.items() if t in ("categorica", "binaria", "codigo") and 2 <= df[c].nunique() <= 10]
    fechas = [c for c, t in tipos.items() if t == "fecha"]
    indices = [c for c, t in tipos.items() if t == "indice"]

    if n < 20:
        avisos.append(f"Hay solo {n} filas: con menos de 20 datos los resultados son poco confiables.")
    if not numericas:
        avisos.append("No se encontraron columnas numéricas: no es posible hacer el análisis.")

    sugerencias = {
        "columna": numericas[0] if numericas else None,
        "grupo": grupos[0] if grupos else None,
        "orden": (fechas or indices or [None])[0],
        "x": puras[1] if len(puras) > 1 else None,
        "y": puras[0] if len(puras) > 1 else None,
    }
    modulos = [
        {"id": "descriptiva", "nombre": "Estadística descriptiva y normalidad", "disponible": bool(numericas),
         "motivo": "Requiere una columna numérica."},
        {"id": "hipotesis", "nombre": "Prueba de hipótesis (media vs. objetivo)", "disponible": bool(numericas),
         "motivo": "Requiere una columna numérica y un valor objetivo."},
        {"id": "grupos", "nombre": "Comparación entre grupos", "disponible": bool(numericas and grupos),
         "motivo": "Requiere una columna numérica y una categórica (2 a 10 grupos)."},
        {"id": "marcas", "nombre": "Comparación de marcas y desempeño", "disponible": bool(numericas and grupos),
         "motivo": "Requiere una columna de grupo (2 a 10 valores) y columnas numéricas."},
        {"id": "regresion", "nombre": "Correlación y regresión", "disponible": len(puras) >= 2,
         "motivo": "Requiere al menos dos columnas numéricas."},
        {"id": "calidad", "nombre": "Control de calidad (cartas y Cp/Cpk)", "disponible": bool(numericas),
         "motivo": "Requiere una columna numérica (idealmente con fecha u orden)."},
    ]
    return {
        "filas": n, "avisos": avisos, "columnas": columnas, "vista_previa": vista,
        "sugerencias": sugerencias, "modulos": modulos,
        "grupos_valores": {c: etiquetas_grupo(df[c])[1] for c in grupos},
    }