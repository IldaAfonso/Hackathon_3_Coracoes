// Formatação no padrão brasileiro. Funções puras (testadas em test/).

const LOCALE = "pt-BR";
const isMissing = (value) => value === null || value === undefined || Number.isNaN(value);

/** Proporção (0 a 1) como porcentagem: 0.1234 -> "12,3%". */
export function pct(value, digits = 1) {
  if (isMissing(value)) return "—";
  return `${(value * 100).toLocaleString(LOCALE, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}%`;
}

/** Inteiro com separador de milhar: 30481 -> "30.481". */
export function int(value) {
  if (isMissing(value)) return "—";
  return Math.round(value).toLocaleString(LOCALE);
}

/** Variação relativa com sinal: -0.28 -> "−28%". */
export function signedPct(value, digits = 0) {
  if (isMissing(value)) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${Math.abs(value * 100).toLocaleString(LOCALE, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}%`;
}

/** Data ISO (AAAA-MM-DD...) como DD/MM/AAAA, sem depender do fuso. */
export function date(iso) {
  if (!iso) return "—";
  const [year, month, day] = String(iso).slice(0, 10).split("-");
  return `${day}/${month}/${year}`;
}

/** Mês ISO como MM/AAAA. */
export function month(iso) {
  if (!iso) return "—";
  const [year, monthNumber] = String(iso).slice(0, 10).split("-");
  return `${monthNumber}/${year}`;
}

/** p-valor legível: 0.0000003 -> "< 0,001". */
export function pValue(value) {
  if (isMissing(value)) return "—";
  if (value < 0.001) return "< 0,001";
  return value.toLocaleString(LOCALE, { minimumFractionDigits: 3, maximumFractionDigits: 3 });
}

/** Singular ou plural: plural(1, "dia", "dias") -> "1 dia". */
export function plural(count, one, many) {
  return `${int(count)} ${Math.round(count) === 1 ? one : many}`;
}

/** Número decimal curto: 0.7 -> "0,70". */
export function decimal(value, digits = 2) {
  if (isMissing(value)) return "—";
  return value.toLocaleString(LOCALE, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}
