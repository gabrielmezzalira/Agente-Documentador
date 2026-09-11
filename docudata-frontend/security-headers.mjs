/**
 * Headers de segurança aplicados a todas as rotas do App Router.
 *
 * Fica num módulo separado de `next.config.ts` para poder ser exercitado por
 * teste sem subir o Next inteiro.
 */

/** Origens de `connect-src`: o próprio frontend e o backend configurado. */
export function connectSources(apiUrl) {
  const fontes = ["'self'"];
  if (apiUrl) {
    try {
      fontes.push(new URL(apiUrl).origin);
    } catch {
      // URL inválida no ambiente: mantém só 'self' em vez de quebrar o build.
    }
  }
  return fontes;
}

/**
 * CSP em modo Report-Only.
 *
 * `unsafe-inline` em script/style é o que o Next precisa hoje: o bootstrap de
 * hidratação e o payload do RSC são scripts inline sem nonce, e a folha de
 * estilo global é injetada inline. Trocar isso por nonce exige renderização
 * dinâmica em toda página — mudança de arquitetura que a Spec 10 avalia.
 * `unsafe-eval` fica restrito ao servidor de desenvolvimento, onde o bundler
 * usa eval para source maps; o build de produção não precisa dessa permissão.
 * Report-Only dá visibilidade das violações agora sem risco de quebrar a UI.
 */
export function contentSecurityPolicy(apiUrl, permitirEval = false) {
  const scriptSrc = ["'self'", "'unsafe-inline'"];
  if (permitirEval) scriptSrc.push("'unsafe-eval'");

  return [
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    `script-src ${scriptSrc.join(" ")}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    "worker-src 'self' blob:",
    `connect-src ${connectSources(apiUrl).join(" ")}`,
  ].join("; ");
}

export function securityHeaders(apiUrl, permitirEval = false) {
  return [
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    { key: "X-Frame-Options", value: "DENY" },
    {
      key: "Permissions-Policy",
      value: "camera=(), microphone=(), geolocation=()",
    },
    {
      key: "Content-Security-Policy-Report-Only",
      value: contentSecurityPolicy(apiUrl, permitirEval),
    },
  ];
}
