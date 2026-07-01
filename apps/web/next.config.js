/** @type {import('next').NextConfig} */
const isGithubPages = process.env.GITHUB_PAGES === "true";
const basePath = (process.env.NEXT_PUBLIC_BASE_PATH || "").replace(/\/$/, "");
const configuredApiUrl = (process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL)?.replace(/\/$/, "");
const apiBase = configuredApiUrl
  ? `${configuredApiUrl.replace(/\/api\/v1$/i, "")}/api/v1`
  : "http://127.0.0.1:8010/api/v1";

const nextConfig = {
  reactStrictMode: true,
  ...(isGithubPages
    ? {
        output: "export",
        trailingSlash: true,
        basePath,
        assetPrefix: basePath || undefined,
        images: {
          unoptimized: true,
        },
      }
    : {}),
  experimental: {
    middlewareClientMaxBodySize: "100mb",
  },
  ...(isGithubPages
    ? {}
    : {
        async rewrites() {
          return [
            {
              source: "/api/v1/:path*",
              destination: `${apiBase}/:path*`,
            },
          ];
        },
      }),
};

module.exports = nextConfig;
