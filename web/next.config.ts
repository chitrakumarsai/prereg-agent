import type { NextConfig } from "next";

// Static export in production: Caddy serves these files and proxies /api to FastAPI.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: false,
  images: { unoptimized: true },
  productionBrowserSourceMaps: false,
};

export default nextConfig;
