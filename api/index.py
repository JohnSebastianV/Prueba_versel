import io
import os
import platform
import sys
import time
from pathlib import Path

T0 = time.time()

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import numpy as np
import openpyxl
import pandas as pd
import scipy
from scipy import stats

IMPORT_SECONDS = round(time.time() - T0, 3)
ARRANQUE = time.time()
PETICIONES = {"total": 0}

# Rutas relativas a este archivo (no al directorio de trabajo)
BASE = Path(__file__).resolve().parent.parent

app = FastAPI(title="Prueba de despliegue")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))

MAX_BYTES = 4 * 1024 * 1024


def a_numerico(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte columnas de texto como '500,3' en numeros cuando es posible."""
    for col in df.columns:
        if df[col].dtype == object:
            convertida = pd.to_numeric(
                df[col].astype(str).str.replace(",", ".", regex=False),
                errors="coerce",
            )
            if convertida.notna().mean() > 0.9:
                df[col] = convertida
    return df


def leer_archivo(nombre: str, contenido: bytes) -> pd.DataFrame:
    n = nombre.lower()
    if n.endswith(".csv"):
        texto = contenido.decode("utf-8-sig", errors="replace")
        # sep=None detecta coma o punto y coma automaticamente
        df = pd.read_csv(io.StringIO(texto), sep=None, engine="python")
    elif n.endswith((".xlsx", ".xlsm")):
        df = pd.read_excel(io.BytesIO(contenido), engine="openpyxl")
    else:
        raise HTTPException(400, "Formato no soportado. Usa .csv o .xlsx")
    return a_numerico(df)


def elegir_columna(df: pd.DataFrame) -> str:
    """Elige la columna numerica a analizar, descartando contadores/IDs
    (columnas enteras que nunca disminuyen, como 'muestra')."""
    numericas = df.select_dtypes(include="number").columns.tolist()
    candidatas = [
        c for c in numericas
        if not (pd.api.types.is_integer_dtype(df[c]) and df[c].is_monotonic_increasing)
    ]
    return (candidatas or numericas)[0]


def analizar(df: pd.DataFrame) -> dict:
    numericas = df.select_dtypes(include="number").columns.tolist()
    if not numericas:
        raise HTTPException(400, "El archivo no tiene columnas numericas.")
    col = elegir_columna(df)
    s = df[col].dropna()
    if len(s) < 3:
        raise HTTPException(400, "Hay muy pocos datos para analizar.")
    muestra = s.sample(5000, random_state=1) if len(s) > 5000 else s
    w, p = stats.shapiro(muestra)
    conteos, bordes = np.histogram(s, bins="auto")
    return {
        "filas": int(len(df)),
        "columnas": df.columns.tolist(),
        "columna_analizada": col,
        "n": int(len(s)),
        "media": float(s.mean()),
        "mediana": float(s.median()),
        "desviacion": float(s.std()),
        "varianza": float(s.var()),
        "minimo": float(s.min()),
        "maximo": float(s.max()),
        "shapiro_p": float(p),
        "histograma": {
            "conteos": conteos.tolist(),
            "bordes": [float(b) for b in bordes],
        },
    }


@app.get("/")
def inicio(request: Request):
    PETICIONES["total"] += 1
    return templates.TemplateResponse(request, "index.html", {"titulo": "Prueba de despliegue"})


@app.get("/api/estado")
def estado():
    PETICIONES["total"] += 1
    # Prueba de escritura en /tmp (lo unico escribible en Vercel)
    try:
        ruta = Path("/tmp") / "prueba.txt"
        ruta.write_text("ok")
        tmp_ok = ruta.read_text() == "ok"
    except Exception as e:  # noqa: BLE001
        tmp_ok = f"error: {e}"
    return {
        "python": sys.version.split()[0],
        "plataforma": platform.platform(),
        "versiones": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "openpyxl": openpyxl.__version__,
        },
        "segundos_importando_librerias": IMPORT_SECONDS,
        "segundos_desde_arranque": round(time.time() - ARRANQUE, 1),
        "peticiones_desde_arranque": PETICIONES["total"],
        "en_vercel": bool(os.environ.get("VERCEL")),
        "existe_data": (BASE / "data").exists(),
        "existe_templates": (BASE / "templates").exists(),
        "existe_static": (BASE / "static").exists(),
        "escritura_tmp": tmp_ok,
    }


@app.get("/api/datos-ejemplo/{nombre}")
def datos_ejemplo(nombre: str):
    PETICIONES["total"] += 1
    if nombre not in {"ejemplo.csv", "ejemplo_puntoycoma.csv"}:
        raise HTTPException(404, "Dataset no encontrado")
    contenido = (BASE / "data" / nombre).read_bytes()
    return analizar(leer_archivo(nombre, contenido))


@app.post("/api/analizar")
async def analizar_archivo(archivo: UploadFile = File(...)):
    PETICIONES["total"] += 1
    contenido = await archivo.read()
    if len(contenido) > MAX_BYTES:
        raise HTTPException(413, "El archivo supera 4 MB.")
    return analizar(leer_archivo(archivo.filename or "", contenido))