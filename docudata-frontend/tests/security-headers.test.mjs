import assert from "node:assert/strict";
import test from "node:test";

import {
  connectSources,
  contentSecurityPolicy,
  securityHeaders,
} from "../security-headers.mjs";

const API = "https://backend.example.com";

test("todas as páginas recebem os headers de segurança exigidos", () => {
  const porChave = Object.fromEntries(
    securityHeaders(API).map((h) => [h.key, h.value]),
  );

  assert.equal(porChave["X-Content-Type-Options"], "nosniff");
  assert.equal(porChave["Referrer-Policy"], "strict-origin-when-cross-origin");
  assert.equal(porChave["X-Frame-Options"], "DENY");
  assert.match(porChave["Permissions-Policy"], /camera=\(\)/);
  assert.match(porChave["Permissions-Policy"], /microphone=\(\)/);
  assert.match(porChave["Permissions-Policy"], /geolocation=\(\)/);
});

test("CSP entra como Report-Only nesta etapa", () => {
  const chaves = securityHeaders(API).map((h) => h.key);

  assert.ok(chaves.includes("Content-Security-Policy-Report-Only"));
  assert.ok(!chaves.includes("Content-Security-Policy"));
});

test("CSP bloqueia framing e libera o que o Next e o app realmente usam", () => {
  const csp = contentSecurityPolicy(API);

  assert.match(csp, /frame-ancestors 'none'/);
  assert.match(csp, /object-src 'none'/);
  // Produção mantém scripts próprios/inline sem liberar eval.
  assert.match(csp, /script-src 'self' 'unsafe-inline'/);
  assert.doesNotMatch(csp, /'unsafe-eval'/);
  // Estilos inline já usados em todo o projeto.
  assert.match(csp, /style-src 'self' 'unsafe-inline'/);
  // Preview de upload e imagens embutidas.
  assert.match(csp, /img-src 'self' data: blob:/);
});

test("unsafe-eval fica limitado ao servidor de desenvolvimento", () => {
  assert.match(contentSecurityPolicy(API, true), /script-src 'self' 'unsafe-inline' 'unsafe-eval'/);
});

test("connect-src cobre apenas o frontend e o backend configurado", () => {
  assert.deepEqual(connectSources(API), ["'self'", API]);
  assert.deepEqual(connectSources(undefined), ["'self'"]);
  // URL inválida não pode derrubar o build.
  assert.deepEqual(connectSources("nao-e-url"), ["'self'"]);
  assert.match(contentSecurityPolicy(API), /connect-src 'self' https:\/\/backend\.example\.com/);
});
