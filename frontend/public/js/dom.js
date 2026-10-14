// Construção de DOM segura: texto entra SEMPRE como nó de texto (nunca
// innerHTML). A API devolve texto digitado por pessoas; tratá-lo como HTML
// abriria a porta para injeção de script (XSS).

/**
 * Cria um elemento.
 * @param {string} tag
 * @param {Object} [props] class, text, dataset, on<Evento>, ou atributos.
 * @param {...(Node|string|null|false|Array)} children
 * @returns {HTMLElement}
 */
export function h(tag, props = {}, ...children) {
  const element = document.createElement(tag);
  for (const [key, value] of Object.entries(props ?? {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") element.className = value;
    else if (key === "text") element.textContent = value;
    else if (key === "dataset") Object.assign(element.dataset, value);
    else if (key.startsWith("on") && typeof value === "function") {
      element.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (value === true) element.setAttribute(key, "");
    else element.setAttribute(key, String(value));
  }
  append(element, children);
  return element;
}

function append(parent, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    parent.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

/** Troca o conteúdo de um contêiner. */
export function render(container, ...children) {
  container.replaceChildren();
  append(container, children);
  return container;
}

const SVG_NS = "http://www.w3.org/2000/svg";

/** Elemento SVG (mesmas regras de `h`: texto sempre como nó de texto). */
export function svg(tag, props = {}, ...children) {
  const element = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(props ?? {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "text") element.textContent = value;
    else element.setAttribute(key, String(value));
  }
  append(element, children);
  return element;
}
