// Modo claro / oscuro. Se carga primero (sin "module") para que la pagina no parpadee.
// Opciones: "auto" (sigue al celular), "claro" u "oscuro". Se recuerda en este navegador.
(function () {
  var raiz = document.documentElement, clave = "mcs.tema";
  var sistema = window.matchMedia("(prefers-color-scheme: dark)");
  function guardado() { try { return localStorage.getItem(clave) || "auto"; } catch (e) { return "auto"; } }
  function aplicar() {
    var modo = guardado();
    var final = modo === "auto" ? (sistema.matches ? "oscuro" : "claro") : modo;
    raiz.dataset.tema = final;
    raiz.dataset.modo = modo;
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", final === "oscuro" ? "#08090a" : "#f2f3f0");
    document.dispatchEvent(new CustomEvent("mcs-tema"));
  }
  window.MCS_TEMA = { modo: guardado, fijar: function (modo) { try { localStorage.setItem(clave, modo); } catch (e) { /* sin permiso */ } aplicar(); } };
  sistema.addEventListener("change", function () { if (guardado() === "auto") aplicar(); });
  aplicar();
})();
