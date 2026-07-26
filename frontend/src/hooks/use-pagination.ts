import { useMemo, useState } from "react";

export interface UsePaginationOptions {
  totalCount: number;
  /** 1-based, matching `components/pagination/`'s convention throughout. @defaultValue 1 */
  initialPage?: number;
  /** @defaultValue 25 */
  initialPageSize?: number;
}

export interface UsePaginationResult {
  page: number;
  pageSize: number;
  totalPages: number;
  /** The 1-based index of the first row on the current page (0 when `totalCount` is 0). */
  from: number;
  /** The 1-based index of the last row on the current page. */
  to: number;
  setPage: (page: number) => void;
  /** Resets to page 1 — changing how many rows fit per page invalidates whatever "page 7" meant under the old size. */
  setPageSize: (pageSize: number) => void;
  nextPage: () => void;
  previousPage: () => void;
  firstPage: () => void;
  lastPage: () => void;
  canNext: boolean;
  canPrevious: boolean;
}

/**
 * Local page/page-size state for a paginated list — no fetching, no URL
 * sync, no business logic. The owning feature still supplies `totalCount`
 * (from its own query) and reacts to `page`/`pageSize` changing to actually
 * fetch the next page; this hook only tracks "what page am I asking for."
 */
export function usePagination({
  totalCount,
  initialPage = 1,
  initialPageSize = 25,
}: UsePaginationOptions): UsePaginationResult {
  const [page, setPageRaw] = useState(initialPage);
  const [pageSize, setPageSizeRaw] = useState(initialPageSize);

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const clampedPage = Math.min(Math.max(page, 1), totalPages);

  const { from, to } = useMemo(() => {
    if (totalCount === 0) return { from: 0, to: 0 };
    const start = (clampedPage - 1) * pageSize + 1;
    const end = Math.min(totalCount, clampedPage * pageSize);
    return { from: start, to: end };
  }, [clampedPage, pageSize, totalCount]);

  function setPage(next: number) {
    setPageRaw(Math.min(Math.max(next, 1), totalPages));
  }

  function setPageSize(nextSize: number) {
    setPageSizeRaw(nextSize);
    setPageRaw(1);
  }

  return {
    page: clampedPage,
    pageSize,
    totalPages,
    from,
    to,
    setPage,
    setPageSize,
    nextPage: () => setPage(clampedPage + 1),
    previousPage: () => setPage(clampedPage - 1),
    firstPage: () => setPage(1),
    lastPage: () => setPage(totalPages),
    canNext: clampedPage < totalPages,
    canPrevious: clampedPage > 1,
  };
}
