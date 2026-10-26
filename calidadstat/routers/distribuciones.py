from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import distribuciones as svc
from ..services.util import a_json

router = APIRouter(prefix="/api/distribuciones")


class CalculoReq(BaseModel):
    dist: str
    params: dict[str, Optional[float]]
    modo: str = "menor"
    x: Optional[float] = None
    a: Optional[float] = None
    b: Optional[float] = None
    prob: Optional[float] = None


class MuestralReq(BaseModel):
    dist: str
    params: dict[str, Optional[float]]
    n: int = 30
    repeticiones: int = 2000


@router.get("")
def catalogo():
    return svc.catalogo()


@router.post("/calcular")
def calcular(req: CalculoReq):
    try:
        return a_json(svc.calcular(req.dist, req.params, req.modo, req.x, req.a, req.b, req.prob))
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/muestral")
def muestral(req: MuestralReq):
    try:
        return a_json(svc.muestral(req.dist, req.params, req.n, req.repeticiones))
    except ValueError as e:
        raise HTTPException(400, str(e)) from e