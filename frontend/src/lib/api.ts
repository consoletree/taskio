import type {
  TicketWithClassification,
  PaginatedTickets,
  Ticket,
  ClassificationResult,
  AnalyticsOverview,
  HealthStatus,
  CreateTicketRequest,
  CorrectTicketRequest,
  TicketCategory,
} from "@/types";

const API_URL = "http://localhost:8000";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        error.detail || `HTTP ${response.status}`
      );
    }

    return response.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(0, "Network error - is the backend running?");
  }
}

// Tickets API

export async function createTicket(
  data: CreateTicketRequest
): Promise<TicketWithClassification> {
  return fetchApi<TicketWithClassification>("/api/tickets", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getTickets(
  page = 1,
  limit = 10,
  status?: string,
  category?: string
): Promise<PaginatedTickets> {
  const params = new URLSearchParams({
    page: String(page),
    limit: String(limit),
  });

  if (status) params.set("status", status);
  if (category) params.set("category", category);

  return fetchApi<PaginatedTickets>(`/api/tickets?${params}`);
}

export async function getTicket(id: string): Promise<Ticket> {
  return fetchApi<Ticket>(`/api/tickets/${id}`);
}

export async function correctTicket(
  id: string,
  data: CorrectTicketRequest
): Promise<Ticket> {
  return fetchApi<Ticket>(`/api/tickets/${id}/correct`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function classifyOnly(
  data: CreateTicketRequest
): Promise<ClassificationResult> {
  return fetchApi<ClassificationResult>("/api/tickets/classify-only", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getCategories(): Promise<{
  categories: TicketCategory[];
  count: number;
}> {
  return fetchApi("/api/tickets/categories");
}

// Analytics API

export async function getAnalytics(): Promise<AnalyticsOverview> {
  return fetchApi<AnalyticsOverview>("/api/analytics/overview");
}

export async function getCacheStats(): Promise<{
  connected: boolean;
  hits?: number;
  misses?: number;
  hit_rate?: number;
}> {
  return fetchApi("/api/analytics/cache");
}

export async function getVectorStats(): Promise<{
  connected: boolean;
  count?: number;
  categories?: Record<string, number>;
}> {
  return fetchApi("/api/analytics/vector-store");
}

// Health API

export async function getHealth(): Promise<HealthStatus> {
  return fetchApi<HealthStatus>("/health");
}

export async function checkBackendConnection(): Promise<boolean> {
  try {
    await fetchApi("/health/live");
    return true;
  } catch {
    return false;
  }
}
