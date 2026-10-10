const PUBLIC_METHODS = new Set([
  "initialize", "server/discover", "ping", "tools/list", "resources/list", "resources/templates/list",
  "prompts/list", "notifications/initialized", "notifications/cancelled",
]);
const MAX_BODY_BYTES = 64 * 1024;

function error(id, code, message, status) {
  return Response.json({ jsonrpc: "2.0", id, error: { code, message } }, {
    status, headers: { "cache-control": "no-store" },
  });
}

async function readBody(request) {
  const reader = request.body?.getReader();
  if (!reader) return new Uint8Array();
  const chunks = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_BODY_BYTES) {
        await reader.cancel();
        return null;
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const body = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    body.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return body;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname !== "/mcp") return new Response("Not found", { status: 404 });
    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405, headers: { allow: "POST" } });
    }
    const origin = request.headers.get("origin");
    if (origin !== null && origin !== url.origin) {
      return error(null, -32000, "Origin is not allowed", 403);
    }
    if (request.headers.get("content-type")?.split(";")[0].trim().toLowerCase() !== "application/json") {
      return error(null, -32600, "Content-Type must be application/json", 415);
    }
    let body, message;
    try {
      body = await readBody(request);
      if (body === null) return error(null, -32600, "Request exceeds 64 KiB", 413);
      message = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(body));
    } catch {
      return error(null, -32700, "Invalid JSON", 400);
    }
    if (!message || Array.isArray(message) || message.jsonrpc !== "2.0" ||
        typeof message.method !== "string" ||
        ("id" in message && typeof message.id !== "string" && typeof message.id !== "number")) {
      return error(null, -32600, "Expected a single JSON-RPC request or notification", 400);
    }
    // Only Sites Dispatch may supply this identity; never expose this Worker directly.
    if (!PUBLIC_METHODS.has(message.method) && !request.headers.get("oai-authenticated-user-id")?.trim()) {
      return error(message.id ?? null, -32000, "Sign in to this Site before calling tools", 401);
    }
    let backend;
    try {
      backend = new URL(env.JMA_BACKEND_URL);
      if (backend.protocol !== "https:" || backend.pathname !== "/mcp" ||
          backend.username || backend.password || backend.search || backend.hash ||
          typeof env.JMA_BACKEND_TOKEN !== "string" || env.JMA_BACKEND_TOKEN.length < 32 ||
          !/^[\x21-\x7e]+$/.test(env.JMA_BACKEND_TOKEN)) throw new Error();
    } catch {
      return error(message.id ?? null, -32000, "Configure JMA_BACKEND_URL and JMA_BACKEND_TOKEN", 503);
    }
    const headers = new Headers({
      "content-type": "application/json",
      "accept": request.headers.get("accept") ?? "",
      "authorization": `Bearer ${env.JMA_BACKEND_TOKEN}`,
    });
    for (const [name, value] of request.headers) {
      if (["mcp-protocol-version", "mcp-method", "mcp-name"].includes(name) || name.startsWith("mcp-param-")) {
        headers.set(name, value);
      }
    }
    try {
      const response = await fetch(backend, {
        method: "POST", headers, body, redirect: "manual", signal: request.signal,
      });
      const contentType = response.headers.get("content-type")?.split(";")[0].trim().toLowerCase();
      if ((response.status >= 300 && response.status < 400) ||
          [401, 403].includes(response.status) || response.status >= 500 ||
          (response.status !== 202 && !["application/json", "text/event-stream"].includes(contentType))) {
        await response.body?.cancel();
        return error(message.id ?? null, -32000, "Backend unavailable; check service configuration", 502);
      }
      const responseHeaders = new Headers({ "cache-control": "no-store, no-transform", "x-accel-buffering": "no" });
      for (const name of ["content-type", "retry-after"]) {
        if (response.headers.has(name)) responseHeaders.set(name, response.headers.get(name));
      }
      return new Response(response.body, { status: response.status, headers: responseHeaders });
    } catch {
      return error(message.id ?? null, -32000, "Backend unreachable; retry later", 502);
    }
  },
};
