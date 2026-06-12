export type TaginfoStat = { type: string; count: number };

export type TaginfoValue = { value: string; count: number };

export type TaginfoCombination = {
  other_key: string;
  other_value?: string;
  together_count: number;
};

export async function fetchTaginfoJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
}

export function countTaginfoStat(rows: TaginfoStat[], type: string): number {
  return rows.find((row) => row.type === type)?.count ?? 0;
}

export function countTaginfoValue(rows: TaginfoValue[], value: string): number {
  return rows.find((row) => row.value === value)?.count ?? 0;
}

export function countTaginfoCombination(
  rows: TaginfoCombination[],
  key: string,
  value = "",
): number {
  return rows
    .filter((row) => row.other_key === key && (row.other_value ?? "") === value)
    .reduce((sum, row) => sum + row.together_count, 0);
}

export function fmt(n: number): string {
  return new Intl.NumberFormat("en").format(n);
}

export function pct(part: number, total: number): string {
  if (!total) return "0%";
  return `${Math.round((part / total) * 100)}%`;
}

export function countPct(part: number, total: number): string {
  return `${fmt(part)} (${pct(part, total)})`;
}

export function remainder(total: number, ...parts: number[]): number {
  return Math.max(0, total - parts.reduce((sum, part) => sum + part, 0));
}
