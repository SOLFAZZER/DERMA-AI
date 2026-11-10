/* Derma-AI: interfaz web (prototipo académico). Sin frameworks. */
(function () {
  "use strict";

  var MAX_BYTES = 5 * 1024 * 1024;
  var MIN_LADO = 100;
  var EXTENSIONES = ["jpg", "jpeg", "png"];
  var ESPERA_MAX_MS = 45000;
  var PASOS = { inicio: 1, carga: 2, previa: 2, analisis: 2, resultado: 3, explicacion: 4 };
  var RIESGO = { benigno: "Lesión benigna", premaligno: "Lesión premaligna", maligno: "Lesión maligna" };

  var estado = { archivo: null, urlPrevia: null, resultado: null, modo: "login", temporizador: null, progreso: 0 };

  function $(id) { return document.getElementById(id); }
  function mostrarEl(el, visible) { el.hidden = !visible; }
  function texto(id, valor) { $(id).textContent = valor; }

  /* ------------------------------------------------------------ utilidades */
  function porcentaje(n) {
    return Number(n).toLocaleString("es-CO", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + " %";
  }
  function tamano(bytes) {
    if (bytes < 1024 * 1024) { return Math.max(1, Math.round(bytes / 1024)) + " KB"; }
    return (bytes / (1024 * 1024)).toLocaleString("es-CO", { maximumFractionDigits: 1 }) + " MB";
  }
  function extension(nombre) {
    var i = nombre.lastIndexOf(".");
    return i < 0 ? "" : nombre.slice(i + 1).toLowerCase();
  }

  /* ------------------------------------------------------------ pantallas */
  function mostrar(nombre) {
    var pantallas = document.querySelectorAll(".pantalla");
    for (var i = 0; i < pantallas.length; i++) { pantallas[i].hidden = true; }
    var pantalla = $("pantalla-" + nombre);
    pantalla.hidden = false;
    if (PASOS[nombre]) {
      mostrarEl($("pasos"), true);
      texto("pasos-texto", "Paso " + PASOS[nombre] + " de 4");
      var barras = $("pasos").querySelectorAll(".pasos-barras i");
      for (var j = 0; j < barras.length; j++) { barras[j].classList.toggle("activo", j < PASOS[nombre]); }
    } else if (nombre === "acceso") {
      mostrarEl($("pasos"), false);
    }
    var titulo = pantalla.querySelector("h1");
    if (titulo && titulo.focus) { titulo.focus(); }
  }

  function liberarImagen() {
    if (estado.urlPrevia) { URL.revokeObjectURL(estado.urlPrevia); }
    estado.urlPrevia = null;
    estado.archivo = null;
    $("archivo").value = "";
  }

  /* ------------------------------------------------------------ API */
  function api(ruta, opciones) {
    return fetch(ruta, opciones).then(function (resp) {
      var tipo = resp.headers.get("content-type") || "";
      var lectura = tipo.indexOf("application/json") >= 0 ? resp.json().catch(function () { return {}; }) : Promise.resolve({});
      return lectura.then(function (datos) {
        return { ok: resp.ok, status: resp.status, datos: datos || {}, reintentarEn: resp.headers.get("retry-after") };
      });
    });
  }
  function postJson(ruta, cuerpo) {
    return api(ruta, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) });
  }

  /* ------------------------------------------------------------ acceso */
  function mostrarAcceso(mensaje) {
    mostrarEl($("sesion"), false);
    limpiarSesionLocal();
    mostrar("acceso");
    fijarModo("login");
    mostrarErrorAcceso(mensaje || "");
  }
  function limpiarSesionLocal() {
    liberarImagen();
    estado.resultado = null;
    $("contrasena").value = "";
  }
  function mostrarErrorAcceso(mensaje) {
    var el = $("error-acceso");
    el.textContent = mensaje;
    el.hidden = !mensaje;
  }
  function fijarModo(modo) {
    estado.modo = modo;
    var registro = modo === "registro";
    $("tab-login").setAttribute("aria-selected", String(!registro));
    $("tab-registro").setAttribute("aria-selected", String(registro));
    texto("btn-acceso", registro ? "Crear cuenta" : "Iniciar sesión");
    $("contrasena").setAttribute("autocomplete", registro ? "new-password" : "current-password");
    mostrarEl($("ayuda-contrasena"), registro);
    mostrarEl($("bloque-aviso"), registro);
    mostrarErrorAcceso("");
  }
  function sesionIniciada(correo) {
    texto("sesion-correo", correo);
    mostrarEl($("sesion"), true);
    $("contrasena").value = "";
    mostrar("inicio");
  }
  function enviarAcceso(evento) {
    evento.preventDefault();
    var correo = $("correo").value.trim();
    var contrasena = $("contrasena").value;
    var registro = estado.modo === "registro";
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(correo)) { return mostrarErrorAcceso("Escribe un correo válido."); }
    if (registro && contrasena.length < 8) { return mostrarErrorAcceso("La contraseña debe tener al menos 8 caracteres."); }
    if (!registro && !contrasena) { return mostrarErrorAcceso("Escribe tu contraseña."); }
    if (registro && !$("acepta-aviso").checked) { return mostrarErrorAcceso("Debes aceptar el tratamiento de datos personales para crear la cuenta."); }
    mostrarErrorAcceso("");
    var boton = $("btn-acceso");
    boton.disabled = true;
    var cuerpo = registro ? { correo: correo, contrasena: contrasena, acepta_aviso: true } : { correo: correo, contrasena: contrasena };
    postJson(registro ? "/api/auth/registro" : "/api/auth/login", cuerpo).then(function (r) {
      if (r.ok) { return sesionIniciada(r.datos.correo || correo); }
      if (r.status === 401) { return mostrarErrorAcceso("Correo o contraseña incorrectos."); }
      if (r.status === 429) {
        var min = r.reintentarEn ? Math.ceil(Number(r.reintentarEn) / 60) : 15;
        return mostrarErrorAcceso("Demasiados intentos fallidos. Espera " + min + " minuto(s) para volver a intentar.");
      }
      if (r.status >= 500) { return mostrarErrorAcceso("El servicio no está disponible. Intenta de nuevo en unos minutos."); }
      mostrarErrorAcceso(r.datos.detail || "No se pudo completar la solicitud.");
    }).catch(function () {
      mostrarErrorAcceso("No hay conexión con el servidor. Revisa tu internet e intenta de nuevo.");
    }).then(function () { boton.disabled = false; });
  }
  function cerrarSesion() {
    api("/api/auth/logout", { method: "POST" }).catch(function () { return null; }).then(function () { mostrarAcceso(""); });
  }

  /* ------------------------------------------------------------ carga de la imagen */
  function errorCarga(mensaje) {
    var el = $("error-carga");
    el.textContent = mensaje;
    el.hidden = !mensaje;
  }
  function validarArchivo(archivo) {
    return new Promise(function (resolver) {
      var ext = extension(archivo.name || "");
      if (EXTENSIONES.indexOf(ext) < 0) { return resolver({ error: "El archivo no es una imagen permitida. Usa un archivo JPG, JPEG o PNG." }); }
      if (archivo.size === 0) { return resolver({ error: "El archivo está vacío. Elige otra imagen." }); }
      if (archivo.size > MAX_BYTES) { return resolver({ error: "La imagen pesa más de 5 MB. Elige una más liviana." }); }
      var url = URL.createObjectURL(archivo);
      var img = new Image();
      img.onload = function () {
        if (img.naturalWidth < MIN_LADO || img.naturalHeight < MIN_LADO) {
          URL.revokeObjectURL(url);
          return resolver({ error: "La imagen es demasiado pequeña. Usa una de al menos " + MIN_LADO + " × " + MIN_LADO + " píxeles." });
        }
        resolver({ url: url, ancho: img.naturalWidth, alto: img.naturalHeight, ext: ext });
      };
      img.onerror = function () {
        URL.revokeObjectURL(url);
        resolver({ error: "La imagen está dañada o no se puede abrir. Prueba con otra." });
      };
      img.src = url;
    });
  }
  function procesarArchivo(archivo) {
    if (!archivo) { return; }
    errorCarga("");
    validarArchivo(archivo).then(function (r) {
      if (r.error) { return errorCarga(r.error); }
      liberarImagen();
      estado.archivo = archivo;
      estado.urlPrevia = r.url;
      $("previa-img").src = r.url;
      texto("d-nombre", archivo.name);
      texto("d-formato", r.ext === "png" ? "PNG" : "JPG");
      texto("d-tamano", tamano(archivo.size));
      texto("d-dim", r.ancho + " × " + r.alto + " px");
      mostrar("previa");
    });
  }
  function nuevaImagen() {
    detenerProgreso();
    liberarImagen();
    estado.resultado = null;
    errorCarga("");
    mostrar("carga");
  }

  /* ------------------------------------------------------------ análisis */
  function iniciarProgreso() {
    detenerProgreso();
    estado.progreso = 4;
    var inicio = Date.now();
    pintarProgreso(estado.progreso, 0);
    estado.temporizador = setInterval(function () {
      estado.progreso += (90 - estado.progreso) * 0.07;
      pintarProgreso(estado.progreso, Math.round((Date.now() - inicio) / 1000));
    }, 500);
  }
  function pintarProgreso(valor, segundos) {
    var v = Math.round(valor);
    $("progreso-barra").style.width = v + "%";
    $("progreso").setAttribute("aria-valuenow", String(v));
    texto("progreso-texto", "Analizando la imagen… " + segundos + " s");
  }
  function detenerProgreso() {
    if (estado.temporizador) { clearInterval(estado.temporizador); }
    estado.temporizador = null;
  }
  function analizar() {
    if (!estado.archivo) { return nuevaImagen(); }
    mostrar("analisis");
    iniciarProgreso();
    var datos = new FormData();
    datos.append("imagen", estado.archivo, estado.archivo.name);
    var control = new AbortController();
    var limite = setTimeout(function () { control.abort(); }, ESPERA_MAX_MS);
    api("/api/analizar", { method: "POST", body: datos, signal: control.signal }).then(function (r) {
      clearTimeout(limite);
      detenerProgreso();
      if (r.ok) {
        estado.resultado = r.datos;
        pintarProgreso(100, 0);
        return mostrarResultado();
      }
      manejarErrorAnalisis(r);
    }).catch(function (e) {
      clearTimeout(limite);
      detenerProgreso();
      if (e && e.name === "AbortError") {
        return mostrarError("El análisis tardó demasiado", "Intenta de nuevo en unos minutos.", true);
      }
      mostrarError("No hay conexión", "No se pudo contactar al servidor. Revisa tu internet e intenta de nuevo.", true);
    });
  }
  function manejarErrorAnalisis(r) {
    var s = r.status;
    if (s === 401) { return mostrarAcceso("Tu sesión venció. Inicia sesión de nuevo."); }
    if (s === 400 || s === 413 || s === 422) {
      return mostrarError("No pudimos usar la imagen", r.datos.detail || "La imagen no es válida. Prueba con otra.", false);
    }
    if (s === 503) {
      return mostrarError("El servicio está ocupado", "El análisis está iniciando o con mucha demanda. Intenta de nuevo en unos minutos.", true);
    }
    mostrarError("No pudimos completar el análisis", "Ocurrió un error inesperado. Intenta de nuevo.", true);
  }
  function mostrarError(titulo, mensaje, reintentar) {
    texto("error-titulo", titulo);
    texto("error-texto", mensaje);
    mostrarEl($("btn-reintentar"), reintentar && !!estado.archivo);
    mostrar("error");
  }

  /* ------------------------------------------------------------ resultado y explicación */
  function mostrarResultado() {
    var r = estado.resultado;
    texto("res-nombre", r.categoria.nombre);
    texto("res-riesgo", RIESGO[r.categoria.nivel_riesgo] || "");
    mostrarEl($("res-riesgo"), !!RIESGO[r.categoria.nivel_riesgo]);
    texto("res-descripcion", r.categoria.descripcion || "");
    texto("res-confianza", porcentaje(r.confianza));
    $("res-confianza-barra").style.width = Math.max(0, Math.min(100, r.confianza)) + "%";
    mostrarEl($("res-baja"), !!r.baja_confianza);
    var lista = $("res-otras");
    lista.textContent = "";
    r.probabilidades.slice(1, 4).forEach(function (p) {
      var li = document.createElement("li");
      var nombre = document.createElement("span");
      var valor = document.createElement("strong");
      nombre.textContent = p.nombre;
      valor.textContent = porcentaje(p.porcentaje);
      li.appendChild(nombre);
      li.appendChild(valor);
      lista.appendChild(li);
    });
    var provisional = /MODELO PROVISIONAL[^.]*\./.exec(r.mensaje || "");
    texto("res-mensaje", provisional ? provisional[0] : "");
    mostrarEl($("res-mensaje"), !!provisional);
    texto("res-aviso", r.aviso || "Prototipo académico: este resultado no es un diagnóstico médico.");
    mostrar("resultado");
  }
  function mostrarExplicacion() {
    var r = estado.resultado;
    var hayMapa = !!r.mapa_calor && /^[A-Za-z0-9+\/=]+$/.test(r.mapa_calor);
    mostrarEl($("exp-comparar"), hayMapa);
    mostrarEl($("exp-leyenda"), hayMapa);
    mostrarEl($("exp-sin-mapa"), !hayMapa);
    if (hayMapa) {
      $("exp-original").src = estado.urlPrevia || "";
      $("exp-mapa").src = "data:image/png;base64," + r.mapa_calor;
      if (r.explicacion_mapa) { texto("exp-texto", r.explicacion_mapa); }
    }
    mostrarEl($("exp-texto"), hayMapa);
    mostrar("explicacion");
  }

  /* ------------------------------------------------------------ eventos */
  function iniciar() {
    $("tab-login").addEventListener("click", function () { fijarModo("login"); });
    $("tab-registro").addEventListener("click", function () { fijarModo("registro"); });
    $("form-acceso").addEventListener("submit", enviarAcceso);
    $("btn-salir").addEventListener("click", cerrarSesion);
    $("btn-comenzar").addEventListener("click", function () { mostrar("carga"); });
    $("btn-elegir").addEventListener("click", function () { $("archivo").click(); });
    $("archivo").addEventListener("change", function () { procesarArchivo($("archivo").files[0]); });
    var zona = $("zona");
    zona.addEventListener("dragover", function (e) { e.preventDefault(); zona.classList.add("arrastrando"); });
    zona.addEventListener("dragleave", function () { zona.classList.remove("arrastrando"); });
    zona.addEventListener("drop", function (e) {
      e.preventDefault();
      zona.classList.remove("arrastrando");
      var archivos = e.dataTransfer && e.dataTransfer.files;
      if (archivos && archivos.length > 1) { return errorCarga("Sube una sola imagen a la vez."); }
      procesarArchivo(archivos && archivos[0]);
    });
    $("btn-cambiar").addEventListener("click", nuevaImagen);
    $("btn-analizar").addEventListener("click", analizar);
    $("btn-explicacion").addEventListener("click", mostrarExplicacion);
    $("btn-volver").addEventListener("click", mostrarResultado);
    $("btn-nueva").addEventListener("click", nuevaImagen);
    $("btn-nueva2").addEventListener("click", nuevaImagen);
    $("btn-error-nueva").addEventListener("click", nuevaImagen);
    $("btn-reintentar").addEventListener("click", analizar);

    api("/api/auth/yo").then(function (r) {
      if (r.ok && r.datos.correo) { sesionIniciada(r.datos.correo); } else { mostrarAcceso(""); }
    }).catch(function () { mostrarAcceso(""); });
  }

  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", iniciar); } else { iniciar(); }
})();
