import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("../dist/server/index.js", import.meta.url), "utf8");
const manifest = JSON.parse(await readFile(new URL("../dist/.openai/hosting.json", import.meta.url), "utf8"));
assert.ok(manifest.capabilities.includes("mcp"));
assert.equal(manifest.d1, null);
assert.equal(manifest.r2, null);
const worker = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
assert.equal(typeof worker.default.fetch, "function");
assert.equal((await worker.default.fetch(new Request("https://site.example/mcp"), {})).status, 405);
console.log("Sites artifact exports Worker ESM fetch and declares MCP");
