const { spawnSync } = require("node:child_process");
const { existsSync, writeFileSync } = require("node:fs");
const { join } = require("node:path");

if (!process.env.NEXT_PUBLIC_API_URL) {
  console.error("Defina NEXT_PUBLIC_API_URL com a URL publica da API. Exemplo:");
  console.error('$env:NEXT_PUBLIC_API_URL="https://abc123.ngrok-free.app/api/v1"');
  process.exit(1);
}

process.env.GITHUB_PAGES = "true";

const result = spawnSync("npm", ["run", "build:clean"], {
  cwd: join(__dirname, ".."),
  env: process.env,
  shell: true,
  stdio: "inherit",
});

if (result.status !== 0) {
  process.exit(result.status || 1);
}

const outDir = join(__dirname, "..", "out");
if (existsSync(outDir)) {
  writeFileSync(join(outDir, ".nojekyll"), "");
}
