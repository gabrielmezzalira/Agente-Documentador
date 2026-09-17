import type { NextConfig } from "next";

import { securityHeaders } from "./security-headers.mjs";

const nextConfig: NextConfig = {
  // Some o `X-Powered-By: Next.js`, que entrega versão do framework de graça.
  poweredByHeader: false,
  // Proxeia /api/* para o backend (domínio diferente, Railway) através do
  // próprio domínio do frontend. Sem isso o cookie de sessão é de terceiro
  // (frontend e backend em domínios diferentes) e o Safari — desktop e iOS,
  // que bloqueiam cookie de terceiro por padrão desde 2020 — nunca persiste
  // o login: a app entra num loop de redirecionar pro /login.
  async rewrites() {
    const backend = process.env.NEXT_PUBLIC_API_URL;
    if (!backend) return [];
    return [{ source: "/api/:path*", destination: `${backend}/:path*` }];
  },
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
