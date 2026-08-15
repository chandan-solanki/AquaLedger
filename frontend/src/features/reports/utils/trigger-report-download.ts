/**
 * Triggers a real browser download via a BFF export proxy (TASKS.md
 * Sprint 11 Session 5 Phases B/C). A plain anchor click, not fetch+blob -
 * the browser handles the backend's `Content-Disposition: attachment`
 * header natively, and the BFF route is same-origin so the session's
 * httpOnly cookies ride along automatically, exactly like every other
 * authenticated navigation.
 *
 * `params` is the same snake_case wire object the caller already builds
 * for its own data query (e.g. `toFishSalesParams(filters)`) - reused as
 * -is rather than re-derived, so there is only one place per report/
 * statement that knows how filter state maps onto query params.
 */
function buildDownloadUrl(path: string, query: Record<string, string>, params: object): string {
  const searchParams = new URLSearchParams(query);
  for (const [key, value] of Object.entries(params as Record<string, unknown>)) {
    if (value === null || value === undefined || value === "") continue;
    searchParams.set(key, String(value));
  }
  return `${path}?${searchParams.toString()}`;
}

function downloadUrl(url: string): void {
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
}

/**
 * `report=...&format=...` via `/api/reports/export` - one endpoint for
 * all 9 existing reports (Phase B). `page`/`page_size` may be present in
 * `params`; the backend ignores both (an export always contains every
 * matching row, never one page of it).
 */
export function triggerReportDownload(
  reportType: string,
  format: "csv" | "excel" | "pdf",
  params: object
): void {
  downloadUrl(buildDownloadUrl("/api/reports/export", { report: reportType, format }, params));
}

/**
 * `format=...` via `/api/reports/customer-statement` or `/supplier-
 * statement` (Phase C) - a formal business document, not a report, so it
 * gets its own dedicated BFF route rather than going through the generic
 * `/api/reports/export`. CSV is never a valid statement format - the
 * backend rejects it with a clean 422, so the type here only offers
 * "excel"/"pdf".
 */
export function triggerStatementDownload(
  statementType: "customer" | "supplier",
  format: "excel" | "pdf",
  params: object
): void {
  downloadUrl(buildDownloadUrl(`/api/reports/${statementType}-statement`, { format }, params));
}
