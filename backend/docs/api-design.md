# API Design — Intelligent Data Platform (IDP)

> **Status: Design / Blueprint.** Target API specification. Implementation pending (Phase 5).

---

## 1. Base URL & Versioning

```
Base: http://<server>:8000
Prefix: /api/v1
Docs: http://<server>:8000/docs (OpenAPI)
```

---

## 2. Common Response Envelope

```json
{
  "data": {},
  "meta": {
    "total": 320,
    "page": 1,
    "page_size": 50
  },
  "error": null
}
```

Error response:

```json
{
  "data": null,
  "meta": null,
  "error": {
    "code": "NOT_FOUND",
    "message": "Country code 'XYZ' not found"
  }
}
```

---

## 3. Endpoints

### 3.1 Health

```
GET /health
```

Response: `{"status": "ok", "version": "0.1.0", "services": {"postgres": "up", "minio": "up"}}`

---

### 3.2 Indicators

#### List indicators with filters

```
GET /api/v1/indicators?country_code=VNM&start_year=2020&end_year=2024&indicator_codes=NY.GDP.MKTP.CD,FP.CPI.TOTL.ZG&page=1&page_size=50
```

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `country_code` | string | Yes | ISO 3-letter code (e.g., `VNM`, `THA`) or `all` |
| `start_year` | integer | No | Filter from year (default: 2000) |
| `end_year` | integer | No | Filter to year (default: current year) |
| `indicator_codes` | string | No | Comma-separated list of indicator codes |
| `source_system` | string | No | Filter by source: `world_bank`, `nso_vietnam`, `fred`, or `all` (default: auto-select authoritative) |
| `category` | string | No | Indicator category filter |
| `page` | integer | No | Page number (default: 1) |
| `page_size` | integer | No | Items per page (default: 50, max: 200) |

**Response:**

```json
{
  "data": [
    {
      "indicator_code": "NY.GDP.MKTP.CD",
      "indicator_name": "GDP (current US$)",
      "source_system": "world_bank",
      "category": "gdp",
      "unit": "USD",
      "country_code": "VNM",
      "country_name": "Vietnam",
      "year": 2023,
      "value": 433700000000.0,
      "loaded_at": "2026-05-18T06:00:00Z"
    }
  ],
  "meta": {
    "total": 25,
    "page": 1,
    "page_size": 50
  }
}
```

#### Get time series for one indicator

```
GET /api/v1/indicators/{indicator_code}?country_code=VNM&start_year=2000&end_year=2024
```

Response: Same structure, data is array of yearly values sorted by year.

---

### 3.3 Countries

```
GET /api/v1/countries
```

**Response:**

```json
{
  "data": [
    {
      "country_code": "VNM",
      "country_name": "Vietnam",
      "region": "East Asia & Pacific",
      "income_group": "Lower-middle",
      "is_asean": true,
      "is_primary": true
    }
  ]
}
```

```
GET /api/v1/countries/{country_code}
```

Returns single country object.

---

### 3.4 Indicator Catalog

```
GET /api/v1/indicators/list?category=gdp
```

**Response:**

```json
{
  "data": [
    {
      "indicator_code": "NY.GDP.MKTP.CD",
      "indicator_name": "GDP (current US$)",
      "category": "gdp",
      "unit": "USD",
      "frequency": "annual",
      "description": "Gross Domestic Product at current US dollars"
    }
  ]
}
```

---

### 3.5 Search

```
GET /api/v1/search?q=GDP+Vietnam+inflation&limit=10
```

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `q` | string | Yes | Search query |
| `limit` | integer | No | Max results (default: 10, max: 50) |
| `type` | string | No | `indicators`, `documents`, or `all` (default) |

**Response:**

```json
{
  "data": [
    {
      "type": "indicator",
      "id": "NY.GDP.MKTP.CD",
      "title": "GDP (current US$)",
      "description": "Gross Domestic Product at current US dollars...",
      "score": 0.92,
      "source": "World Bank"
    },
    {
      "type": "document",
      "id": "doc_12345",
      "title": "Vietnam Economic Outlook 2024",
      "abstract": "This report analyzes...",
      "score": 0.87,
      "source": "World Bank Documents",
      "pdf_url": "https://..."
    }
  ]
}
```

---

### 3.6 Chatbot (WebSocket)

```
WS /api/v1/chat
```

**Client → Server:**

```json
{"type": "query", "session_id": "uuid-optional", "query": "GDP của Việt Nam năm 2023?", "model": "gemini-2.0-flash"}
```

**Server → Client (streaming):**

```json
{"type": "token", "data": "GDP"}
{"type": "token", "data": " của"}
{"type": "token", "data": " Việt"}
...
{"type": "citation", "refs": ["Doc_1", "Doc_3"]}
{"type": "done", "tokens_used": 512, "session_id": "uuid"}
{"type": "error", "message": "..."}
```

### 3.7 Chatbot (REST fallback)

```
POST /api/v1/chat
```

**Request:**

```json
{
  "query": "GDP của Việt Nam năm 2023?",
  "session_id": "uuid-optional",
  "model": "gemini-2.0-flash",
  "stream": false
}
```

**Response (non-streaming):**

```json
{
  "data": {
    "session_id": "uuid",
    "response": "GDP của Việt Nam năm 2023 đạt 433.7 tỷ USD [Doc_1]...",
    "citations": [
      {"ref": "Doc_1", "source": "World Bank", "indicator": "NY.GDP.MKTP.CD"}
    ],
    "tokens_used": 512,
    "follow_up_questions": ["Lạm phát cùng năm?", "So sánh với Thái Lan?"]
  }
}
```

---

## 4. Error Codes

| HTTP Status | Code | Description |
|---|---|---|
| 400 | `BAD_REQUEST` | Invalid parameters |
| 404 | `NOT_FOUND` | Resource not found |
| 422 | `VALIDATION_ERROR` | Request body validation failed |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Unexpected server error |
| 503 | `SERVICE_UNAVAILABLE` | Upstream service down (DB, ES, Neo4j) |

---

## 5. Rate Limiting

| Client | Limit | Window |
|---|---|---|
| Anonymous | 30 requests | per minute |
| Authenticated | 120 requests | per minute |
| Chatbot (WebSocket) | 10 messages | per minute |
| Chatbot (REST) | 5 requests | per minute |

Implemented via Redis in Phase 5. Returns `429` with `Retry-After` header.

---

## 6. Authentication (Phase 6+)

- API key via `X-API-Key` header for service-to-service
- JWT via `Authorization: Bearer <token>` for user-facing apps
- Not required in Phase 5 (internal-only deployment)

---

## 7. CORS

Internal-only deployment in Phase 5; CORS allow-list is empty by default. When a consumer (Jupyter notebook, BI tool, etc.) is added later, add its origin explicitly.

---

## 8. WebSocket Protocol Details

- Heartbeat: ping/pong every 30s
- Reconnect: client should reconnect with same `session_id`
- Max message size: 4KB (query)
- Session timeout: 30 min idle → session closed
- Max concurrent sessions per user: 3
