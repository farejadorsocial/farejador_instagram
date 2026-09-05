/* Entry point do Farejador.
 * Os módulos abaixo são carregados em ordem porque compartilham o mesmo estado global
 * da aplicação original. A ordem é intencional e preserva o comportamento existente.
 */
(function carregarModulos(lista, indice) {
  if (indice >= lista.length) return;
  const script = document.createElement("script");
  script.src = `${lista[indice]}?v=20260905-2c80eb0`;
  script.onload = function () { carregarModulos(lista, indice + 1); };
  script.onerror = function () {
    console.error("Falha ao carregar módulo:", lista[indice]);
    const erro = document.createElement("div");
    erro.className = "card empty";
    erro.style.margin = "24px";
    erro.textContent = "Não foi possível carregar um módulo da interface.";
    document.querySelector("#content")?.replaceChildren(erro);
  };
  document.head.appendChild(script);
})([
  "/static/js/core/runtime.js",
  "/static/js/modules/dashboard.js",
  "/static/js/modules/profiles.js",
  "/static/js/modules/compare.js",
  "/static/js/modules/auth.js",
  "/static/js/modules/events.js"
], 0);
