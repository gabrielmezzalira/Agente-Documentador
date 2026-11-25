const PARTICULAS = new Set(["de", "da", "do", "das", "dos", "e"]);

/** Capitaliza cada parte, mantendo "de/da/do/dos/das/e" em minúsculas ("MARIA DA SILVA" → "Maria da Silva"). */
export function nomeFormatado(nome: string): string {
  return nome
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((p, i) => {
      const baixa = p.toLowerCase();
      if (i > 0 && PARTICULAS.has(baixa)) return baixa;
      return baixa.charAt(0).toUpperCase() + baixa.slice(1);
    })
    .join(" ");
}

/** Primeiro e último nome, pra caber em chips ("Alam Guilherme Tavares Menezes" → "Alam Menezes"). */
export function nomeCurto(nome: string): string {
  const partes = nomeFormatado(nome).split(" ").filter(Boolean);
  if (partes.length <= 2) return partes.join(" ");
  const ultimo = [...partes].reverse().find((p) => !PARTICULAS.has(p.toLowerCase()));
  return `${partes[0]} ${ultimo ?? partes[partes.length - 1]}`;
}
