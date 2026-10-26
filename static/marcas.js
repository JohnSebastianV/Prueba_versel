"use strict";
/* ===== Pestaña «Comparación de marcas» (usa archivo, perfil, $, esc, num, pv, plot... de app.js) ===== */

const RX = {
  menor: /ppm|emisi|contamin|defect|falla|error|queja/i,
  bil: /potenc|peso|volumen|longitud|diametro|diámetro|medida/i,
  extra: /repar|falla|defect|queja|error/i,
};
const pick = (lista, rx) => lista.find((n) => rx.test(n)) || lista[0] || null;

function marcasAlLimpiar() {
  $("m-resultados").innerHTML = "";
  $("m-config").hidden = true;
  $("m-sin-archivo").hidden = false;
}

function marcasAlCargar(p) {
  $("m-resultados").innerHTML = "";
  const grupos = Object.keys(p.grupos_valores || {});
  const hay = grupos.length > 0 && p.columnas.some((c) => ["numerica", "codigo"].includes(c.tipo));
  $("m-config").hidden = !hay;
  $("m-sin-archivo").hidden = true;
  if (!hay) {
    $("m-resultados").innerHTML = '<div class="aviso warn">Este archivo no tiene una columna de grupo (2 a 10 valores distintos) junto con columnas numéricas.</div>';
    return;
  }
  llenar("m-grupo", grupos, { valor: pick(grupos, /marca|grupo|turno|maquina|máquina|equipo|proveedor|agente/i) });
  marcasActualizar();
}

function marcasActualizar() {
  if (!perfil) return;
  const g = $("m-grupo").value;
  const cuant = perfil.columnas.filter((c) => ["numerica", "codigo"].includes(c.tipo) && c.nombre !== g).map((c) => c.nombre);
  llenar("m-var-menor", cuant, { vacio: "(ninguna)", valor: cuant.find((n) => RX.menor.test(n)) });
  llenar("m-var-bil", cuant, { vacio: "(ninguna)", valor: cuant.find((n) => RX.bil.test(n)) });
  const vals = perfil.grupos_valores[g] || [];
  llenar("m-sel", vals, { vacio: "(el de mejor desempeño)" });
  llenar("m-g1", vals, { valor: vals[0] });
  llenar("m-g2", vals, { valor: vals[1] });
  marcasExtras();
}

function marcasExtras() {
  const g = $("m-grupo").value, a = $("m-var-menor").value, b = $("m-var-bil").value;
  const cols = perfil.columnas.filter((c) => ["numerica", "codigo"].includes(c.tipo) && ![g, a, b].includes(c.nombre)).map((c) => c.nombre);
  $("m-extras").innerHTML = cols.length
    ? cols.map((n) => `<div class="extra" data-col="${esc(n)}"><label class="chk"><input type="checkbox" ${RX.extra.test(n) ? "checked" : ""}> ${esc(n)}</label>
        <select><option value="menor">menor es mejor</option><option value="mayor">mayor es mejor</option></select></div>`).join("")
    : '<p class="peq">No hay otras variables numéricas.</p>';
}
["m-grupo", "m-var-menor", "m-var-bil"].forEach((id) => $(id).addEventListener("change", () => (id === "m-grupo" ? marcasActualizar() : marcasExtras())));

$("btn-preset").onclick = () => {
  $("m-lim").value = "400"; $("m-lim2").value = "1000"; $("m-obj").value = "2.7"; $("m-tol").value = "0.22"; $("m-p0").value = "0.8";
  const vals = perfil && perfil.grupos_valores[$("m-grupo").value] || [];
  if (vals.includes("3")) $("m-g1").value = "3";
  if (vals.includes("4")) $("m-g2").value = "4";
};

$("btn-marcas").onclick = async () => {
  if (!archivo) return;
  const b = $("btn-marcas");
  ocupado(b, true, "Analizando…");
  const extras = [...document.querySelectorAll("#m-extras .extra")].filter((r) => r.querySelector("input").checked)
    .map((r) => ({ col: r.dataset.col, dir: r.querySelector("select").value }));
  try {
    const r = await api("/api/marcas", {
      method: "POST",
      body: formData({
        grupo: $("m-grupo").value, var_menor: $("m-var-menor").value, limite: $("m-lim").value, limite2: $("m-lim2").value,
        var_bil: $("m-var-bil").value, objetivo: $("m-obj").value, tol: $("m-tol").value, extras: JSON.stringify(extras),
        conf: $("m-conf").value, sel: $("m-sel").value, g1: $("m-g1").value, g2: $("m-g2").value, p0: $("m-p0").value, alt: $("m-alt").value,
      }),
    });
    renderMarcas(r);
  } catch (e) {
    $("m-resultados").innerHTML = `<div class="aviso error">${esc(e.message)}</div>`;
  } finally { ocupado(b, false); }
};

const etq = (col, g) => (/^-?\d+(\.\d+)?$/.test(g) ? `${col.charAt(0).toUpperCase() + col.slice(1)} ${g}` : g);
const parrafos = (arr) => arr.map((t) => `<p>${esc(t)}</p>`).join("");
const pct = (v) => (v === null || v === undefined ? "—" : num(v, 1) + " %");
const dec = (rech) => (rech ? '<span class="badge rojo">Se rechaza H₀</span>' : '<span class="badge verde">No se rechaza H₀</span>');

function renderMarcas(r) {
  const gc = r.grupo_col, E = (g) => etq(gc, g);
  const partes = [];
  const nomSec = { a: "a) Cajas", b: "b) Especificación", c: "c) Desempeño global", d: "d) Intervalos de confianza", e: "e) Variabilidad", f: "f) Proporción" };
  const avisos = r.avisos.map((a) => `<div class="aviso warn">${esc(a)}</div>`).join("") +
    Object.entries(r.errores || {}).map(([k, v]) => `<div class="aviso warn"><b>${nomSec[k] || k}:</b> ${esc(v)}</div>`).join("");

  if (r.a) {
    const a = r.a;
    partes.push({ html: `<section class="card"><h2>a) Diagrama de cajas · ${esc(a.columna)} por ${esc(gc)}</h2>
      <div id="m-box" class="plot alto"></div>
      <div class="scroll"><table class="tabla"><thead><tr><th>${esc(gc)}</th><th>n</th><th>Media</th><th>Mediana</th><th>Desv. est.</th><th>IQR</th><th>Mín.</th><th>Máx.</th>
      ${a.limite !== null ? `<th>% ≤ ${num(a.limite, 4)}</th>` : ""}${a.limite2 !== null ? `<th>% ≤ ${num(a.limite2, 4)}</th>` : ""}</tr></thead><tbody>
      ${a.tabla.map((t) => `<tr${t.grupo === a.mejor ? ' class="mejor"' : ""}><td>${esc(E(t.grupo))}</td><td>${t.n}</td><td>${num(t.media, 2)}</td><td>${num(t.mediana, 2)}</td><td>${num(t.desviacion, 2)}</td><td>${num(t.iqr, 2)}</td><td>${num(t.minimo, 2)}</td><td>${num(t.maximo, 2)}</td>
      ${a.limite !== null ? `<td>${pct(t.pct_limite)}</td>` : ""}${a.limite2 !== null ? `<td>${pct(t.pct_norma)}</td>` : ""}</tr>`).join("")}</tbody></table></div>
      <div class="aviso ok">${parrafos(a.texto)}</div></section>`,
      dibujar: () => {
        const tr = a.tabla.map((t, i) => ({ type: "box", x: [E(t.grupo)], q1: [t.caja.q1], median: [t.caja.mediana], q3: [t.caja.q3], lowerfence: [t.caja.bigote_inf],
          upperfence: [t.caja.bigote_sup], mean: [t.caja.media], boxmean: true, name: E(t.grupo), marker: { color: PALETA[i % PALETA.length] } }));
        a.tabla.forEach((t) => { if (t.caja.atipicos.length) tr.push({ type: "scatter", mode: "markers", x: t.caja.atipicos.map(() => E(t.grupo)), y: t.caja.atipicos, marker: { color: ROJO, size: 4 }, showlegend: false, hoverinfo: "y" }); });
        const sh = [], an = [];
        [[a.limite, "Límite seguro", NARANJA], [a.limite2, "Límite norma", ROJO]].forEach(([v, n, c]) => {
          if (v !== null) { sh.push({ type: "line", xref: "paper", x0: 0, x1: 1, y0: v, y1: v, line: { color: c, dash: "dash", width: 2 } }); an.push({ xref: "paper", x: 1, y: v, text: `${n} = ${num(v, 4)}`, showarrow: false, xanchor: "right", yanchor: "bottom", font: { color: c } }); }
        });
        plot("m-box", tr, { title: titulo(`${a.columna} por ${gc}`), yaxis: { title: a.columna }, showlegend: false, shapes: sh, annotations: an });
      } });
  }

  if (r.b) {
    const b = r.b;
    partes.push({ html: `<section class="card"><h2>b) Cumplimiento de la especificación · ${esc(b.columna)}</h2>
      <p class="peq">Especificación: ${num(b.objetivo, 4)} ± ${num(b.tolerancia, 4)} → [${num(b.lsl, 4)} ; ${num(b.usl, 4)}]</p>
      <div id="m-espec" class="plot"></div>
      <div class="scroll"><table class="tabla"><thead><tr><th>${esc(gc)}</th><th>n</th><th>Media</th><th>Desv. est.</th><th>Media − objetivo</th><th>% dentro</th><th>% bajo LSL</th><th>% sobre USL</th><th>Cp</th><th>Cpk</th><th>Cpm</th></tr></thead><tbody>
      ${b.tabla.map((t) => `<tr${t.grupo === b.mejor ? ' class="mejor"' : ""}><td>${esc(E(t.grupo))}</td><td>${t.n}</td><td>${num(t.media, 3)}</td><td>${num(t.desviacion, 3)}</td><td>${num(t.desv_objetivo, 3)}</td><td>${pct(t.pct_cumple)}</td><td>${pct(t.pct_bajo)}</td><td>${pct(t.pct_sobre)}</td><td>${num(t.cp, 2)}</td><td>${num(t.cpk, 2)}</td><td>${num(t.cpm, 2)}</td></tr>`).join("")}</tbody></table></div>
      <div class="aviso ok">${parrafos(b.texto)}</div></section>`,
      dibujar: () => {
        const x = b.tabla.map((t) => E(t.grupo));
        plot("m-espec", [
          { x, y: b.tabla.map((t) => t.pct_bajo), type: "bar", name: "Bajo LSL", marker: { color: NARANJA } },
          { x, y: b.tabla.map((t) => t.pct_cumple), type: "bar", name: "Dentro de especificación", marker: { color: VERDE } },
          { x, y: b.tabla.map((t) => t.pct_sobre), type: "bar", name: "Sobre USL", marker: { color: ROJO } },
        ], { barmode: "stack", title: titulo("Distribución del cumplimiento (%)"), yaxis: { title: "%", range: [0, 100] }, legend: { orientation: "h", y: -0.2 } });
      } });
  }

  if (r.c) {
    const c = r.c;
    const color = (rk, n) => { const t = n > 1 ? (rk - 1) / (n - 1) : 0; return `rgba(${Math.round(15 + t * 165)},${Math.round(118 - t * 80)},${Math.round(110 - t * 70)},0.18)`; };
    const n = r.grupos.length;
    partes.push({ html: `<section class="card"><h2>c) Desempeño global por criterios</h2>
      <p class="peq">Entre paréntesis, el puesto en cada criterio (1 = mejor). Gana la menor suma de puestos.</p>
      <div class="scroll"><table class="tabla"><thead><tr><th>${esc(gc)}</th>${c.criterios.map((k) => `<th>${esc(k.nombre)}<br><span class="peq">${k.sentido === "menor" ? "↓ menor es mejor" : "↑ mayor es mejor"}</span></th>`).join("")}<th>Suma de puestos</th></tr></thead><tbody>
      ${c.tabla.map((t) => `<tr${t.grupo === c.mejor ? ' class="mejor"' : ""}><td>${esc(E(t.grupo))}</td>${c.criterios.map((k) => `<td style="background:${color(t.rangos[k.id], n)}">${num(t.valores[k.id], 3)} (${num(t.rangos[k.id], 1)})</td>`).join("")}<td><b>${num(t.total, 1)}</b></td></tr>`).join("")}</tbody></table></div>
      <div class="aviso ok">${parrafos(c.texto)}</div></section>` });
  }

  if (r.d) {
    const d = r.d, cf = num(d.conf * 100, 0);
    const filas = [];
    if (d.media) filas.push(`<tr><td>Media de ${esc(d.media.columna)}</td><td>${num(d.media.estimado, 4)}</td><td>${num(d.media.inferior, 4)}</td><td>${num(d.media.superior, 4)}</td><td>t de Student</td></tr>`);
    if (d.varianza) filas.push(`<tr><td>Varianza de ${esc(d.varianza.columna)}</td><td>${num(d.varianza.estimado, 4)}</td><td>${num(d.varianza.inferior, 4)}</td><td>${num(d.varianza.superior, 4)}</td><td>Chi-cuadrado</td></tr>`,
      `<tr><td>Desv. estándar de ${esc(d.varianza.columna)}</td><td>${num(Math.sqrt(d.varianza.estimado), 4)}</td><td>${num(d.varianza.sd_inf, 4)}</td><td>${num(d.varianza.sd_sup, 4)}</td><td>Raíz del IC de la varianza</td></tr>`);
    if (d.proporcion) {
      const p = d.proporcion;
      filas.push(`<tr><td>Proporción con ${esc(p.columna)} ≤ ${num(p.limite, 4)} (${p.exitos}/${p.n})</td><td>${num(p.estimado, 4)}</td><td>${num(p.wald[0], 4)}</td><td>${num(p.wald[1], 4)}</td><td>Wald (aprox. normal)</td></tr>`,
        `<tr><td>&nbsp;</td><td>${num(p.estimado, 4)}</td><td>${num(p.wilson[0], 4)}</td><td>${num(p.wilson[1], 4)}</td><td>Wilson</td></tr>`,
        `<tr><td>&nbsp;</td><td>${num(p.estimado, 4)}</td><td>${num(p.exacto[0], 4)}</td><td>${num(p.exacto[1], 4)}</td><td>Exacto (Clopper-Pearson)</td></tr>`);
    }
    partes.push({ html: `<section class="card"><h2>d) Intervalos de confianza al ${cf} % · ${esc(E(d.grupo))}</h2>
      <div class="scroll"><table class="tabla"><thead><tr><th>Parámetro</th><th>Estimación</th><th>Límite inferior</th><th>Límite superior</th><th>Método</th></tr></thead><tbody>${filas.join("")}</tbody></table></div>
      <div class="aviso ok">${parrafos(d.texto)}</div>${d.supuesto ? `<p class="peq">${esc(d.supuesto)}</p>` : ""}</section>` });
  }

  if (r.e) {
    const e = r.e;
    partes.push({ html: `<section class="card"><h2>e) Variabilidad de ${esc(e.columna)}: ${esc(E(e.g1))} vs. ${esc(E(e.g2))}</h2>
      <div class="stats">${tarjeta("s " + E(e.g1), num(e.s1, 4), "n = " + e.n1)}${tarjeta("s " + E(e.g2), num(e.s2, 4), "n = " + e.n2)}${tarjeta("F = s₁²/s₂²", num(e.f, 3), `${e.gl1} y ${e.gl2} g.l.`)}${tarjeta("Valor p (F)", pv(e.p))}${tarjeta("Valor p (Levene)", pv(e.levene_p))}</div>
      <p>Decisión (prueba F): ${dec(e.rechaza)}</p><div class="aviso ok">${parrafos(e.texto)}</div></section>` });
  }

  if (r.f) {
    const f = r.f;
    partes.push({ html: `<section class="card"><h2>f) Prueba de una proporción · ${esc(E(f.grupo))}</h2>
      <div class="stats">${tarjeta("p̂ observada", num(f.phat * 100, 2) + " %", `${f.exitos} de ${f.n}`)}${tarjeta("p₀ afirmada", num(f.p0 * 100, 1) + " %", "H₁: " + f.h1)}${tarjeta("Estadístico z", num(f.z, 3))}${tarjeta("Valor p (Z)", pv(f.p_z))}${tarjeta("Valor p (exacta)", pv(f.p_exacto))}</div>
      <p>Decisión (α = ${num(f.alfa, 2)}): ${dec(f.rechaza)}</p><div class="aviso ok">${parrafos(f.texto)}</div></section>` });
  }

  $("m-resultados").innerHTML = avisos + partes.map((p) => p.html).join("");
  partes.forEach((p) => p.dibujar && p.dibujar());
}