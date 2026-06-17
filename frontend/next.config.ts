import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the workspace root; otherwise Next picks up an unrelated lockfile in $HOME.
  turbopack: { root: import.meta.dirname },
};

export default nextConfig;
