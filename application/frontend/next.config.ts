// Path: frontend/next.config.ts

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  skipTrailingSlashRedirect: true,
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
