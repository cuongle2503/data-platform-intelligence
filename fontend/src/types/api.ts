export interface Country {
  country_code: string;
  country_name: string;
  region?: string;
  income_group?: string;
}

export interface IndicatorMeta {
  indicator_code: string;
  indicator_name: string;
  category?: string;
  unit?: string;
  description?: string;
}

export interface IndicatorData {
  indicator_code: string;
  indicator_name: string;
  country_code: string;
  year: number;
  value: number;
  category?: string;
  source_system: string;
}

export interface ChatRequest {
  query: string;
  session_id?: string | null;
}

export interface ChatResponse {
  session_id: string;
  query: string;
  response: string;
}

export interface SearchResult {
  id: string;
  score: number;
  source: Record<string, any>;
}
