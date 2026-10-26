"""Genera los datasets de ejemplo en data/. Ejecutar desde la raíz: python tools/generar_ejemplos.py"""
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
DATA.mkdir(exist_ok=True)
rng = np.random.default_rng(2026)

# --- 1. Control de calidad: volumen de botellas (objetivo 500, specs 495-505) ---
n = 120
idx = np.arange(n)
temp = rng.normal(24, 1.5, n)
turno = np.where(idx < n // 2, "Mañana", "Noche")
vol = 500 + 0.6 * (temp - 24) + np.where(turno == "Noche", -0.8, 0.0) + rng.normal(0, 1.4, n)
vol[70:73] += 6.5   # causa especial: desajuste temporal
vol[100] -= 7.0     # causa especial: dato bajo
pd.DataFrame({
    "fecha": pd.date_range("2026-03-02 06:00", periods=n, freq="30min").strftime("%Y-%m-%d %H:%M"),
    "muestra": idx // 5 + 1,
    "turno": turno,
    "maquina": np.where((idx // 5) % 2 == 0, "A", "B"),
    "volumen_ml": vol.round(2),
    "temperatura_c": temp.round(1),
}).to_csv(DATA / "calidad_botellas.csv", index=False)

# --- 2. Tiempos de servicio de soporte técnico ---
m = 150
agente = rng.choice(["Ana", "Luis", "Marta"], m)
cola = rng.integers(0, 16, m)
tiempo = rng.lognormal(np.log(12), 0.4, m) * (1 + 0.04 * cola) * np.where(agente == "Luis", 1.3, 1.0)
pd.DataFrame({
    "fecha": pd.date_range("2026-04-01 08:00", periods=m, freq="47min").strftime("%Y-%m-%d %H:%M"),
    "agente": agente,
    "tiempo_min": tiempo.round(1),
    "tickets_en_cola": cola,
}).to_csv(DATA / "tiempos_servicio.csv", index=False)

print("Archivos generados en", DATA)