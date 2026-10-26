from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.simulacion import simular
from ..services.util import a_json

router = APIRouter(prefix="/api")


class Equipo(BaseModel):
    dist: str = "normal"
    params: dict[str, Optional[float]]


class Escenario(BaseModel):
    nombre: str = "Escenario"
    a: Equipo
    b: Equipo


class SimulacionReq(BaseModel):
    n: int = 60
    semilla: Optional[int] = None
    escenarios: list[Escenario]


@router.post("/simulacion")
def post_simulacion(req: SimulacionReq):
    try:
        return a_json(simular([e.model_dump() for e in req.escenarios], req.n, req.semilla))
    except ValueError as e:
        raise HTTPException(400, str(e)) from e