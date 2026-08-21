import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { FishStockDetailPage } from "@/features/fish-stock/pages/fish-stock-detail-page";

const { hasPermissionMock, useFishStockDetailMock, useTripCatchInvoiceUsageSummaryMock } = vi.hoisted(() => ({
  hasPermissionMock: vi.fn(() => true),
  useFishStockDetailMock: vi.fn(),
  useTripCatchInvoiceUsageSummaryMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ fishId: "fish-1" }),
  usePathname: () => "/fish-stock/fish-1",
}));

vi.mock("@/features/auth/hooks/use-permissions", () => ({
  usePermissions: () => ({ hasPermission: hasPermissionMock }),
}));

vi.mock("@/features/fish-stock/hooks/use-fish-stock-detail", () => ({
  useFishStockDetail: useFishStockDetailMock,
}));

vi.mock("@/features/invoices/hooks/use-trip-catch-invoice-usage-summary", () => ({
  useTripCatchInvoiceUsageSummary: useTripCatchInvoiceUsageSummaryMock,
}));

const DETAIL = {
  fishId: "fish-1",
  fishName: "Pomfret",
  unit: "kg" as const,
  totalCaught: "180.000",
  totalSold: "60.000",
  totalAvailable: "120.000",
  totalWaste: "0.000",
  catches: [
    {
      tripCatchId: "catch-1",
      tripId: "trip-1",
      tripNumber: "TRIP-2026-0042",
      landingDate: "2026-07-22",
      quantityCaught: "180.000",
      soldQuantity: "60.000",
      availableQuantity: "120.000",
      wasteQuantity: "0.000",
    },
  ],
};

function mockDetailQuery(overrides: Partial<ReturnType<typeof useFishStockDetailMock>> = {}) {
  useFishStockDetailMock.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  hasPermissionMock.mockReturnValue(true);
  useTripCatchInvoiceUsageSummaryMock.mockReturnValue({ data: [], isLoading: false });
});

describe("FishStockDetailPage", () => {
  it("shows a permission error and never fetches the record's content when the user lacks fish:view", () => {
    hasPermissionMock.mockReturnValue(false);
    mockDetailQuery({ data: DETAIL });

    render(<FishStockDetailPage />);

    expect(screen.getByText("You don't have permission to view fish stock")).toBeInTheDocument();
    expect(screen.queryByText("Pomfret")).not.toBeInTheDocument();
  });

  it("renders the fish name, unit, totals and contributing catches", () => {
    mockDetailQuery({ data: DETAIL });

    render(<FishStockDetailPage />);

    expect(screen.getByRole("heading", { name: "Pomfret" })).toBeInTheDocument();
    expect(screen.getByText("TRIP-2026-0042")).toBeInTheDocument();
    expect(screen.getAllByText("Kg").length).toBeGreaterThan(0);
  });

  it("emphasizes Available as the primary operational number", () => {
    mockDetailQuery({ data: DETAIL });

    render(<FishStockDetailPage />);

    expect(screen.getByText("How much of this fish can still be sold.")).toBeInTheDocument();
    // The figure appears twice - once prominently, once in the plain summary list - and the
    // prominent one carries the large, accented styling this requirement is actually about.
    const occurrences = screen.getAllByText("120.000 Kg");
    expect(occurrences.length).toBe(2);
    expect(occurrences.some((el) => el.className.includes("text-4xl"))).toBe(true);
  });

  it("shows a Not Found state for an unknown fish, distinct from a generic failure", () => {
    mockDetailQuery({
      isError: true,
      error: { category: "not_found", status: 404, code: "FISH_STOCK_FISH_NOT_FOUND", message: "Fish not found" },
    });

    render(<FishStockDetailPage />);

    expect(screen.getByText("Fish not found")).toBeInTheDocument();
    expect(screen.queryByText("Failed to load fish stock")).not.toBeInTheDocument();
  });

  it("shows a generic retryable error for a non-404 failure", () => {
    const refetch = vi.fn();
    mockDetailQuery({
      isError: true,
      error: { category: "server", status: 500, code: "INTERNAL_ERROR", message: "Something broke" },
      refetch,
    });

    render(<FishStockDetailPage />);

    expect(screen.getByText("Failed to load fish stock")).toBeInTheDocument();
    expect(screen.getByText("Something broke")).toBeInTheDocument();
  });

  it("renders a loading state before the record arrives", () => {
    mockDetailQuery({ isLoading: true });

    render(<FishStockDetailPage />);

    expect(screen.queryByText("Pomfret")).not.toBeInTheDocument();
  });

  it("requests invoice usage for exactly the fish's own contributing catches (Sprint 15 Session 7)", () => {
    mockDetailQuery({ data: DETAIL });

    render(<FishStockDetailPage />);

    expect(useTripCatchInvoiceUsageSummaryMock).toHaveBeenCalledWith(["catch-1"]);
  });

  it("still renders Contributing Catches normally when the usage summary fetch fails", () => {
    mockDetailQuery({ data: DETAIL });
    useTripCatchInvoiceUsageSummaryMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });

    render(<FishStockDetailPage />);

    expect(screen.getByText("TRIP-2026-0042")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
