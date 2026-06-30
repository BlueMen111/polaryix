import type { Language } from "@/i18n/translations";

export const BRL_TO_USD = 0.2;

export function formatCurrency(value: number, locale: string, currency: "BRL" | "USD") {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function convertPriceByLocale(valueBRL: number, language: Language) {
  if (language === "en-US") {
    return {
      value: valueBRL * BRL_TO_USD,
      currency: "USD" as const,
      locale: "en-US",
      estimated: true,
    };
  }

  return {
    value: valueBRL,
    currency: "BRL" as const,
    locale: "pt-BR",
    estimated: false,
  };
}

export function formatPriceByLanguage(valueBRL: number, language: Language) {
  const price = convertPriceByLocale(valueBRL, language);
  return formatCurrency(price.value, price.locale, price.currency);
}
