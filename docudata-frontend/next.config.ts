import type { NextConfig } from "next";

import { securityHeaders } from "./security-headers.mjs";

const nextConfig: NextConfig = {
  // Some o `X-Powered-By: Next.js`, que entrega versão do framework de graça.
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders(
          process.env.NEXT_PUBLIC_API_URL,
          process.env.NODE_ENV !== "production",
        ),
      },
    ];
  },
};

export default nextConfig;
