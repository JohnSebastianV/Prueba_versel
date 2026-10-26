from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from ..services.calidad import analisis_calidad
from ..services.descriptiva import descriptiva, normalidad
from ..services.hipotesis import comparar_grupos, una_muestra
from ..services.interpretacion import interpretar
from ..services.lectura import leer_archivo, limpiar, perfil, serie_numerica, tipo_columna
from ..services.regresion import correlaciones, regresion_simple
from ..services.util import a_float, a_json

router = APIRouter(prefix="/api")

BASE = Path(__file__).resolve().parents[2]
MAX_BYTES = 4 * 1024 * 1024

EJEMPLOS = {
    "calidad_botellas.csv": "Control de calidad: volumen de botellas (120 mediciones, 2 turnos)",
    "tiempos_servicio.csv": "Tiempos de atención de soporte (150 tickets, 3 agentes)",
    "ejemplo_puntoycoma.csv": "Formato Excel colombiano (; y coma decimal)",
}


async def _cargar(archivo: UploadFile):
    contenido = await archivo.read()
    if len(contenido) > MAX_BYTES:
        raise HTTPException(413, "El archivo supera el límite de 4 MB.")
    try:
        df = leer_archivo(archivo.filename or "", contenido)
        return limpiar(df)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/ejemplos")
def listar_ejemplos():
    return [{"archivo": k, "descripcion": v} for k, v in EJEMPLOS.items() if (BASE / "data" / k).exists()]


@router.get("/ejemplo/{nombre}")
def obtener_ejemplo(nombre: str):
    if nombre not in EJEMPLOS or not (BASE / "data" / nombre).exists():
        raise HTTPException(404, "Dataset de ejemplo no encontrado.")
    return Response((BASE / "data" / nombre).read_bytes(), media_type="text/csv")


@router.post("/perfil")
async def post_perfil(archivo: UploadFile = File(...)):
    df, avisos = await _cargar(archivo)
    return a_json(perfil(df, avisos))


@router.post("/analisis")
async def post_analisis(
    archivo: UploadFile = File(...),
    modulos: str = Form("descriptiva"),
    columna: Optional[str] = Form(None),
    grupo: Optional[str] = Form(None),
    orden: Optional[str] = Form(None),
    x: Optional[str] = Form(None),
    y: Optional[str] = Form(None),
    objetivo: Optional[str] = Form(None),
    lsl: Optional[str] = Form(None),
    usl: Optional[str] = Form(None),
    subgrupo: Optional[str] = Form(None),
    contexto: str = Form("general"),
):
    df, _ = await _cargar(archivo)
    mods = {m.strip() for m in modulos.split(",") if m.strip()}
    try:
        obj, li, ls = a_float(objetivo), a_float(lsl), a_float(usl)
        sub = a_float(subgrupo)
        sub = int(sub) if sub is not None else None
        serie = None
        if mods & {"descriptiva", "hipotesis", "grupos", "calidad"}:
            if not columna:
                raise ValueError("Elige la columna de medición.")
            serie = serie_numerica(df, columna)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    res, errores = {"columna": columna}, {}

    def correr(nombre, fn):
        try:
            res[nombre] = fn()
        except ValueError as e:
            errores[nombre] = str(e)

    if "descriptiva" in mods:
        correr("descriptiva", lambda: descriptiva(serie, columna))
    if "hipotesis" in mods and obj is not None:
        def _hip():
            vals = serie.to_numpy()
            nm = normalidad(vals)
            return una_muestra(vals, obj, bool(nm and nm["normal"]))
        correr("hipotesis", _hip)
    if "grupos" in mods and grupo:
        correr("grupos", lambda: comparar_grupos(df, columna, grupo))
    if "regresion" in mods:
        numericas = [c for c in df.columns if tipo_columna(df[c]) == "numerica"]
        if len(numericas) >= 2:
            correr("correlaciones", lambda: correlaciones(df, numericas))
        if x and y:
            correr("regresion", lambda: regresion_simple(df, x, y))
    if "calidad" in mods:
        correr("calidad", lambda: analisis_calidad(df, columna, orden or None, li, ls, obj, sub))

    res["errores"] = errores
    res["interpretacion"] = interpretar(res, contexto)
    return a_json(res)