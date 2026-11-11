const { JSDOM } = require("jsdom");
const fs = require("fs");
const assert = require("assert");
const RAIZ = require("path").join(__dirname, "..", "frontend");
const html = fs.readFileSync(RAIZ + "/index.html", "utf8");
const js = fs.readFileSync(RAIZ + "/js/app.js", "utf8");

const PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";
const respuesta = (status, cuerpo, cab = {}) => ({
  ok: status >= 200 && status < 300, status,
  headers: { get: (k) => (k.toLowerCase() === "content-type" ? "application/json" : cab[k.toLowerCase()] || null) },
  json: async () => cuerpo,
});
const RESULTADO = (extra = {}) => ({
  categoria: { codigo: "NV", nombre: "Nevus melanocítico", nivel_riesgo: "benigno", descripcion: "Lunar común." },
  confianza: 87.3, baja_confianza: false,
  probabilidades: [
    { codigo: "NV", nombre: "Nevus melanocítico", porcentaje: 87.3 },
    { codigo: "MEL", nombre: "Melanoma", porcentaje: 6.1 },
    { codigo: "BKL", nombre: "Queratosis benigna", porcentaje: 3.2 },
    { codigo: "BCC", nombre: "Carcinoma basocelular", porcentaje: 1.4 },
    { codigo: "DF", nombre: "Dermatofibroma", porcentaje: 0.9 },
  ],
  mapa_calor: PNG_B64, explicacion_mapa: "Las zonas más cálidas (rojo) son las que más influyeron.",
  mensaje: "", version_modelo: { id: 1, arquitectura: "MobileNetV2" }, aviso: "Prototipo académico. No es un diagnóstico.",
  ...extra,
});

async function nuevaApp(rutas, { dim = [400, 300] } = {}) {
  const dom = new JSDOM(html, { runScripts: "outside-only", url: "http://localhost/", pretendToBeVisual: true });
  const w = dom.window;
  const llamadas = [];
  w.fetch = async (ruta, op = {}) => {
    llamadas.push({ ruta, op });
    const f = rutas[ruta];
    if (!f) throw new Error("ruta sin mock: " + ruta);
    return typeof f === "function" ? f(op, llamadas) : f;
  };
  let n = 0;
  w.URL.createObjectURL = () => "blob:mock-" + ++n;
  w.URL.revokeObjectURL = () => {};
  w.Image = class { set src(v) { this.naturalWidth = dim[0]; this.naturalHeight = dim[1]; setTimeout(() => this.onload && this.onload(), 0); } };
  w.eval(js);
  const esperar = (ms = 20) => new Promise((r) => setTimeout(r, ms));
  await esperar();
  const $ = (id) => w.document.getElementById(id);
  const visible = (id) => !$(id).hidden;
  const pantallaVisible = () => [...w.document.querySelectorAll(".pantalla")].filter((p) => !p.hidden).map((p) => p.id.replace("pantalla-", ""));
  const click = (id) => $(id).dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  const archivo = (nombre, tam = 1000) => new w.File([new Uint8Array(tam)], nombre, { type: "image/png" });
  const elegir = async (f) => {
    Object.defineProperty($("archivo"), "files", { value: [f], configurable: true });
    $("archivo").dispatchEvent(new w.Event("change", { bubbles: true }));
    await esperar();
  };
  const enviarForm = async () => { $("form-acceso").dispatchEvent(new w.Event("submit", { cancelable: true, bubbles: true })); await esperar(); };
  return { w, $, visible, pantallaVisible, click, archivo, elegir, enviarForm, esperar, llamadas };
}
const con_sesion = { "/api/auth/yo": respuesta(200, { correo: "ana@correo.com" }) };
let pruebas = 0;
async function prueba(nombre, f) { try { await f(); pruebas++; console.log("  ok  -", nombre); } catch (e) { console.log("FALLA -", nombre, "\n      ", e.message); process.exitCode = 1; } }

(async () => {
  await prueba("sin sesión muestra el acceso y oculta los pasos", async () => {
    const a = await nuevaApp({ "/api/auth/yo": respuesta(401, { detail: "x" }) });
    assert.deepStrictEqual(a.pantallaVisible(), ["acceso"]);
    assert.ok(!a.visible("pasos") && !a.visible("sesion"));
  });

  await prueba("con sesión activa va directo al inicio (paso 1 de 4)", async () => {
    const a = await nuevaApp(con_sesion);
    assert.deepStrictEqual(a.pantallaVisible(), ["inicio"]);
    assert.strictEqual(a.$("pasos-texto").textContent, "Paso 1 de 4");
    assert.strictEqual(a.$("sesion-correo").textContent, "ana@correo.com");
    assert.strictEqual(a.$("pasos").querySelectorAll("i.activo").length, 1);
  });

  await prueba("login incorrecto muestra el mensaje", async () => {
    const a = await nuevaApp({ "/api/auth/yo": respuesta(401, {}), "/api/auth/login": respuesta(401, { detail: "Correo o contraseña incorrectos." }) });
    a.$("correo").value = "ana@correo.com"; a.$("contrasena").value = "mal-clave";
    await a.enviarForm();
    assert.strictEqual(a.$("error-acceso").textContent, "Correo o contraseña incorrectos.");
    assert.deepStrictEqual(a.pantallaVisible(), ["acceso"]);
  });

  await prueba("login bloqueado (429) indica los minutos de espera", async () => {
    const a = await nuevaApp({ "/api/auth/yo": respuesta(401, {}), "/api/auth/login": respuesta(429, { detail: "x" }, { "retry-after": "900" }) });
    a.$("correo").value = "ana@correo.com"; a.$("contrasena").value = "x";
    await a.enviarForm();
    assert.match(a.$("error-acceso").textContent, /15 minuto/);
  });

  await prueba("login correcto abre la sesión", async () => {
    const a = await nuevaApp({ "/api/auth/yo": respuesta(401, {}), "/api/auth/login": respuesta(200, { correo: "ana@correo.com" }) });
    a.$("correo").value = "Ana@Correo.com"; a.$("contrasena").value = "clave-segura-1";
    await a.enviarForm();
    assert.deepStrictEqual(a.pantallaVisible(), ["inicio"]);
    assert.strictEqual(a.$("contrasena").value, "");
  });

  await prueba("registro valida correo, contraseña y aviso antes de enviar", async () => {
    const a = await nuevaApp({ "/api/auth/yo": respuesta(401, {}), "/api/auth/registro": respuesta(201, { correo: "n@x.co" }) });
    a.click("tab-registro");
    assert.ok(a.visible("bloque-aviso") && a.visible("ayuda-contrasena"));
    assert.strictEqual(a.$("btn-acceso").textContent, "Crear cuenta");
    a.$("correo").value = "no-es-correo"; a.$("contrasena").value = "clave-segura-1"; await a.enviarForm();
    assert.match(a.$("error-acceso").textContent, /correo válido/);
    a.$("correo").value = "n@x.co"; a.$("contrasena").value = "corta"; await a.enviarForm();
    assert.match(a.$("error-acceso").textContent, /al menos 8/);
    a.$("contrasena").value = "clave-segura-1"; await a.enviarForm();
    assert.match(a.$("error-acceso").textContent, /aceptar el tratamiento/);
    assert.strictEqual(a.llamadas.filter((l) => l.ruta === "/api/auth/registro").length, 0);
    a.$("acepta-aviso").checked = true; await a.enviarForm();
    const llamada = a.llamadas.find((l) => l.ruta === "/api/auth/registro");
    assert.deepStrictEqual(JSON.parse(llamada.op.body), { correo: "n@x.co", contrasena: "clave-segura-1", acepta_aviso: true });
    assert.deepStrictEqual(a.pantallaVisible(), ["inicio"]);
  });

  await prueba("registro con correo repetido (409) muestra el mensaje del servidor", async () => {
    const a = await nuevaApp({ "/api/auth/yo": respuesta(401, {}), "/api/auth/registro": respuesta(409, { detail: "Ese correo ya está registrado." }) });
    a.click("tab-registro");
    a.$("correo").value = "n@x.co"; a.$("contrasena").value = "clave-segura-1"; a.$("acepta-aviso").checked = true;
    await a.enviarForm();
    assert.strictEqual(a.$("error-acceso").textContent, "Ese correo ya está registrado.");
  });

  await prueba("cerrar sesión vuelve al acceso", async () => {
    const a = await nuevaApp({ ...con_sesion, "/api/auth/logout": respuesta(204, {}) });
    a.click("btn-salir"); await a.esperar();
    assert.deepStrictEqual(a.pantallaVisible(), ["acceso"]);
    assert.ok(a.llamadas.some((l) => l.ruta === "/api/auth/logout" && l.op.method === "POST"));
  });

  await prueba("carga: rechaza PDF, vacío, mayor de 5 MB y demasiado pequeña", async () => {
    const a = await nuevaApp(con_sesion);
    a.click("btn-comenzar");
    assert.deepStrictEqual(a.pantallaVisible(), ["carga"]);
    assert.strictEqual(a.$("pasos-texto").textContent, "Paso 2 de 4");
    await a.elegir(a.archivo("informe.pdf")); assert.match(a.$("error-carga").textContent, /JPG, JPEG o PNG/);
    await a.elegir(a.archivo("a.png", 0)); assert.match(a.$("error-carga").textContent, /vacío/);
    await a.elegir(a.archivo("a.png", 6 * 1024 * 1024)); assert.match(a.$("error-carga").textContent, /más de 5 MB/);
    assert.deepStrictEqual(a.pantallaVisible(), ["carga"]);
    const p = await nuevaApp(con_sesion, { dim: [50, 400] });
    p.click("btn-comenzar"); await p.elegir(p.archivo("a.png"));
    assert.match(p.$("error-carga").textContent, /demasiado pequeña.*100 × 100/);
  });

  await prueba("carga válida muestra la vista previa con nombre, formato, tamaño y dimensiones", async () => {
    const a = await nuevaApp(con_sesion);
    a.click("btn-comenzar"); await a.elegir(a.archivo("lesion.PNG", 2.5 * 1024 * 1024));
    assert.deepStrictEqual(a.pantallaVisible(), ["previa"]);
    assert.strictEqual(a.$("d-nombre").textContent, "lesion.PNG");
    assert.strictEqual(a.$("d-formato").textContent, "PNG");
    assert.strictEqual(a.$("d-tamano").textContent, "2,5 MB");
    assert.strictEqual(a.$("d-dim").textContent, "400 × 300 px");
    assert.ok(a.$("previa-img").src.startsWith("blob:"));
    a.click("btn-cambiar"); assert.deepStrictEqual(a.pantallaVisible(), ["carga"]);
  });

  await prueba("soltar varias imágenes a la vez muestra un aviso", async () => {
    const a = await nuevaApp(con_sesion); a.click("btn-comenzar");
    const ev = new a.w.Event("drop", { bubbles: true, cancelable: true });
    ev.dataTransfer = { files: [a.archivo("a.png"), a.archivo("b.png")] };
    a.$("zona").dispatchEvent(ev); await a.esperar();
    assert.match(a.$("error-carga").textContent, /una sola imagen/);
  });

  await prueba("soltar una imagen (arrastrar y soltar) abre la vista previa", async () => {
    const a = await nuevaApp(con_sesion); a.click("btn-comenzar");
    const ev = new a.w.Event("drop", { bubbles: true, cancelable: true });
    ev.dataTransfer = { files: [a.archivo("a.png")] };
    a.$("zona").dispatchEvent(ev); await a.esperar();
    assert.deepStrictEqual(a.pantallaVisible(), ["previa"]);
  });

  await prueba("flujo completo: analizar, resultado, explicación con mapa, volver y nueva imagen", async () => {
    const a = await nuevaApp({ ...con_sesion, "/api/analizar": respuesta(200, RESULTADO()) });
    a.click("btn-comenzar"); await a.elegir(a.archivo("lesion.png"));
    a.click("btn-analizar"); await a.esperar(400);
    const envio = a.llamadas.find((l) => l.ruta === "/api/analizar");
    assert.strictEqual(envio.op.method, "POST");
    assert.strictEqual(envio.op.body.get("imagen").name, "lesion.png");
    assert.deepStrictEqual(a.pantallaVisible(), ["resultado"]);
    assert.strictEqual(a.$("pasos-texto").textContent, "Paso 3 de 4");
    assert.strictEqual(a.$("res-nombre").textContent, "Nevus melanocítico");
    assert.strictEqual(a.$("res-riesgo").textContent, "Lesión benigna");
    assert.strictEqual(a.$("res-confianza").textContent, "87,3 %");
    assert.strictEqual(a.$("res-confianza-barra").style.width, "87.3%");
    assert.ok(!a.visible("res-baja") && !a.visible("res-mensaje"));
    const otras = [...a.$("res-otras").querySelectorAll("li")].map((l) => l.textContent);
    assert.deepStrictEqual(otras, ["Melanoma6,1 %", "Queratosis benigna3,2 %", "Carcinoma basocelular1,4 %"]);
    assert.match(a.$("res-aviso").textContent, /Prototipo académico/);
    a.click("btn-explicacion");
    assert.deepStrictEqual(a.pantallaVisible(), ["explicacion"]);
    assert.strictEqual(a.$("pasos-texto").textContent, "Paso 4 de 4");
    assert.ok(a.visible("exp-comparar") && a.visible("exp-leyenda") && !a.visible("exp-sin-mapa"));
    assert.strictEqual(a.$("exp-mapa").src, "data:image/png;base64," + PNG_B64);
    assert.ok(a.$("exp-original").src.startsWith("blob:"));
    assert.match(a.$("exp-texto").textContent, /más cálidas/);
    a.click("btn-volver"); assert.deepStrictEqual(a.pantallaVisible(), ["resultado"]);
    a.click("btn-nueva"); assert.deepStrictEqual(a.pantallaVisible(), ["carga"]);
    assert.strictEqual(a.$("archivo").value, "");
  });

  await prueba("baja confianza y modelo provisional se avisan en el resultado", async () => {
    const msg = "MODELO PROVISIONAL DE DESARROLLO: este resultado no proviene de un modelo entrenado. La confianza del resultado es baja: tómalo con precaución.";
    const a = await nuevaApp({ ...con_sesion, "/api/analizar": respuesta(200, RESULTADO({ baja_confianza: true, confianza: 31.2, mensaje: msg })) });
    a.click("btn-comenzar"); await a.elegir(a.archivo("l.png")); a.click("btn-analizar"); await a.esperar(400);
    assert.ok(a.visible("res-baja"));
    assert.match(a.$("res-mensaje").textContent, /MODELO PROVISIONAL DE DESARROLLO/);
    assert.strictEqual(a.$("res-confianza").textContent, "31,2 %");
  });

  await prueba("sin mapa de calor, la explicación lo dice y el resultado sigue disponible", async () => {
    const a = await nuevaApp({ ...con_sesion, "/api/analizar": respuesta(200, RESULTADO({ mapa_calor: "", explicacion_mapa: "" })) });
    a.click("btn-comenzar"); await a.elegir(a.archivo("l.png")); a.click("btn-analizar"); await a.esperar(400);
    a.click("btn-explicacion");
    assert.ok(a.visible("exp-sin-mapa") && !a.visible("exp-comparar") && !a.visible("exp-leyenda"));
  });

  await prueba("un mapa de calor con contenido sospechoso no se usa como imagen", async () => {
    const a = await nuevaApp({ ...con_sesion, "/api/analizar": respuesta(200, RESULTADO({ mapa_calor: 'x" onerror="alert(1)' })) });
    a.click("btn-comenzar"); await a.elegir(a.archivo("l.png")); a.click("btn-analizar"); await a.esperar(400);
    a.click("btn-explicacion");
    assert.ok(a.visible("exp-sin-mapa"));
    assert.ok(!a.$("exp-mapa").src.includes("onerror"));
  });

  await prueba("el texto del servidor se muestra como texto (sin ejecutar HTML)", async () => {
    const mal = RESULTADO(); mal.categoria.nombre = '<img src=x onerror="window.pwned=1">';
    const a = await nuevaApp({ ...con_sesion, "/api/analizar": respuesta(200, mal) });
    a.click("btn-comenzar"); await a.elegir(a.archivo("l.png")); a.click("btn-analizar"); await a.esperar(400);
    assert.strictEqual(a.$("res-nombre").querySelectorAll("img").length, 0);
    assert.ok(a.$("res-nombre").textContent.includes("<img"));
    assert.strictEqual(a.w.pwned, undefined);
  });

  for (const [estado, cuerpo, titulo, reintenta] of [
    [422, { detail: "La imagen está dañada o no se pudo leer." }, "No pudimos usar la imagen", false],
    [413, { detail: "La imagen supera el tamaño máximo de 5 MB." }, "No pudimos usar la imagen", false],
    [400, { detail: "El archivo no es una imagen JPG o PNG válida." }, "No pudimos usar la imagen", false],
    [503, { detail: "x" }, "El servicio está ocupado", true],
    [500, { detail: "x" }, "No pudimos completar el análisis", true],
  ]) {
    await prueba(`error ${estado} del análisis → «${titulo}»${reintenta ? " con reintento" : ""}`, async () => {
      const a = await nuevaApp({ ...con_sesion, "/api/analizar": respuesta(estado, cuerpo) });
      a.click("btn-comenzar"); await a.elegir(a.archivo("l.png")); a.click("btn-analizar"); await a.esperar(100);
      assert.deepStrictEqual(a.pantallaVisible(), ["error"]);
      assert.strictEqual(a.$("error-titulo").textContent, titulo);
      assert.strictEqual(a.visible("btn-reintentar"), reintenta);
      if (estado === 422 || estado === 413 || estado === 400) assert.strictEqual(a.$("error-texto").textContent, cuerpo.detail);
      a.click("btn-error-nueva"); assert.deepStrictEqual(a.pantallaVisible(), ["carga"]);
    });
  }

  await prueba("reintentar vuelve a enviar la misma imagen", async () => {
    let intento = 0;
    const a = await nuevaApp({ ...con_sesion, "/api/analizar": () => (++intento === 1 ? respuesta(503, {}) : respuesta(200, RESULTADO())) });
    a.click("btn-comenzar"); await a.elegir(a.archivo("l.png")); a.click("btn-analizar"); await a.esperar(100);
    assert.deepStrictEqual(a.pantallaVisible(), ["error"]);
    a.click("btn-reintentar"); await a.esperar(400);
    assert.deepStrictEqual(a.pantallaVisible(), ["resultado"]);
    assert.strictEqual(a.llamadas.filter((l) => l.ruta === "/api/analizar").length, 2);
  });

  await prueba("sesión vencida durante el análisis (401) lleva al acceso con aviso", async () => {
    const a = await nuevaApp({ ...con_sesion, "/api/analizar": respuesta(401, { detail: "x" }) });
    a.click("btn-comenzar"); await a.elegir(a.archivo("l.png")); a.click("btn-analizar"); await a.esperar(100);
    assert.deepStrictEqual(a.pantallaVisible(), ["acceso"]);
    assert.match(a.$("error-acceso").textContent, /sesión venció/);
    assert.ok(!a.visible("sesion"));
  });

  await prueba("sin conexión al servidor muestra un error claro con reintento", async () => {
    const a = await nuevaApp({ ...con_sesion, "/api/analizar": () => { throw new Error("red caída"); } });
    a.click("btn-comenzar"); await a.elegir(a.archivo("l.png")); a.click("btn-analizar"); await a.esperar(100);
    assert.strictEqual(a.$("error-titulo").textContent, "No hay conexión");
    assert.ok(a.visible("btn-reintentar"));
  });

  await prueba("el indicador de progreso avanza mientras se espera y nunca llega a 100 antes de la respuesta", async () => {
    let soltar; const espera = new Promise((r) => (soltar = r));
    const a = await nuevaApp({ ...con_sesion, "/api/analizar": async () => { await espera; return respuesta(200, RESULTADO()); } });
    a.click("btn-comenzar"); await a.elegir(a.archivo("l.png")); a.click("btn-analizar");
    assert.deepStrictEqual(a.pantallaVisible(), ["analisis"]);
    await a.esperar(1200);
    const v = Number(a.$("progreso").getAttribute("aria-valuenow"));
    assert.ok(v > 4 && v < 90, "progreso " + v);
    assert.match(a.$("progreso-texto").textContent, /Analizando la imagen/);
    soltar(); await a.esperar(100);
    assert.deepStrictEqual(a.pantallaVisible(), ["resultado"]);
  });

  await prueba("descargar PDF: envía el resultado y la imagen, y baja el archivo", async () => {
    const a = await nuevaApp({ ...con_sesion, "/api/analizar": respuesta(200, RESULTADO()),
      "/api/exportar-pdf": { ok: true, status: 200, headers: { get: () => "application/pdf" }, blob: async () => ({}) } });
    a.click("btn-comenzar"); await a.elegir(a.archivo("l.png")); a.click("btn-analizar"); await a.esperar(400);
    let bajado = null;
    a.w.HTMLAnchorElement.prototype.click = function () { bajado = this.download; };
    a.click("btn-pdf"); await a.esperar(100);
    const l = a.llamadas.find((x) => x.ruta === "/api/exportar-pdf");
    assert.ok(l, "no llamó a la API");
    assert.strictEqual(JSON.parse(l.op.body.get("resultado")).categoria.codigo, "NV");
    assert.ok(l.op.body.get("imagen") && l.op.body.get("fecha"));
    assert.strictEqual(bajado, "derma-ai-resultado.pdf");
    assert.strictEqual(a.$("btn-pdf").disabled, false);
  });

  await prueba("descargar PDF: si falla muestra un error y deja reintentar", async () => {
    const a = await nuevaApp({ ...con_sesion, "/api/analizar": respuesta(200, RESULTADO()), "/api/exportar-pdf": respuesta(500, {}) });
    a.click("btn-comenzar"); await a.elegir(a.archivo("l.png")); a.click("btn-analizar"); await a.esperar(400);
    a.click("btn-pdf"); await a.esperar(100);
    assert.ok(a.visible("error-pdf"));
    assert.match(a.$("error-pdf").textContent, /No se pudo generar el PDF/);
    assert.strictEqual(a.$("btn-pdf").disabled, false);
  });

  console.log(`\n${pruebas} pruebas de la interfaz pasaron` + (process.exitCode ? " (hay fallas)" : ""));
})();
