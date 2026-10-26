"""Interpretación automática en español a partir de los resultados."""


def f(v, d=2):
    return "—" if v is None else f"{v:.{d}f}".replace(".", ",")


def fp(p):
    return "—" if p is None else ("< 0,001" if p < 0.001 else f(p, 3))


def interpretar(res, contexto="general"):
    h, r = [], []

    d = res.get("descriptiva")
    if d:
        s, col = d["resumen"], d["columna"]
        h.append(f"«{col}» tiene {s['n']} datos válidos: media {f(s['media'])}, mediana {f(s['mediana'])} "
                 f"y desviación estándar {f(s['desviacion'])}.")
        if s["cv"] is not None:
            nivel = "baja" if s["cv"] < 10 else "moderada" if s["cv"] < 30 else "alta"
            h.append(f"El coeficiente de variación es {f(s['cv'], 1)} %: variabilidad relativa {nivel}.")
        a = s["asimetria"]
        if a is not None:
            if abs(a) < 0.5:
                h.append("La distribución es aproximadamente simétrica.")
            elif a > 0:
                h.append("La distribución tiene sesgo positivo (cola larga a la derecha): la media tiende a superar a la mediana.")
                if contexto == "tiempos":
                    r.append("En tiempos con sesgo positivo, reporta la mediana o percentiles (p. ej. P90) como valor típico, no solo la media.")
            else:
                h.append("La distribución tiene sesgo negativo (cola larga a la izquierda).")
        nm = d.get("normalidad")
        if nm:
            if nm["normal"]:
                h.append(f"Shapiro-Wilk (p = {fp(nm['p'])}): no se rechaza la normalidad; los métodos paramétricos son razonables.")
            else:
                h.append(f"Shapiro-Wilk (p = {fp(nm['p'])}): se rechaza la normalidad al 5 %; conviene usar métodos no paramétricos o transformar los datos.")
        if s["n_atipicos"]:
            h.append(f"Se detectaron {s['n_atipicos']} valores atípicos (criterio 1,5 × IQR).")
            r.append("Revisa los valores atípicos: pueden ser errores de captura o eventos especiales que conviene investigar.")
        if s["n"] < 30:
            r.append("Con menos de 30 datos los resultados son poco estables; recolecta más mediciones si es posible.")

    t = res.get("hipotesis")
    if t:
        if t["rechaza"]:
            h.append(f"{t['prueba']}: p = {fp(t['p'])} < 0,05, se rechaza H₀ ({t['h0']}). La media muestral ({f(t['media'])}) "
                     f"difiere de forma estadísticamente significativa de {f(t['mu0'])}.")
            r.append("La media se aparta del valor objetivo: revisa el centrado o ajuste del proceso.")
        else:
            h.append(f"{t['prueba']}: p = {fp(t['p'])} ≥ 0,05, no se rechaza H₀ ({t['h0']}). No hay evidencia de que la media difiera de {f(t['mu0'])}.")

    g = res.get("grupos")
    if g:
        mayor = max(g["grupos"], key=lambda e: e["media"])
        menor = min(g["grupos"], key=lambda e: e["media"])
        if g["rechaza"]:
            h.append(f"{g['prueba']} (p = {fp(g['p'])}): hay diferencias significativas entre los grupos de «{g['grupo']}». "
                     f"Mayor media: {mayor['nombre']} ({f(mayor['media'])}); menor: {menor['nombre']} ({f(menor['media'])}).")
            r.append(f"Investiga qué hace distinto al grupo «{mayor['nombre']}» frente a «{menor['nombre']}» (turno, máquina, operario, proveedor) y estandariza el método.")
        else:
            h.append(f"{g['prueba']} (p = {fp(g['p'])}): no hay evidencia de diferencias entre los grupos de «{g['grupo']}».")
        if g["descartados"]:
            h.append(f"Se excluyeron {g['descartados']} grupos con menos de 3 datos.")

    c = res.get("correlaciones")
    if c and c["principales"]:
        p = c["principales"][0]
        h.append(f"La correlación lineal más fuerte es entre «{p['a']}» y «{p['b']}» (r = {f(p['r'])}).")

    rg = res.get("regresion")
    if rg:
        fuerza = "débil" if abs(rg["r"]) < 0.3 else "moderada" if abs(rg["r"]) < 0.7 else "fuerte"
        sentido = "positiva" if rg["r"] > 0 else "negativa"
        h.append(f"Regresión de «{rg['y']}» sobre «{rg['x']}»: relación {fuerza} y {sentido} (r = {f(rg['r'])}, R² = {f(rg['r2'])}). "
                 f"Por cada unidad que aumenta «{rg['x']}», «{rg['y']}» cambia en promedio {f(rg['pendiente'], 3)}.")
        if rg["p"] < 0.05:
            h.append(f"La pendiente es significativa (p = {fp(rg['p'])}).")
        else:
            h.append(f"La pendiente no es significativa (p = {fp(rg['p'])}): no hay evidencia de relación lineal.")
        nr = rg.get("normalidad_residuos")
        if nr and not nr["normal"]:
            r.append("Los residuos no parecen normales: interpreta los intervalos y valores p de la regresión con cautela.")
        r.append("Recuerda que una correlación o regresión no demuestra causalidad.")

    q = res.get("calidad")
    if q:
        nf = len(q["principal"]["fuera"]) + len(q["secundaria"]["fuera"])
        if nf:
            h.append(f"La carta {q['tipo_carta']} muestra {nf} punto(s) fuera de los límites de control: el proceso no es estable.")
            r.append("Investiga las causas especiales de los puntos fuera de control (cambio de turno, material, ajuste de máquina) antes de evaluar la capacidad.")
        else:
            h.append(f"La carta {q['tipo_carta']} no muestra puntos fuera de los límites de control.")
        if q["principal"]["racha8"]:
            h.append("Hay una racha de 8 o más puntos seguidos al mismo lado de la línea central: posible desplazamiento de la media.")
        cap = q["capacidad"]
        if cap:
            h.append(f"Índices de capacidad: Cpk = {f(cap['cpk'])}"
                     + (f", Cp = {f(cap['cp'])}" if cap["cp"] is not None else "")
                     + f" → proceso «{cap['clasificacion'].lower()}». Se observa {f(cap['fuera_obs_pct'], 1)} % de datos fuera de especificación "
                     f"y se esperan unos {f(cap['ppm_esperado'], 0)} PPM.")
            if cap["clasificacion"] == "No capaz":
                r.append("Cpk < 1,00: reduce la variabilidad y/o centra el proceso para cumplir las especificaciones.")
            elif cap["clasificacion"] == "Marginalmente capaz":
                r.append("Cpk entre 1,00 y 1,33: el proceso cumple con poco margen; se recomienda mejorarlo.")
            if cap["descentrado"]:
                r.append("Cp es bastante mayor que Cpk: el proceso está descentrado; ajustar la media hacia el valor objetivo mejoraría la capacidad.")
        else:
            r.append("Escribe los límites de especificación (LSL/USL) para calcular Cp y Cpk.")
    return {"hallazgos": h, "recomendaciones": r}