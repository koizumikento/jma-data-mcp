// Isolated test harness: emulate Sites Dispatch and route Worker fetch to loopback.
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { Readable } from "node:stream";
import worker from "../worker/index.js";

const nativeFetch = globalThis.fetch;
globalThis.fetch = (url, init) => {
  assert.equal(String(url), "https://backend.example/mcp");
  return nativeFetch(`http://127.0.0.1:${process.argv[2]}/mcp`, init);
};
const server = createServer(async (incoming, outgoing) => {
  try {
    const request = new Request(`http://127.0.0.1:${server.address().port}${incoming.url}`, {
      method: incoming.method, headers: incoming.headers,
      ...(["GET", "HEAD"].includes(incoming.method) ? {} : { body: Readable.toWeb(incoming), duplex: "half" }),
    });
    const response = await worker.fetch(request, {
      JMA_BACKEND_URL: "https://backend.example/mcp", JMA_BACKEND_TOKEN: process.env.JMA_BACKEND_TOKEN,
    });
    outgoing.writeHead(response.status, Object.fromEntries(response.headers));
    if (response.body) Readable.fromWeb(response.body).pipe(outgoing);
    else outgoing.end();
  } catch {
    outgoing.writeHead(500).end();
  }
});
server.listen(0, "127.0.0.1", () => console.log(server.address().port));
