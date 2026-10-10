import assert from "node:assert/strict";
import { mock, test } from "node:test";
import worker from "../worker/index.js";

const env = { JMA_BACKEND_URL: "https://backend.example/mcp", JMA_BACKEND_TOKEN: "fixture-service-token-0000000000000000" };
const call = { jsonrpc: "2.0", id: 1, method: "tools/call", params: { name: "get_station_info", arguments: { code: "44132" } } };
function request(message = call, headers = {}, options = {}) {
  return new Request("https://site.example/mcp", {
    method: "POST", headers: { "content-type": "application/json", accept: "application/json, text/event-stream", ...headers },
    body: JSON.stringify(message), ...options,
  });
}

test("identity is required for data calls; service access does not create identity", async () => {
  const upstream = mock.method(globalThis, "fetch", () => { throw new Error("Must not contact backend"); });
  try {
    for (const headers of [{}, { authorization: "Bearer visitor-token" }, { "OAI-Sites-Authorization": "Bearer service-access" }, { "oai-authenticated-user-id": " " }]) {
      assert.equal((await worker.fetch(request(call, headers), env)).status, 401);
    }
    assert.equal(upstream.mock.callCount(), 0);
  } finally { mock.restoreAll(); }
});

test("discovery and calls preserve body, protocol headers, paging, and result bytes", async () => {
  const result = JSON.stringify({ jsonrpc: "2.0", id: 1, result: { structuredContent: { temperature: { value: 0, unit: "℃" }, missing: null } } });
  const upstream = mock.method(globalThis, "fetch", async (url, init) => {
    assert.equal(String(url), env.JMA_BACKEND_URL);
    assert.equal(init.headers.get("authorization"), `Bearer ${env.JMA_BACKEND_TOKEN}`);
    for (const name of ["cookie", "origin", "oai-authenticated-user-id", "oai-authenticated-user-email", "OAI-Sites-Authorization", "mcp-session-id"]) {
      assert.equal(init.headers.has(name), false);
    }
    assert.equal(init.redirect, "manual");
    assert.equal(init.headers.get("mcp-protocol-version"), "2026-07-28");
    assert.equal(init.headers.get("mcp-method"), "tools/call");
    assert.equal(init.headers.get("mcp-name"), "get_station_info");
    assert.equal(init.headers.get("mcp-param-fixture"), "same");
    assert.deepEqual(JSON.parse(new TextDecoder().decode(init.body)), call);
    return new Response(result, { headers: { "content-type": "application/json", "set-cookie": "must-not-leak", "server": "private-backend" } });
  });
  try {
    const response = await worker.fetch(request(call, {
      "oai-authenticated-user-id": "fixture-owner", "oai-authenticated-user-email": "fixture@example.invalid",
      authorization: "Bearer visitor-token", cookie: "private", "OAI-Sites-Authorization": "Bearer platform-token",
      "mcp-protocol-version": "2026-07-28", "mcp-method": "tools/call", "mcp-name": "get_station_info", "mcp-param-fixture": "same",
      "mcp-session-id": "ignored",
    }), env);
    assert.equal(await response.text(), result);
    assert.equal(response.headers.get("cache-control"), "no-store, no-transform");
    assert.equal(response.headers.has("set-cookie"), false);
    upstream.mock.mockImplementation(async (_url, init) => {
      assert.deepEqual(JSON.parse(new TextDecoder().decode(init.body)).params, { cursor: "opaque" });
      return new Response(JSON.stringify({ jsonrpc: "2.0", id: 2, result: { tools: [], nextCursor: "opaque-next" } }), { headers: { "content-type": "application/json" } });
    });
    const discovery = await worker.fetch(request({ jsonrpc: "2.0", id: 2, method: "tools/list", params: { cursor: "opaque" } }), env);
    assert.equal((await discovery.json()).result.nextCursor, "opaque-next");
  } finally { mock.restoreAll(); }
});

test("invalid requests fail before any backend call", async () => {
  const upstream = mock.method(globalThis, "fetch", () => { throw new Error("Must not fetch"); });
  try {
    for (const [req, expected] of [
      [request(call, { origin: "https://attacker.example" }), 403],
      [request(call, { origin: "null" }), 403],
      [request(call, { "content-type": "text/plain" }), 415],
      [request(call, {}, { body: "{" }), 400],
      [request(call, {}, { body: new Uint8Array([0xff]) }), 400],
      [request([call]), 400],
      [request({ jsonrpc: "2.0", id: 1, result: {} }), 400],
      [request({ ...call, id: null }), 400],
      [request({ ...call, id: {} }), 400],
      [request(call, {}, { body: "x".repeat(65537) }), 413],
    ]) assert.equal((await worker.fetch(req, env)).status, expected);
    assert.equal(upstream.mock.callCount(), 0);
    assert.equal((await worker.fetch(new Request("https://site.example/other"), env)).status, 404);
    for (const method of ["GET", "DELETE", "PUT"]) {
      assert.equal((await worker.fetch(new Request("https://site.example/mcp", { method }), env)).status, 405);
    }
  } finally { mock.restoreAll(); }
});

test("fixed HTTPS backend, secret, redirects, and network failures fail closed", async () => {
  let responseStatus = 302;
  const upstream = mock.method(globalThis, "fetch", async () => new Response("private upstream detail", {
    status: responseStatus, headers: { location: "https://attacker.example", "www-authenticate": "private challenge" },
  }));
  const req = () => request(call, { "oai-authenticated-user-id": "fixture-owner" });
  try {
    for (const badUrl of ["http://backend.example/mcp", "https://user:password@backend.example/mcp", "https://backend.example/other", "https://backend.example/mcp?q=secret", "https://backend.example/mcp#fragment"]) {
      assert.equal((await worker.fetch(req(), { ...env, JMA_BACKEND_URL: badUrl })).status, 503);
    }
    for (const token of [undefined, "", "short", "x".repeat(32) + "\n"]) {
      assert.equal((await worker.fetch(req(), { ...env, JMA_BACKEND_TOKEN: token })).status, 503);
    }
    assert.equal(upstream.mock.callCount(), 0);
    for (responseStatus of [302, 401, 403, 500, 503]) {
      const response = await worker.fetch(req(), env);
      assert.equal(response.status, 502);
      assert.equal((await response.text()).includes("private"), false);
      assert.equal(response.headers.has("www-authenticate"), false);
    }
    upstream.mock.mockImplementation(async () => new Response("private reverse-proxy HTML", { headers: { "content-type": "text/html" } }));
    assert.equal((await worker.fetch(req(), env)).status, 502);
    upstream.mock.mockImplementation(async () => { throw new Error(`private URL and ${env.JMA_BACKEND_TOKEN}`); });
    const response = await worker.fetch(req(), env);
    assert.equal(response.status, 502);
    assert.equal((await response.text()).includes(env.JMA_BACKEND_TOKEN), false);
  } finally { mock.restoreAll(); }
});

test("accepted notifications and streaming/error responses are forwarded", async () => {
  const upstream = mock.method(globalThis, "fetch", async () => new Response(null, { status: 202 }));
  try {
    const initialized = { jsonrpc: "2.0", method: "notifications/initialized" };
    assert.equal((await worker.fetch(request(initialized), env)).status, 202);
    upstream.mock.mockImplementation(async () => new Response("event: message\ndata: fixture\n\n", { headers: { "content-type": "text/event-stream" } }));
    const stream = await worker.fetch(request(call, { "oai-authenticated-user-id": "fixture-owner", origin: "https://site.example" }), env);
    assert.equal(stream.headers.get("content-type"), "text/event-stream");
    assert.equal(await stream.text(), "event: message\ndata: fixture\n\n");
    upstream.mock.mockImplementation(async () => Response.json({ jsonrpc: "2.0", id: 1, error: { code: -32020, message: "Header mismatch" } }, { status: 400 }));
    const response = await worker.fetch(request(call, { "oai-authenticated-user-id": "fixture-owner" }), env);
    assert.equal(response.status, 400);
    assert.equal((await response.json()).error.code, -32020);
  } finally { mock.restoreAll(); }
});
