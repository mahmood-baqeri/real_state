import path from "node:path";
import type { NextConfig } from "next";

const BACKEND_ORIGIN = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8020";

const nextConfig: NextConfig = {
  outputFileTracingRoot: path.resolve(__dirname),
  skipTrailingSlashRedirect: true,
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: "/media/:path*",
        destination: `${BACKEND_ORIGIN}/media/:path*`,
      },
    ];
  },
};

export default nextConfig;
