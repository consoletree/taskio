// API Response Types

export type TicketCategory =
  | "Product Issue"
  | "Software Issue"
  | "Network Issue"
  | "Battery Issue"
  | "General Question";

export type TicketStatus = "open" | "classified" | "corrected" | "resolved";

export interface SimilarTicket {
  id: string;
  category: string | null;
  similarity: number;
}

export interface ClassificationResult {
  category: TicketCategory;
  confidence: number;
  reasoning: string;
  key_indicators: string[];
  similar_tickets: SimilarTicket[];
  latency_ms: number;
  cached: boolean;
  rag_used: boolean;
}

export interface Ticket {
  id: string;
  title: string;
  description: string;
  predicted_category: TicketCategory | null;
  actual_category: TicketCategory | null;
  confidence_score: number | null;
  reasoning: string | null;
  status: TicketStatus;
  created_at: string;
  updated_at: string;
}

export interface TicketWithClassification {
  ticket: Ticket;
  classification: ClassificationResult;
}

export interface PaginatedTickets {
  tickets: Ticket[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

// Analytics Types

export interface CategoryStat {
  category: string;
  count: number;
  percentage: number;
}

export interface AccuracyStats {
  total_reviewed: number;
  correct_predictions: number;
  accuracy_percentage: number;
}

export interface AnalyticsOverview {
  total_tickets: number;
  accuracy: AccuracyStats;
  category_distribution: CategoryStat[];
  avg_confidence: number;
  cache_hit_rate: number;
  vector_store_count: number;
}

// Health Types

export interface ServiceHealth {
  name: string;
  status: "healthy" | "unhealthy";
  details?: Record<string, unknown>;
}

export interface HealthStatus {
  status: "healthy" | "degraded";
  services: ServiceHealth[];
  version: string;
}

// Request Types

export interface CreateTicketRequest {
  title?: string;
  description: string;
}

export interface CorrectTicketRequest {
  corrected_category: TicketCategory;
  feedback?: string;
}
