import { api } from "./api-client";
import type {
  Country,
  IndicatorMeta,
  IndicatorData,
  ChatRequest,
  ChatResponse,
  SearchResult,
} from "@/types/api";

export const countryService = {
  list: () => api.get<Country[]>("/api/countries"),
};

export const indicatorService = {
  list: () => api.get<IndicatorMeta[]>("/api/indicators/list"),
  query: (params: {
    country_code: string;
    start_year?: number;
    end_year?: number;
  }) => {
    const search = new URLSearchParams({ country_code: params.country_code });
    if (params.start_year) search.set("start_year", String(params.start_year));
    if (params.end_year) search.set("end_year", String(params.end_year));
    return api.get<IndicatorData[]>(`/api/indicators?${search}`);
  },
  byCode: (code: string, country_code: string = "all") =>
    api.get<IndicatorData[]>(`/api/indicators/${code}?country_code=${country_code}`),
};

export const chatService = {
  send: (q: string, sessionId?: string) =>
    api.post<ChatResponse>("/api/chat", {
      query: q,
      session_id: sessionId ?? null,
    } as ChatRequest),
};

export const searchService = {
  search: (q: string, limit: number = 10) =>
    api.get<SearchResult[]>(`/api/search?q=${encodeURIComponent(q)}&limit=${limit}`),
};
