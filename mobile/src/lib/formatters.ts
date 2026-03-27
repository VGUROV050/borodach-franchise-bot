// Formatting helpers for currency, numbers, dates

export function formatCurrency(value: number): string {
  return value.toLocaleString("ru-RU", {
    maximumFractionDigits: 0,
  }) + " \u20BD";
}

export function formatNumber(value: number): string {
  return value.toLocaleString("ru-RU");
}

export function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function rankChangeText(change: number): string {
  if (change > 0) return `+${change}`;
  if (change < 0) return `${change}`;
  return "=";
}

export function rankChangeColor(change: number): string {
  if (change > 0) return "#4CAF50";
  if (change < 0) return "#F44336";
  return "#9E9E9E";
}
