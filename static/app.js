document.getElementById("marca-js").textContent = "JavaScript estático: cargado ✔";

const mostrar = (id, datos) =>
  (document.getElementById(id).textContent =
    typeof datos === "string" ? datos : JSON.stringify(datos, null, 2));

async function pedir(url, opciones, salida) {
  const t0 = performance.now();
  mostrar(salida, "Cargando...");
  try {
    const r = await fetch(url, opciones);
    const texto = await r.text();
    let cuerpo;
    try { cuerpo = JSON.parse(texto); } catch { cuerpo = texto; }
    const seg = ((performance.now() - t0) / 1000).toFixed(2);
    mostrar(salida, `HTTP ${r.status} · ${seg} s\n\n` + JSON.stringify(cuerpo, null, 2));
    return r.ok ? cuerpo : null;
  } catch (e) {
    mostrar(salida, "Error de red: " + e);
    return null;
  }
}

function dibujar(h, col) {
  const x = h.conteos.map((_, i) => (h.bordes[i] + h.bordes[i + 1]) / 2);
  Plotly.newPlot("grafico", [{ x, y: h.conteos, type: "bar", marker: { color: "#0F766E" } }],
    { title: "Histograma de " + col, margin: { t: 40 } });
}

document.getElementById("btn-estado").onclick = () =>
  pedir("/api/estado", {}, "salida-estado");

document.getElementById("btn-subir").onclick = async () => {
  const f = document.getElementById("archivo").files[0];
  if (!f) return mostrar("salida-subida", "Elige un archivo primero.");
  const fd = new FormData();
  fd.append("archivo", f);
  // No se bloquea por tamaño a propósito: se quiere ver el error real del servidor
  const r = await pedir("/api/analizar", { method: "POST", body: fd }, "salida-subida");
  if (r) dibujar(r.histograma, r.columna_analizada);
};

document.querySelectorAll(".ej").forEach((b) => {
  b.onclick = async () => {
    const r = await pedir("/api/datos-ejemplo/" + b.dataset.n, {}, "salida-ejemplo");
    if (r) dibujar(r.histograma, r.columna_analizada);
  };
});