/** Mirrors the backend's ExpenseType enum (app/modules/trip_expenses/constants.py). */
export type ExpenseType =
  | "diesel"
  | "ice"
  | "food"
  | "labour"
  | "harbour"
  | "maintenance"
  | "repair"
  | "permit"
  | "other";

/**
 * Raw backend shape (snake_case), matching TripExpenseResponse
 * (app/modules/trip_expenses/schemas.py) exactly. `amount` is a string -
 * the backend serializes `Decimal` as a JSON string, never a float
 * (ARCHITECTURE.md §5.1), and the client keeps that representation rather
 * than parsing into a JS number.
 */
export interface BackendTripExpense {
  id: string;
  tenant_id: string;
  trip_id: string;
  expense_type: ExpenseType;
  amount: string;
  expense_date: string;
  description: string | null;
  vendor_name: string | null;
  receipt_number: string | null;
  created_at: string;
  updated_at: string;
}

/** The client-facing, camelCase shape every trip-expense-service.ts function returns. */
export interface TripExpense {
  id: string;
  tenantId: string;
  tripId: string;
  expenseType: ExpenseType;
  amount: string;
  expenseDate: string;
  description: string | null;
  vendorName: string | null;
  receiptNumber: string | null;
  createdAt: string;
  updatedAt: string;
}

export function mapBackendTripExpense(tripExpense: BackendTripExpense): TripExpense {
  return {
    id: tripExpense.id,
    tenantId: tripExpense.tenant_id,
    tripId: tripExpense.trip_id,
    expenseType: tripExpense.expense_type,
    amount: tripExpense.amount,
    expenseDate: tripExpense.expense_date,
    description: tripExpense.description,
    vendorName: tripExpense.vendor_name,
    receiptNumber: tripExpense.receipt_number,
    createdAt: tripExpense.created_at,
    updatedAt: tripExpense.updated_at,
  };
}

/**
 * Query params for GET /trip-expenses (app/modules/trip_expenses/schemas.py's
 * TripExpenseListParams) - snake_case to match the wire format exactly.
 * `use-trip-expenses.ts` only ever populates `trip_id`/`page`/`page_size`
 * this session - the `q`/`expense_type`/date-range filters the backend
 * already supports are left unwired since Trip Expenses has no filter UI
 * here (a bounded, read-only sub-table scoped to one trip, not a list page).
 */
export interface TripExpenseListParams {
  q?: string;
  trip_id?: string;
  expense_type?: ExpenseType;
  expense_date_from?: string;
  expense_date_to?: string;
  sort?: string;
  page: number;
  page_size: number;
}

/**
 * Request body for POST /trip-expenses (TripExpenseCreateRequest,
 * app/modules/trip_expenses/schemas.py) - snake_case to match the wire
 * format exactly. `trip_id`, `expense_type`, `amount` and `expense_date`
 * are required; every other field is optional.
 */
export interface TripExpenseCreateRequest {
  trip_id: string;
  expense_type: ExpenseType;
  amount: string;
  expense_date: string;
  description?: string;
  vendor_name?: string;
  receipt_number?: string;
}

/** Request body for PUT /trip-expenses/{id} (TripExpenseUpdateRequest) - a partial update, only present fields change. */
export interface TripExpenseUpdateRequest {
  trip_id?: string;
  expense_type?: ExpenseType;
  amount?: string;
  expense_date?: string;
  description?: string;
  vendor_name?: string;
  receipt_number?: string;
}
