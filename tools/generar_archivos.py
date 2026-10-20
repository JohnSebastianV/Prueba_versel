import numpy as np
import pandas as pd

rng = np.random.default_rng(1)


def generar(nombre, filas):
    idx = np.arange(filas)
    df = pd.DataFrame({
        "fecha": pd.date_range("2026-01-01", periods=filas, freq="min"),
        "muestra": idx // 5 + 1,
        "turno": np.where(idx % 2 == 0, "Manana", "Noche"),
        "volumen_ml": rng.normal(500, 2, filas).round(3),
    })
    if nombre.endswith(".xlsx"):
        df.to_excel(nombre, index=False)
    else:
        df.to_csv(nombre, index=False)


generar("grande_aprox_3_5MB.csv", 85_000)   # debe PASAR
generar("grande_aprox_5MB.csv", 130_000)    # debe FALLAR con 413
generar("pequeno.xlsx", 500)                # prueba de Excel
print("Archivos generados. Revisa sus tamaños con 'ls -lh'.")