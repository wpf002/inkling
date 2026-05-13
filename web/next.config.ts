import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      // Phase 3 replaced /reveal-stub with /reveal. Keep the old path
      // working so any stale link or bookmark still lands somewhere
      // useful instead of 404ing.
      { source: "/reveal-stub", destination: "/reveal", permanent: true },
    ];
  },
};

export default nextConfig;
