// Cliente da API. A interface só conversa com /api (mesma origem, via nginx).

import { REQUEST_TIMEOUT_MS } from "./config.js";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** O FastAPI devolve `detail` como texto (nossos erros) ou lista (validação). */
function messageFrom(payload, status) {
  const detail = payload?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join("; ");
  return `O servidor respondeu com erro ${status}.`;
}

async function request(path, { method = "GET", body, form, signal } = {}) {
  const timeout = AbortSignal.timeout(REQUEST_TIMEOUT_MS);
  const merged = signal ? AbortSignal.any([signal, timeout]) : timeout;
  const options = { method, signal: merged, headers: {} };
  if (form) options.body = form;
  else if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(`/api${path}`, options);
  } catch (error) {
    if (signal?.aborted) throw error; // navegação cancelou: não é erro para o usuário
    throw new ApiError(0, "Não consegui falar com o servidor. Verifique se o backend está no ar.");
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, messageFrom(payload, response.status));
  return payload;
}

export const api = {
  get: (path, signal) => request(path, { signal }),
  post: (path, body, signal) => request(path, { method: "POST", body, signal }),
  upload: (path, form, signal) => request(path, { method: "POST", form, signal }),
};
