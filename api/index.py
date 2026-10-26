import os
import platform
import sys
import time
from pathlib import Path

T0 = time.time()

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import numpy as np
import openpyxl
import pandas as pd
import scipy

from calidadstat.routers import datos, distribuciones, marcas, simulacion

IMPORT_SECONDS = round(time.time() - T0, 3)

app = FastAPI(
    title="CalidadStat",
    description="Análisis estadístico adaptativo de procesos: descriptiva, control de calidad, "
    "comparación de marcas, simulación, pruebas de hipótesis, regresión y distribuciones.",
)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))

app.include_router(datos.router)
app.include_router(marcas.router)
app.include_router(simulacion.router)
app.include_router(distribuciones.router)


@app.get("/", include_in_schema=False)
def inicio(request: Request):
    return templates.TemplateResponse(request, "index.html", {"titulo": "CalidadStat"})


@app.get("/api/estado")
def estado():
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
        "en_vercel": bool(os.environ.get("VERCEL")),
    }