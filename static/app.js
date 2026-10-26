"use strict";

/* ============ utilidades ============ */
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (v, d = 3) => (v === null || v === undefined || Number.isNaN(v) ? "—" : Number(v).toLocaleString("es-CO", { maximumFractionDigits: d }));
const pv = (p) => (p === null || p === undefined ? "—" : p < 0.001 ? "< 0,001" : num(p, 3));
const VERDE = "#0F766E", ROJO = "#B42318", AZUL = "#14213D", NARANJA = "#B45309";
const PALETA = [VERDE, "#2563EB", NARANJA, "#7C3AED", ROJO, "#0891B2", "#65A30D", "#DB2777", "#475569", "#CA8A04"];
const MAX_MB = 4;

let archivo = null;
let perfil = null;

const tarjeta = (t, v, sub = "") =>
  `<div class="stat"><div class="stat-t">${esc(t)}</div><div class="stat-v">${v}</div>${sub ? `<div class="stat-s">${esc(sub)}</div>` : ""}</div>`;
const aviso = (id, tipo, txt) => { $(id).innerHTML = `<div class="aviso ${tipo}">${esc(txt)}</div>`; };

async function api(url, opciones) {
  let r;
  try { r = await fetch(url, opciones); } catch { throw new Error("No se pudo conectar con el servidor."); }
  const texto = await r.text();
  let cuerpo = null;
  try { cuerpo = JSON.parse(texto); } catch { /* respuesta no JSON */ }
  if (!r.ok) {
    if (r.status === 413) throw new Error(`El archivo supera el límite de ${MAX_MB} MB de la plataforma.`);
    if (cuerpo && typeof cuerpo.detail === "string") throw new Error(cuerpo.detail);
    if (r.status === 422) throw new Error("Revisa los datos ingresados: hay campos vacíos o inválidos.");
    throw new Error(`Error ${r.status} del servidor.`);
  }
  return cuerpo;
}

function ocupado(btn, on, texto) {
  if (on) { btn.dataset.txt = btn.textContent; btn.textContent = texto || "Procesando…"; }
  else btn.textContent = btn.dataset.txt || btn.textContent;
  btn.disabled = on;
}

/* ============ gráficos ============ */
const CFG = { responsive: true, displaylogo: false };
function plot(id, trazas, layout = {}) {
  const el = $(id);
  if (!el) return;
  Plotly.newPlot(el, trazas, {
    margin: { t: 40, r: 16, b: 48, l: 56 }, paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "system-ui, sans-serif", color: AZUL }, ...layout,
  }, CFG);
}
const titulo = (t) => ({ text: t, font: { size: 14 } });

/* ============ pestañas ============ */
function mostrarTab(id) {
  document.querySelectorAll(".panel").forEach((p) => { p.hidden = p.id !== "tab-" + id; });
  document.querySelectorAll("#tabs .tab").forEach((b) => {
    const on = b.dataset.tab === id;
    b.classList.toggle("activa", on);
    b.setAttribute("aria-selected", on);
  });
  document.querySelectorAll(`#tab-${id} .plot`).forEach((el) => { if (el.data) Plotly.Plots.resize(el); });
}
document.querySelectorAll("#tabs .tab").forEach((b) => (b.onclick = () => mostrarTab(b.dataset.tab)));
document.querySelectorAll("[data-ir]").forEach((b) => (b.onclick = () => mostrarTab(b.dataset.ir)));

/* ============ carga de archivo ============ */
$("archivo").addEventListener("change", (e) => { if (e.target.files[0]) cargar(e.target.files[0]); });
const zona = $("zona");
["dragenter", "dragover"].forEach((ev) => zona.addEventListener(ev, (e) => { e.preventDefault(); zona.classList.add("sobre"); }));
["dragleave", "drop"].forEach((ev) => zona.addEventListener(ev, (e) => { e.preventDefault(); zona.classList.remove("sobre"); }));
zona.addEventListener("drop", (e) => { if (e.dataTransfer.files[0]) cargar(e.dataTransfer.files[0]); });

async function cargarEjemplos() {
  try {
    const lista = await api("/api/ejemplos");
    $("ejemplos").innerHTML = lista.map((e) => `<button class="btn-ej" data-a="${esc(e.archivo)}">${esc(e.descripcion)}</button>`).join("");
    document.querySelectorAll(".btn-ej").forEach((b) => (b.onclick = async () => {
      try {
        const r = await fetch("/api/ejemplo/" + encodeURIComponent(b.dataset.a));
        if (!r.ok) throw new Error();
        cargar(new File([await r.blob()], b.dataset.a, { type: "text/csv" }));
      } catch { aviso("msg-carga", "error", "No se pudo cargar el ejemplo."); }
    }));
  } catch { /* sin ejemplos */ }
}

function limpiarResultados() {
  $("resultados-analisis").innerHTML = "";
  $("resultados-calidad").innerHTML = "";
  $("bloque-perfil").hidden = true;
  $("bloque-config").hidden = true;
  $("bloque-calidad").hidden = true;
  $("aviso-sin-archivo").hidden = false;
  if (typeof marcasAlLimpiar === "function") marcasAlLimpiar();
}

async function cargar(f) {
  limpiarResultados();
  archivo = null; perfil = null;
  if (f.size > MAX_MB * 1024 * 1024) {
    return aviso("msg-carga", "error", `El archivo pesa ${(f.size / 1048576).toFixed(1)} MB y el máximo es ${MAX_MB} MB.`);
  }
  aviso("msg-carga", "info", "Leyendo el archivo…");
  try {
    const fd = new FormData();
    fd.append("archivo", f);
    perfil = await api("/api/perfil", { method: "POST", body: fd });
    archivo = f;
    aviso("msg-carga", "ok", `Archivo cargado: ${f.name}`);
    renderPerfil(perfil);
  } catch (e) {
    aviso("msg-carga", "error", e.message);
  }
  $("archivo").value = "";
}

const TIPOS = { numerica: "Numérica", indice: "Índice/contador", codigo: "Código / categoría numérica", binaria: "Binaria", categorica: "Categórica", fecha: "Fecha", texto: "Texto", constante: "Constante", vacia: "Vacía" };

function llenar(id, nombres, { vacio = null, valor = null } = {}) {
  const sel = $(id);
  sel.innerHTML = (vacio ? `<option value="">${esc(vacio)}</option>` : "") + nombres.map((n) => `<option value="${esc(n)}">${esc(n)}</option>`).join("");
  if (valor && nombres.includes(valor)) sel.value = valor;
  else if (!vacio && nombres.length) sel.selectedIndex = 0;
  else sel.value = "";
}

function renderPerfil(p) {
  $("perfil-resumen").innerHTML = `<b>${p.filas.toLocaleString("es-CO")}</b> filas · <b>${p.columnas.length}</b> columnas`;
  $("perfil-avisos").innerHTML = p.avisos.map((a) => `<div class="aviso warn">${esc(a)}</div>`).join("");
  $("perfil-columnas").innerHTML =
    `<thead><tr><th>Columna</th><th>Tipo detectado</th><th>Válidos</th><th>Faltantes</th><th>Únicos</th><th>Ejemplo</th></tr></thead><tbody>` +
    p.columnas.map((c) => `<tr><td>${esc(c.nombre)}</td><td><span class="badge">${TIPOS[c.tipo] || c.tipo}</span></td><td>${c.validos}</td><td>${c.faltantes}</td><td>${c.unicos}</td><td>${esc(c.ejemplo)}</td></tr>`).join("") + "</tbody>";
  $("perfil-vista").innerHTML =
    `<thead><tr>${p.vista_previa.columnas.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>` +
    p.vista_previa.filas.map((f) => `<tr>${f.map((v) => `<td>${esc(v)}</td>`).join("")}</tr>`).join("") + "</tbody>";
  $("perfil-modulos").innerHTML = p.modulos.map((m) =>
    `<span class="badge ${m.disponible ? "verde" : ""}" title="${esc(m.disponible ? "Disponible" : m.motivo)}">${m.disponible ? "✔" : "✖"} ${esc(m.nombre)}</span>`).join("");

  const por = (...tipos) => p.columnas.filter((c) => tipos.includes(c.tipo)).map((c) => c.nombre);
  const numericas = por("numerica", "codigo");
  const grupos = p.columnas.filter((c) => ["categorica", "binaria", "codigo"].includes(c.tipo) && c.unicos >= 2 && c.unicos <= 10).map((c) => c.nombre);
  const ordenables = por("fecha", "indice");
  const s = p.sugerencias;
  llenar("columna", numericas, { valor: s.columna });
  llenar("grupo", grupos, { vacio: "(ninguno)", valor: s.grupo });
  llenar("reg-x", numericas, { vacio: "(ninguna)", valor: s.x });
  llenar("reg-y", numericas, { vacio: "(ninguna)", valor: s.y });
  llenar("q-columna", numericas, { valor: s.columna });
  llenar("q-orden", ordenables, { vacio: "(usar orden de las filas)", valor: s.orden });

  $("bloque-perfil").hidden = false;
  $("bloque-config").hidden = numericas.length === 0;
  $("bloque-calidad").hidden = numericas.length === 0;
  $("aviso-sin-archivo").hidden = true;
  if (typeof marcasAlCargar === "function") marcasAlCargar(p);
}
$("columna").addEventListener("change", () => { $("q-columna").value = $("columna").value; });
$("q-columna").addEventListener("change", () => { $("columna").value = $("q-columna").value; });

function formData(extra) {
  const fd = new FormData();
  fd.append("archivo", archivo);
  Object.entries(extra).forEach(([k, v]) => { if (v !== null && v !== undefined && v !== "") fd.append(k, v); });
  return fd;
}

/* ============ pestaña 1: análisis ============ */
$("btn-analizar").onclick = async () => {
  if (!archivo) return;
  const b = $("btn-analizar");
  ocupado(b, true, "Analizando…");
  try {
    const r = await api("/api/analisis", {
      method: "POST",
      body: formData({
        modulos: "descriptiva,hipotesis,grupos,regresion", columna: $("columna").value, contexto: $("contexto").value,
        objetivo: $("objetivo").value, grupo: $("grupo").value, x: $("reg-x").value, y: $("reg-y").value,
      }),
    });
    renderAnalisis(r);
  } catch (e) {
    $("resultados-analisis").innerHTML = `<div class="aviso error">${esc(e.message)}</div>`;
  } finally { ocupado(b, false); }
};

function bloqueErrores(errores) {
  const nombres = { descriptiva: "Descriptiva", hipotesis: "Prueba de hipótesis", grupos: "Comparación de grupos", correlaciones: "Correlaciones", regresion: "Regresión", calidad: "Control de calidad" };
  return Object.entries(errores || {}).map(([k, v]) => `<div class="aviso warn"><b>${nombres[k] || k}:</b> ${esc(v)}</div>`).join("");
}

function renderAnalisis(r) {
  const partes = [];
  if (r.descriptiva) partes.push(secDescriptiva(r.descriptiva));
  if (r.hipotesis) partes.push(secHipotesis(r.hipotesis));
  if (r.grupos) partes.push(secGrupos(r.grupos));
  if (r.correlaciones || r.regresion) partes.push(secRegresion(r.correlaciones, r.regresion));
  partes.push(secInterpretacion(r.interpretacion));
  $("resultados-analisis").innerHTML = bloqueErrores(r.errores) + partes.map((p) => p.html).join("");
  partes.forEach((p) => p.dibujar && p.dibujar());
}

function secDescriptiva(d) {
  const s = d.resumen;
  const items = [
    ["Datos (n)", num(s.n, 0)], ["Media", num(s.media)], ["Mediana", num(s.mediana)], ["Moda", s.moda === null ? "—" : num(s.moda)],
    ["Desv. estándar", num(s.desviacion)], ["Varianza", num(s.varianza)], ["Mínimo", num(s.minimo)], ["Máximo", num(s.maximo)],
    ["Rango", num(s.rango)], ["Q1", num(s.q1)], ["Q3", num(s.q3)], ["IQR", num(s.iqr)],
    ["Coef. de variación", s.cv === null ? "—" : num(s.cv, 1) + " %"], ["Asimetría", num(s.asimetria)], ["Curtosis", num(s.curtosis)], ["Atípicos", num(s.n_atipicos, 0)],
  ];
  const nm = d.normalidad;
  const normTxt = nm
    ? `Shapiro-Wilk: W = ${num(nm.estadistico, 4)}, p = ${pv(nm.p)} → ${nm.normal ? '<span class="badge verde">No se rechaza normalidad</span>' : '<span class="badge rojo">Se rechaza normalidad</span>'}`
    : "No se pudo evaluar la normalidad (datos insuficientes o constantes).";
  const html = `<section class="card"><h2>Estadística descriptiva · ${esc(d.columna)}</h2>
    <div class="stats">${items.map(([t, v]) => tarjeta(t, v)).join("")}</div>
    <p>Intervalo de confianza del 95 % para la media: <b>${num(s.ic95[0])}</b> a <b>${num(s.ic95[1])}</b> · Error estándar: ${num(s.error_estandar)}</p>
    <p>${normTxt}</p>
    <div class="graficos"><div id="p-hist" class="plot"></div><div id="p-box" class="plot"></div><div id="p-qq" class="plot"></div></div></section>`;
  const dibujar = () => {
    const h = d.histograma, ancho = h.bordes[1] - h.bordes[0];
    const centros = h.conteos.map((_, i) => (h.bordes[i] + h.bordes[i + 1]) / 2);
    const trazas = [{ x: centros, y: h.conteos, type: "bar", width: ancho * 0.95, marker: { color: VERDE }, name: "Frecuencia" }];
    if (s.desviacion > 0) {
      const a = h.bordes[0], b = h.bordes[h.bordes.length - 1];
      const xs = Array.from({ length: 80 }, (_, i) => a + ((b - a) * i) / 79);
      trazas.push({ x: xs, y: xs.map((x) => (s.n * ancho * Math.exp(-0.5 * ((x - s.media) / s.desviacion) ** 2)) / (s.desviacion * Math.sqrt(2 * Math.PI))), mode: "lines", name: "Normal teórica", line: { color: ROJO } });
    }
    plot("p-hist", trazas, { title: titulo("Histograma"), xaxis: { title: d.columna }, yaxis: { title: "Frecuencia", rangemode: "tozero" }, legend: { orientation: "h", y: -0.3 }, margin: { t: 40, r: 16, b: 70, l: 56 } });
    const c = d.caja;
    const caja = [{ type: "box", x: [d.columna], q1: [c.q1], median: [c.mediana], q3: [c.q3], lowerfence: [c.bigote_inf], upperfence: [c.bigote_sup], mean: [c.media], boxmean: true, marker: { color: VERDE }, name: "Caja" }];
    if (c.atipicos.length) caja.push({ type: "scatter", mode: "markers", x: c.atipicos.map(() => d.columna), y: c.atipicos, marker: { color: ROJO }, name: "Atípicos" });
    plot("p-box", caja, { title: titulo("Diagrama de caja"), showlegend: false });
    if (d.qq) {
      const q = d.qq, x0 = q.teorico[0], x1 = q.teorico[q.teorico.length - 1];
      plot("p-qq", [
        { x: q.teorico, y: q.muestra, mode: "markers", marker: { color: VERDE, size: 5 }, name: "Datos" },
        { x: [x0, x1], y: [q.intercepto + q.pendiente * x0, q.intercepto + q.pendiente * x1], mode: "lines", line: { color: ROJO }, name: "Referencia" },
      ], { title: titulo("Gráfico Q-Q (normalidad)"), xaxis: { title: "Cuantiles teóricos" }, yaxis: { title: "Cuantiles muestrales" }, showlegend: false });
    }
  };
  return { html, dibujar };
}

function secHipotesis(h) {
  const dec = h.rechaza ? '<span class="badge rojo">Se rechaza H₀</span>' : '<span class="badge verde">No se rechaza H₀</span>';
  return { html: `<section class="card"><h2>Prueba de hipótesis</h2><div class="scroll"><table class="tabla"><tbody>
    <tr><th>Prueba</th><td>${esc(h.prueba)}</td></tr>
    <tr><th>H₀ / H₁</th><td>${esc(h.h0)} &nbsp;/&nbsp; ${esc(h.h1)}</td></tr>
    <tr><th>Estadístico</th><td>${num(h.estadistico, 4)}</td></tr>
    <tr><th>Valor p</th><td>${pv(h.p)}</td></tr>
    <tr><th>Media muestral</th><td>${num(h.media)}${h.ic95 ? ` (IC 95 %: ${num(h.ic95[0])} a ${num(h.ic95[1])})` : ""}</td></tr>
    <tr><th>Decisión (α = 0,05)</th><td>${dec}</td></tr></tbody></table></div></section>` };
}

function secGrupos(g) {
  const dec = g.rechaza ? '<span class="badge rojo">Hay diferencias significativas</span>' : '<span class="badge verde">Sin diferencias significativas</span>';
  const filas = g.grupos.map((e) => `<tr><td>${esc(e.nombre)}</td><td>${e.n}</td><td>${num(e.media)}</td><td>${num(e.mediana)}</td><td>${num(e.desviacion)}</td></tr>`).join("");
  const html = `<section class="card"><h2>Comparación entre grupos · ${esc(g.columna)} por ${esc(g.grupo)}</h2>
    <div class="scroll"><table class="tabla"><thead><tr><th>Grupo</th><th>n</th><th>Media</th><th>Mediana</th><th>Desv. est.</th></tr></thead><tbody>${filas}</tbody></table></div>
    <p><b>${esc(g.prueba)}</b>: estadístico = ${num(g.estadistico, 4)}, p = ${pv(g.p)} → ${dec}</p>
    <p class="peq">${esc(g.justificacion)} (Levene p = ${pv(g.levene_p)})</p>
    <div id="p-grupos" class="plot alto"></div></section>`;
  const dibujar = () => plot("p-grupos", g.grupos.map((e, i) => ({
    type: "box", x: [e.nombre], q1: [e.caja.q1], median: [e.caja.mediana], q3: [e.caja.q3], lowerfence: [e.caja.bigote_inf],
    upperfence: [e.caja.bigote_sup], mean: [e.caja.media], boxmean: true, name: e.nombre, marker: { color: PALETA[i % PALETA.length] },
  })), { title: titulo("Distribución por grupo"), yaxis: { title: g.columna }, showlegend: false });
  return { html, dibujar };
}

function secRegresion(c, r) {
  let html = "";
  if (c) html += `<section class="card"><h2>Matriz de correlación (Pearson)</h2><div id="p-corr" class="plot alto"></div></section>`;
  if (r) {
    const items = [["Pendiente (b)", num(r.pendiente, 4)], ["Intercepto (a)", num(r.intercepto, 4)], ["r de Pearson", num(r.r)], ["R²", num(r.r2)],
      ["Valor p (pendiente)", pv(r.p)], ["IC 95 % pendiente", `${num(r.ic95_pendiente[0], 3)} a ${num(r.ic95_pendiente[1], 3)}`],
      ["Error residual", num(r.error_residual)], ["ρ de Spearman", num(r.spearman)]];
    html += `<section class="card"><h2>Regresión lineal · ${esc(r.y)} = a + b · ${esc(r.x)}</h2>
      <div class="stats">${items.map(([t, v]) => tarjeta(t, v)).join("")}</div>
      <label>Predecir ${esc(r.y)} para ${esc(r.x)} = <input id="pred-x" type="number" step="any" placeholder="Escribe un valor"></label>
      <p id="pred-y"></p>
      <div class="graficos"><div id="p-reg" class="plot alto"></div><div id="p-res" class="plot alto"></div></div></section>`;
  }
  const dibujar = () => {
    if (c) plot("p-corr", [{ z: c.matriz, x: c.columnas, y: c.columnas, type: "heatmap", zmin: -1, zmax: 1, colorscale: "RdBu", reversescale: true, texttemplate: "%{z:.2f}" }], { margin: { t: 20, r: 16, b: 90, l: 110 } });
    if (!r) return;
    plot("p-reg", [
      { x: r.puntos.x, y: r.puntos.y, mode: "markers", marker: { color: VERDE, size: 6, opacity: 0.7 }, name: "Datos" },
      { x: r.recta.x, y: r.recta.y, mode: "lines", line: { color: ROJO, width: 2 }, name: "Recta ajustada" },
    ], { title: titulo("Diagrama de dispersión y recta"), xaxis: { title: r.x }, yaxis: { title: r.y }, legend: { orientation: "h", y: -0.25 }, margin: { t: 40, r: 16, b: 70, l: 56 } });
    plot("p-res", [{ x: r.residuos.ajustados, y: r.residuos.valores, mode: "markers", marker: { color: AZUL, size: 5, opacity: 0.6 } }],
      { title: titulo("Residuos vs. valores ajustados"), xaxis: { title: "Valor ajustado" }, yaxis: { title: "Residuo", zeroline: true }, showlegend: false });
    $("pred-x").addEventListener("input", (e) => {
      const v = parseFloat(e.target.value);
      $("pred-y").innerHTML = Number.isFinite(v) ? `Predicción: ${esc(r.y)} ≈ <b>${num(r.intercepto + r.pendiente * v, 4)}</b>` : "";
    });
  };
  return { html, dibujar };
}

function secInterpretacion(i) {
  const lista = (arr) => (arr.length ? `<ul class="lista">${arr.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>` : "<p class='peq'>Sin observaciones adicionales.</p>");
  return { html: `<section class="card interp"><h2>Interpretación automática</h2><h3>Hallazgos</h3>${lista(i.hallazgos)}<h3>Recomendaciones</h3>${lista(i.recomendaciones)}</section>` };
}

/* ============ pestaña 2: control de calidad ============ */
$("btn-calidad").onclick = async () => {
  if (!archivo) return;
  const b = $("btn-calidad");
  ocupado(b, true, "Calculando…");
  try {
    const r = await api("/api/analisis", {
      method: "POST",
      body: formData({
        modulos: "calidad", columna: $("q-columna").value, orden: $("q-orden").value, lsl: $("q-lsl").value,
        usl: $("q-usl").value, objetivo: $("q-objetivo").value, subgrupo: $("q-subgrupo").value, contexto: "calidad",
      }),
    });
    renderCalidad(r);
  } catch (e) {
    $("resultados-calidad").innerHTML = `<div class="aviso error">${esc(e.message)}</div>`;
  } finally { ocupado(b, false); }
};

function dibujarCarta(id, c, specs) {
  const tr = [{ x: c.x, y: c.valores, text: c.etiquetas, mode: "lines+markers", name: c.nombre, line: { color: AZUL, width: 1.5 }, marker: { size: 5, color: AZUL }, hovertemplate: "%{text}<br>%{y:.3f}<extra></extra>" }];
  if (c.racha8.length) tr.push({ x: c.racha8.map((i) => c.x[i]), y: c.racha8.map((i) => c.valores[i]), mode: "markers", name: "Racha de 8", marker: { size: 9, color: NARANJA, symbol: "diamond" } });
  if (c.fuera.length) tr.push({ x: c.fuera.map((i) => c.x[i]), y: c.fuera.map((i) => c.valores[i]), mode: "markers", name: "Fuera de control", marker: { size: 11, color: ROJO } });
  const x0 = c.x[0], x1 = c.x[c.x.length - 1];
  const linea = (y, n, color, dash) => ({ x: [x0, x1], y: [y, y], mode: "lines", name: `${n} = ${num(y, 3)}`, line: { color, dash, width: 1.5 }, hoverinfo: "skip" });
  tr.push(linea(c.ucl, "LCS", ROJO, "dash"), linea(c.cl, "LC", VERDE, "solid"), linea(c.lcl, "LCI", ROJO, "dash"));
  if (specs) {
    if (specs.usl !== null) tr.push(linea(specs.usl, "USL", NARANJA, "dot"));
    if (specs.lsl !== null) tr.push(linea(specs.lsl, "LSL", NARANJA, "dot"));
  }
  plot(id, tr, { title: titulo(c.nombre), xaxis: { title: "Observación" }, legend: { orientation: "h", y: -0.3 }, margin: { t: 40, r: 16, b: 90, l: 56 } });
}

function renderCalidad(r) {
  if (!r.calidad) { $("resultados-calidad").innerHTML = bloqueErrores(r.errores); return; }
  const q = r.calidad, cap = q.capacidad;
  const items = [["Estabilidad", q.estable ? "Estable" : "Inestable", `${q.principal.fuera.length + q.secundaria.fuera.length} puntos fuera`], ["Media", num(q.media)], ["Desv. estándar total", num(q.desviacion_total)], ["σ dentro (within)", num(q.sigma_within)]];
  if (cap) items.push(["Cp", num(cap.cp, 2)], ["Cpk", num(cap.cpk, 2), cap.clasificacion], ["Pp", num(cap.pp, 2)], ["Ppk", num(cap.ppk, 2)], ["% fuera de espec. (obs.)", num(cap.fuera_obs_pct, 2) + " %"], ["PPM esperado", num(cap.ppm_esperado, 0)]);
  const html = bloqueErrores(r.errores) + q.avisos.map((a) => `<div class="aviso warn">${esc(a)}</div>`).join("") +
    `<section class="card"><h2>Resultados · ${esc(q.columna)} (carta ${esc(q.tipo_carta)}, n = ${q.n})</h2>
    <div class="stats">${items.map(([t, v, s]) => tarjeta(t, v, s)).join("")}</div>
    <div id="c-principal" class="plot alto"></div><div id="c-sec" class="plot alto"></div>
    <div id="c-hist" class="plot alto"></div></section>` + secInterpretacion(r.interpretacion).html;
  $("resultados-calidad").innerHTML = html;

  dibujarCarta("c-principal", q.principal, q.tipo_carta === "I-MR" ? { lsl: q.lsl, usl: q.usl } : null);
  dibujarCarta("c-sec", q.secundaria, null);
  const h = q.histograma, ancho = h.bordes[1] - h.bordes[0];
  const centros = h.conteos.map((_, i) => (h.bordes[i] + h.bordes[i + 1]) / 2);
  const marca = (v, color, texto) => v === null ? null : { shape: { type: "line", x0: v, x1: v, y0: 0, y1: 1, yref: "paper", line: { color, dash: "dash", width: 2 } }, ann: { x: v, y: 1, yref: "paper", text: texto, showarrow: false, yanchor: "bottom", font: { color } } };
  const marcas = [marca(q.lsl, NARANJA, "LSL"), marca(q.usl, NARANJA, "USL"), marca(q.objetivo, VERDE, "Objetivo")].filter(Boolean);
  plot("c-hist", [{ x: centros, y: h.conteos, type: "bar", width: ancho * 0.95, marker: { color: VERDE }, name: "Frecuencia" }], {
    title: titulo("Distribución de las mediciones frente a las especificaciones"), xaxis: { title: q.columna }, yaxis: { title: "Frecuencia" },
    shapes: marcas.map((m) => m.shape), annotations: marcas.map((m) => m.ann), showlegend: false, margin: { t: 60, r: 16, b: 48, l: 56 },
  });
}

/* ============ pestaña 3: distribuciones ============ */
let catalogo = [];
const val = (id) => ($(id).value === "" ? null : Number($(id).value));

async function iniciarDist() {
  try {
    catalogo = await api("/api/distribuciones");
    $("dist").innerHTML = catalogo.map((d) => `<option value="${d.id}">${esc(d.nombre)}</option>`).join("");
    pintarParams();
    pintarModo();
  } catch (e) { $("res-dist").innerHTML = `<div class="aviso error">${esc(e.message)}</div>`; }
}
function pintarParams() {
  const d = catalogo.find((x) => x.id === $("dist").value);
  if (!d) return;
  $("params").innerHTML = d.params.map((p) => `<label>${esc(p.etiqueta)}<input type="number" step="any" data-par="${p.id}" value="${p.defecto}"></label>`).join("");
  $("nota-dist").textContent = d.discreta ? "Variable aleatoria discreta." : "Variable aleatoria continua.";
}
function leerParams() {
  const o = {};
  document.querySelectorAll("#params input").forEach((i) => { o[i.dataset.par] = i.value === "" ? null : Number(i.value); });
  return o;
}
function pintarModo() {
  const m = $("modo").value;
  document.querySelectorAll(".campo-x").forEach((e) => (e.hidden = !["menor", "mayor", "igual"].includes(m)));
  document.querySelectorAll(".campo-ab").forEach((e) => (e.hidden = m !== "entre"));
  document.querySelectorAll(".campo-prob").forEach((e) => (e.hidden = m !== "percentil"));
}
$("dist").addEventListener("change", pintarParams);
$("modo").addEventListener("change", pintarModo);

$("btn-dist").onclick = async () => {
  const b = $("btn-dist");
  ocupado(b, true, "Calculando…");
  try {
    const r = await api("/api/distribuciones/calcular", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dist: $("dist").value, params: leerParams(), modo: $("modo").value, x: val("dist-x"), a: val("dist-a"), b: val("dist-b"), prob: val("dist-prob") }),
    });
    $("res-dist").innerHTML = `<section class="card"><h2>Resultado</h2>
      <div class="stats">${tarjeta(r.etiqueta, num(r.valor, 6))}${tarjeta("Valor esperado E[X]", num(r.media, 4))}${tarjeta("Varianza", num(r.varianza, 4))}${tarjeta("Desv. estándar", num(r.desviacion, 4))}</div>
      <div id="g-dist" class="plot alto"></div></section>`;
    const g = r.grafico;
    if (r.discreta) {
      plot("g-dist", [{ x: g.x, y: g.y, type: "bar", marker: { color: g.region.map((v) => (v ? VERDE : "#CBD5E1")) } }],
        { title: titulo("Función de masa de probabilidad"), xaxis: { title: "x", dtick: g.x.length > 25 ? undefined : 1 }, yaxis: { title: "P(X = x)" }, showlegend: false });
    } else {
      plot("g-dist", [
        { x: g.x, y: g.y, mode: "lines", line: { color: AZUL, width: 2 }, name: "Densidad" },
        { x: g.region_x, y: g.region_y, mode: "lines", fill: "tozeroy", line: { color: VERDE }, fillcolor: "rgba(15,118,110,0.35)", name: "Región" },
      ], { title: titulo("Función de densidad"), xaxis: { title: "x" }, yaxis: { title: "f(x)" }, showlegend: false });
    }
  } catch (e) { $("res-dist").innerHTML = `<div class="aviso error">${esc(e.message)}</div>`; }
  finally { ocupado(b, false); }
};

$("btn-muestral").onclick = async () => {
  const b = $("btn-muestral");
  ocupado(b, true, "Simulando…");
  try {
    const r = await api("/api/distribuciones/muestral", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dist: $("dist").value, params: leerParams(), n: Math.round(val("m-n") ?? 30), repeticiones: Math.round(val("m-rep") ?? 2000) }),
    });
    $("res-muestral").innerHTML = `<section class="card"><h2>Distribución muestral de la media (n = ${r.n}, ${r.repeticiones} muestras)</h2>
      <div class="stats">${tarjeta("Media teórica μ", num(r.mu, 4))}${tarjeta("Media de las medias", num(r.media_medias, 4))}${tarjeta("Error estándar teórico σ/√n", num(r.error_estandar, 4))}${tarjeta("Desv. de las medias (simulada)", num(r.desv_medias, 4))}</div>
      <p class="peq">La curva roja es la normal que predice el Teorema Central del Límite; si n es grande, el histograma se parece a ella aunque la población no sea normal.</p>
      <div id="g-muestral" class="plot alto"></div></section>`;
    plot("g-muestral", [
      { x: r.centros, y: r.densidad, type: "bar", width: r.ancho * 0.95, marker: { color: VERDE }, name: "Medias simuladas" },
      { x: r.curva.x, y: r.curva.y, mode: "lines", line: { color: ROJO, width: 2 }, name: "Normal teórica" },
    ], { title: titulo("Histograma de las medias muestrales"), xaxis: { title: "Media muestral" }, yaxis: { title: "Densidad" }, legend: { orientation: "h", y: -0.25 }, margin: { t: 40, r: 16, b: 70, l: 56 } });
  } catch (e) { $("res-muestral").innerHTML = `<div class="aviso error">${esc(e.message)}</div>`; }
  finally { ocupado(b, false); }
};

/* ============ inicio ============ */
cargarEjemplos();
iniciarDist();