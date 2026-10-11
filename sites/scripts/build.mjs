import { copyFile, mkdir } from "node:fs/promises";

// Sites' Worker ESM layout, using portable Node operations instead of bash.
await mkdir(new URL("../dist/server/", import.meta.url), { recursive: true });
await mkdir(new URL("../dist/.openai/", import.meta.url), { recursive: true });
await copyFile(new URL("../worker/index.js", import.meta.url), new URL("../dist/server/index.js", import.meta.url));
await copyFile(new URL("../.openai/hosting.json", import.meta.url), new URL("../dist/.openai/hosting.json", import.meta.url));
