import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  outputFileTracingRoot: path.resolve(__dirname),
  skipTrailingSlashRedirect: true,
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
