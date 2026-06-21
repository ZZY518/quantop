const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000/api";

export type Stock = {
  symbol: string;
  name: string;
  market: string;
  exchange: string;
  industry: string | null;
  list_date: string | null;
  status: string;
};

export type Daily = {
  symbol: string;
  trade_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  pre_close: number | null;
  change_amount: number | null;
  pct_chg: number | null;
  volume: number;
  amount: number;
};

export type ChartBar = {
  symbol: string;
  period: string;
  trade_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  amount: number;
  ma5: number | null;
  ma10: number | null;
  ma20: number | null;
  ma60: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_hist: number | null;
};

export type Factor = {
  symbol: string;
  name?: string;
  trade_date: string;
  ma5: number | null;
  ma10: number | null;
  ma20: number | null;
  ma60: number | null;
  rsi6: number | null;
  rsi12: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_hist: number | null;
  return_1d: number | null;
  return_5d: number | null;
  return_20d: number | null;
  volatility_20d: number | null;
  score_trend: number | null;
  score_momentum: number | null;
  score_risk: number | null;
  total_score: number | null;
};

export type HotRank = {
  rank: number;
  symbol: string;
  name: string;
  latest_price: number | null;
  change_amount: number | null;
  pct_chg: number | null;
  source: string;
  fetched_at: string;
};

export type SyncLog = {
  id: number;
  task_name: string;
  source: string;
  biz_date: string | null;
  status: string;
  start_time: string;
  end_time: string | null;
  total_count: number;
  success_count: number;
  fail_count: number;
  error_message: string | null;
};

export type DataSourceSettings = {
  current: string;
  options: string[];
};

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(await errorMessage(res, "GET", path));
  return res.json();
}

export async function apiPost<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { method: "POST" });
  if (!res.ok) throw new Error(await errorMessage(res, "POST", path));
  return res.json();
}

async function errorMessage(res: Response, method: string, path: string): Promise<string> {
  let detail = "";
  try {
    const body = await res.json();
    detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
  } catch {
    detail = await res.text();
  }
  return `${method} ${path} failed: ${res.status}${detail ? ` - ${detail}` : ""}`;
}

export { API_BASE };
