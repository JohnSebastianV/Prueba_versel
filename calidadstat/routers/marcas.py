import json
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..services.marcas import analizar
from ..services.util import a_float, a_json
from .datos import _cargar

router = APIRouter(prefix="/api")


@router.post("/marcas")
async def post_marcas(
    archivo: UploadFile = File(...),
    grupo: str = Form(...),
    var_menor: Optional[str] = Form(None),
    limite: Optional[str] = Form(None),
    limite2: Optional[str] = Form(None),
    var_bil: Optional[str] = Form(None),
    objetivo: Optional[str] = Form(None),
    tol: Optional[str] = Form(None),
    extras: Optional[str] = Form(None),
    conf: str = Form("0.95"),
    sel: Optional[str] = Form(None),
    g1: Optional[str] = Form(None),
    g2: Optional[str] = Form(None),
    p0: Optional[str] = Form("0.8"),
    alt: str = Form("distinto"),
):
    df, _ = await _cargar(archivo)
    try:
        lista = []
        for e in json.loads(extras) if extras else []:
            if e.get("dir") not in ("menor", "mayor"):
                raise ValueError("Sentido no válido en una variable adicional.")
            lista.append((str(e["col"]), e["dir"]))
        res = analizar(
            df, grupo, var_menor or None, a_float(limite), a_float(limite2), var_bil or None,
            a_float(objetivo), a_float(tol), lista, a_float(conf), sel or None, g1 or None, g2 or None,
            a_float(p0), alt,
        )
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        raise HTTPException(400, str(e) if isinstance(e, ValueError) else "Parámetros inválidos.") from e
    return a_json(res)