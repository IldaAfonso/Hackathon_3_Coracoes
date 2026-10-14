// Roteador por hash (#/pd/dna/G5PS...), sem biblioteca. Cada rota é uma
// página com { title, render({ root, params, signal, area }) }.
//
// O menu muda com a área: na entrada mostra as duas áreas; dentro de uma
// área mostra só as páginas dela (ver areas.js).

import { AREAS, resolveRoute, setCurrentArea } from "./areas.js";
import { destroyCharts } from "./charts.js";
import { errorBox, foldToolbar, loading } from "./components.js";
import { APP_TITLE } from "./config.js";
import { h, render } from "./dom.js";
import { parseHash } from "./hash.js";

let controller = null;

/** Menu da área atual (ou o seletor de áreas, fora delas). */
function renderMenu(nav, area, activePage) {
  // Na página inicial os cartões das áreas já são o menu: a barra repetiria.
  nav.hidden = !area && activePage === "";
  if (nav.hidden) {
    render(nav);
    return;
  }
  if (!area) {
    render(nav,
      h("a", { href: "#/", text: "Início", "aria-current": activePage === "" ? "page" : null }),
      Object.entries(AREAS).map(([key, info]) => h("a", { href: `#/${key}`, text: info.label })));
    return;
  }
  const info = AREAS[area];
  render(nav,
    h("a", { class: "nav__back", href: "#/", text: "← Áreas" }),
    h("span", { class: "nav__area", text: info.label }),
    info.pages.map(([page, label]) => h("a", {
      href: `#/${area}/${page}`, text: label,
      "aria-current": page === activePage ? "page" : null,
    })));
}

export function startRouter({ root, nav, routes, fallback = "" }) {
  async function show() {
    controller?.abort();
    controller = new AbortController();
    const { signal } = controller;
    const { area, page: name, params } = resolveRoute(parseHash(window.location.hash));
    const page = routes[name] ?? routes[fallback];
    setCurrentArea(area);
    document.body.dataset.area = area ?? "";
    destroyCharts();
    renderMenu(nav, area, routes[name] ? name : fallback);
    const areaLabel = area ? ` · ${AREAS[area].label}` : "";
    document.title = page.title ? `${page.title}${areaLabel} · ${APP_TITLE}` : APP_TITLE;
    render(root, loading());
    try {
      const content = await page.render({ params, signal, root, area });
      if (signal.aborted) return;
      render(root, foldToolbar(content), content);
      if (typeof content?.afterMount === "function") content.afterMount();
    } catch (error) {
      if (signal.aborted) return;
      render(root, errorBox(error, show));
    }
    root.focus({ preventScroll: true });
    window.scrollTo({ top: 0 });
  }
  window.addEventListener("hashchange", show);
  show();
}
