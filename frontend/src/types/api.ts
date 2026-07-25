/** Mirrors the backend's PaginatedResponse[T] shape (app/common/schemas.py). */
export interface ApiListEnvelope<T> {
  data: T[];
  meta: {
    total_records: number;
    total_pages: number;
    current_page: number;
    page_size: number;
    has_next: boolean;
    has_previous: boolean;
  };
}

export type ApiErrorCategory =
  | "unauthorized" // 401
  | "forbidden" // 403
  | "not_found" // 404
  | "conflict" // 409
  | "validation" // 422
  | "server" // 5xx
  | "network" // no response / timeout
  | "unknown";

/** Mirrors the backend's ErrorDetail.field_errors shape (app/common/schemas.py). */
export type ApiFieldErrors = Record<string, string[]>;

export interface ApiError {
  category: ApiErrorCategory;
  status: number | null;
  code: string;
  message: string;
  fieldErrors?: ApiFieldErrors;
  requestId?: string | null;
}
