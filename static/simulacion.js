"use strict";
/* ===== Pestaña «Simulación de equipos» ===== */

const SIM_DEF = [
  { nombre: "Escenario 1", a: { dist: "normal", p: [175, 30] }, b: { dist: "normal", p: [170, 50] } },
  { nombre: "Escenario 2", a: { dist: "gamma", p: [1.2, 150] }, b: { dist: "gamma", p: [0.95, 190] } },
];
const SIM_ETQ = { normal: ["Media μ", "Desviación σ"], gamma: ["Forma α", "Escala β (media = α·β)"] };
const SIM_POR_DEFECTO = { normal: [175, 30], gamma: [1.2, 150] };
let simUltimo = null;

function equipoHTML(id, titulo_, d) {
  const e = SIM_ETQ[d.dist];
  return `<div class="eq" id="${id}"><b>${titulo_}</b>
    <label>Distribución<select class="eq-dist"><option value="normal"${d.dist === "normal" ? " selected" : ""}>Normal</option><option value="gamma"${d.dist === "gamma" ? " selected" : ""}>Gamma</option></select></label>
    <label><span class="l1">${e[0]}</span><input class="eq-p1" type="number" step="any" value="${d.p[0]}"></label>
    <label><span class="l2">${e[1]}</span><input class="eq-p2" type="number" step="any" value="${d.p[1]}"></label></div>`;
}

function simPintarForm() {
  $("sim-form").innerHTML = SIM_DEF.map((e, i) =>
    `<h3>${esc(e.nombre)}</h3><div class="eqs">${equipoHTML(`s${i}a`, "Equipo A", e.a)}${equipoHTML(`s${i}b`, "Equipo B", e.b)}</div>`).join("");
  document.querySelectorAll("#sim-form .eq-dist").forEach((sel) => sel.addEventListener("change", () => {
    const box = sel.closest(".eq"), d = sel.value;
    box.querySelector(".l1").textContent = SIM_ETQ[d][0];
    box.querySelector(".l2").textContent = SIM_ETQ[d][1];
    box.querySelector(".eq-p1").value = SIM_POR_DEFECTO[d][0];
    box.querySelector(".eq-p2").value = SIM_POR_DEFECTO[d][1];
  }));
}

const numONull = (v) => (v === "" ? null : Number(v));
function leerEquipo(id) {
  const el = $(id), dist = el.querySelector(".eq-dist").value;
  const p1 = numONull(el.querySelector(".eq-p1").value), p2 = numONull(el.querySelector(".eq-p2").value);
  return { dist, params: dist === "normal" ? { mu: p1, sigma: p2 } : { alpha: p1, beta: p2 } };
}

$("btn-sim").onclick = async () => {
  const b = $("btn-sim");
  ocupado(b, true, "Simulando…");
  try {
    const r = await api("/api/simulacion", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        n: Math.round(numONull($("sim-n").value) ?? 60),
        semilla: numONull($("sim-semilla").value) === null ? null : Math.round(Number($("sim-semilla").value)),
        escenarios: SIM_DEF.map((e, i) => ({ nombre: e.nombre, a: leerEquipo(`s${i}a`), b: leerEquipo(`s${i}b`) })),
      }),
    });
    simUltimo = r;
    renderSim(r);
    $("btn-sim-csv").hidden = false;
  } catch (e) {
    $("sim-resultados").innerHTML = `<div class="aviso error">${esc(e.message)}</div>`;
  } finally { ocupado(b, false); }
};

$("btn-sim-csv").onclick = () => {
  if (!simUltimo) return;
  const filas = ["escenario,equipo,valor"];
  simUltimo.escenarios.forEach((e) => ["A", "B"].forEach((k) => e[k].datos.forEach((v) => filas.push(`${e.nombre.replace(/,/g, "")},${k},${v}`))));
  const url = URL.createObjectURL(new Blob([filas.join("\n")], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url; a.download = `simulacion_semilla_${simUltimo.semilla}.csv`;
  document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
};

const decAjuste = (rech) => (rech ? '<span class="badge rojo">Se rechaza el ajuste</span>' : '<span class="badge verde">No se rechaza</span>');
const decH0 = (rech) => (rech ? '<span class="badge rojo">Se rechaza H₀</span>' : '<span class="badge verde">No se rechaza H₀</span>');

function renderSim(r) {
  const medidas = [["n", "n", 0], ["Media", "media", 2], ["Mediana", "mediana", 2], ["Desv. estándar", "desviacion", 2], ["Varianza", "varianza", 1],
    ["Mínimo", "minimo", 2], ["Máximo", "maximo", 2], ["Q1", "q1", 2], ["Q3", "q3", 2], ["Coef. de variación (%)", "cv", 1], ["Asimetría", "asimetria", 3], ["Curtosis", "curtosis", 3]];
  const html = [`<div class="aviso info">Semilla usada: <b>${r.semilla}</b> · n = ${r.n} por equipo. Con la misma semilla y los mismos parámetros obtienes exactamente los mismos datos.</div>`];
  const graf = [];

  r.escenarios.forEach((e, i) => {
    const A = e.A, B = e.B, c = e.comparacion, mw = c.mann_whitney;
    const gof = [A, B].flatMap((g) => g.pruebas.map((p) => `<tr><td>${g.nombre}</td><td>${esc(p.prueba)}</td><td>${p.modelo}</td><td>${num(p.estadistico, 4)}</td><td>${p.gl === null ? "—" : p.gl}</td><td>${pv(p.p)}</td><td>${decAjuste(p.rechaza)}</td></tr>`)).join("");
    html.push(`<section class="card"><h2>${esc(e.nombre)}: A ~ ${esc(A.descripcion)} · B ~ ${esc(B.descripcion)}</h2>
      <h3>a) Medidas descriptivas, histogramas y bondad de ajuste</h3>
      <div class="scroll"><table class="tabla"><thead><tr><th>Medida</th><th>Equipo A</th><th>Equipo B</th></tr></thead><tbody>
      ${medidas.map(([t, k, d]) => `<tr><td>${t}</td><td>${num(A.descriptiva[k], d)}</td><td>${num(B.descriptiva[k], d)}</td></tr>`).join("")}</tbody></table></div>
      <div class="graficos"><div id="sh-${i}-a" class="plot alto"></div><div id="sh-${i}-b" class="plot alto"></div></div>
      <div class="scroll"><table class="tabla"><thead><tr><th>Equipo</th><th>Prueba</th><th>Modelo</th><th>Estadístico</th><th>g.l.</th><th>Valor p</th><th>Decisión (α = 0,05)</th></tr></thead><tbody>${gof}</tbody></table></div>
      <p class="peq">H₀: los datos provienen del modelo indicado. Los parámetros del modelo se estimaron con la misma muestra (media y desviación para la Normal; máxima verosimilitud para la Gamma), por lo que los valores p de Kolmogorov-Smirnov son aproximados; en la prueba chi-cuadrado se descontaron los g.l. de los parámetros estimados.</p>
      <h3>b) Comparación de medias (H₀: μA = μB; H₁: μA ≠ μB)</h3>
      <p>Diferencia observada de medias (A − B): <b>${num(c.dif, 3)}</b></p>
      <div class="scroll"><table class="tabla"><thead><tr><th>Método</th><th>Estadístico</th><th>g.l.</th><th>Valor p</th><th>IC 95 % de μA − μB</th><th>Decisión</th></tr></thead><tbody>
      ${c.medias.map((m) => `<tr><td>${esc(m.metodo)}</td><td>${num(m.estadistico, 4)}</td><td>${m.gl === null ? "—" : num(m.gl, 1)}</td><td>${pv(m.p)}</td><td>${num(m.ic[0], 2)} a ${num(m.ic[1], 2)}</td><td>${decH0(m.rechaza)}</td></tr>`).join("")}</tbody></table></div>
      <h3>c) Prueba de Mann-Whitney (Wilcoxon rango-suma)</h3>
      <div class="stats">${tarjeta("Estadístico U", num(mw.U, 1))}${tarjeta("Valor p", pv(mw.p))}${tarjeta("P(A > B)", num(mw.prob_a_mayor * 100, 1) + " %")}${tarjeta("Mediana A / B", `${num(mw.mediana_a, 1)} / ${num(mw.mediana_b, 1)}`)}${tarjeta("Desplazamiento (Hodges-Lehmann)", num(mw.hodges_lehmann, 2))}</div>
      <p>Decisión: ${decH0(mw.rechaza)}</p>
      <div class="aviso ok"><ul class="lista">${e.interpretacion.map((t) => `<li>${esc(t)}</li>`).join("")}</ul></div></section>`);
    graf.push(() => ["a", "b"].forEach((k) => {
      const g = k === "a" ? A : B, h = g.histograma, ancho = h.bordes[1] - h.bordes[0];
      const centros = h.conteos.map((_, j) => (h.bordes[j] + h.bordes[j + 1]) / 2);
      const tr = [{ x: centros, y: h.conteos, type: "bar", width: ancho * 0.95, marker: { color: VERDE }, name: "Frecuencia" },
        { x: g.curvas.x, y: g.curvas.normal, mode: "lines", line: { color: ROJO, width: 2 }, name: "Normal ajustada" }];
      if (g.curvas.gamma) tr.push({ x: g.curvas.x, y: g.curvas.gamma, mode: "lines", line: { color: AZUL, width: 2, dash: "dash" }, name: "Gamma ajustada" });
      plot(`sh-${i}-${k}`, tr, { title: titulo(`Equipo ${g.nombre}: histograma y ajustes`), xaxis: { title: "Tiempo (ms)" }, yaxis: { title: "Frecuencia", rangemode: "tozero" }, legend: { orientation: "h", y: -0.3 }, margin: { t: 40, r: 16, b: 80, l: 56 } });
    }));
  });

  const filasRes = [];
  const nombres = r.escenarios.map((e) => e.nombre);
  r.escenarios[0].comparacion.medias.forEach((m, j) => filasRes.push([m.metodo, ...r.escenarios.map((e) => e.comparacion.medias[j])]));
  filasRes.push(["Mann-Whitney", ...r.escenarios.map((e) => e.comparacion.mann_whitney)]);
  html.push(`<section class="card"><h2>Comparación entre escenarios</h2>
    <div class="scroll"><table class="tabla"><thead><tr><th>Prueba</th>${nombres.map((n) => `<th>${esc(n)}: valor p</th><th>Decisión</th>`).join("")}</tr></thead><tbody>
    ${filasRes.map(([n, ...cols]) => `<tr><td>${esc(n)}</td>${cols.map((c) => `<td>${pv(c.p)}</td><td>${decH0(c.rechaza)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
    <p class="peq">Cambia la semilla (o déjala vacía) para ver cómo varían las conclusiones de una muestra a otra: con n pequeño, el azar puede cambiar la decisión.</p></section>`);

  $("sim-resultados").innerHTML = html.join("");
  graf.forEach((fn) => fn());
}

simPintarForm();