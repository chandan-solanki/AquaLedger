import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DataTable, useDataTable } from "@/components/data-table";
import { getInvoiceItemColumns } from "@/features/invoices/components/invoice-item-columns";
import type { Fish } from "@/features/fish";
import type { InvoiceItem } from "@/features/invoices/types/invoice-item";
import type { TripCatchOtherInvoiceUsage } from "@/features/invoices/types/trip-catch-other-invoice-usage";

const FISH_BY_ID = new Map<string, Fish>([
  ["fish-1", { id: "fish-1", name: "Pomfret", unit: "kg" } as Fish],
]);

const { hasPermissionMock, getTripCatchConflictsMock } = vi.hoisted(() => ({
  hasPermissionMock: vi.fn(() => true),
  getTripCatchConflictsMock: vi.fn(),
}));

vi.mock("@/features/auth/hooks/use-permissions", () => ({
  usePermissions: () => ({ hasPermission: hasPermissionMock }),
}));

vi.mock("@/features/invoices/services/invoice-service", () => ({
  invoiceService: { getTripCatchConflicts: getTripCatchConflictsMock },
}));

const ITEM: InvoiceItem = {
  id: "item-1",
  tenantId: "tenant-1",
  invoiceId: "invoice-current",
  lineNumber: 1,
  fishId: "fish-1",
  tripCatchId: "catch-1",
  description: "Pomfret - Grade A",
  quantity: "10.000",
  unit: "kg",
  rate: "100.0000",
  discountPercent: "0.00",
  discountAmount: "0.00",
  taxableAmount: "1000.00",
  taxRate: "0.00",
  taxAmount: "0.00",
  lineTotal: "1000.00",
  createdAt: "2026-07-22T00:00:00Z",
  updatedAt: "2026-07-22T00:00:00Z",
};

const OTHER_ITEM: InvoiceItem = { ...ITEM, id: "item-2", tripCatchId: "catch-2" };

function usageEntry(overrides: Partial<TripCatchOtherInvoiceUsage> = {}): TripCatchOtherInvoiceUsage {
  return {
    tripCatchId: "catch-1",
    otherInvoiceCount: 0,
    otherDraftQuantity: "0.000",
    otherConsumedQuantity: "0.000",
    ...overrides,
  };
}

function renderColumns(
  items: InvoiceItem[] = [ITEM],
  usageByTripCatchId?: Map<string, TripCatchOtherInvoiceUsage>,
  isUsageLoading = false
) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function Harness() {
    const columns = getInvoiceItemColumns(
      () => [],
      FISH_BY_ID,
      "invoice-current",
      usageByTripCatchId,
      isUsageLoading
    );
    const table = useDataTable({ data: items, columns });
    return <DataTable table={table} aria-label="Invoice items" />;
  }
  return render(
    <QueryClientProvider client={queryClient}>
      <Harness />
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  hasPermissionMock.mockReturnValue(true);
  getTripCatchConflictsMock.mockResolvedValue({
    tripCatchId: "catch-1",
    requiredQuantity: null,
    availableQuantity: "100.000",
    shortfallQuantity: null,
    conflictingInvoices: [],
  });
});

describe("getInvoiceItemColumns Other Invoice Usage indicator (Sprint 15 Session 8)", () => {
  it("shows a dash when a catch has no usage entry", () => {
    renderColumns([ITEM], new Map());
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("shows a dash when the usage summary is unavailable (e.g. the fetch failed)", () => {
    renderColumns([ITEM], undefined, false);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("shows a loading placeholder while usage is being fetched", () => {
    renderColumns([ITEM], undefined, true);
    expect(screen.getByText("…")).toBeInTheDocument();
    expect(screen.queryByText("—")).not.toBeInTheDocument();
  });

  it("shows a dash for an item with no trip catch reference, regardless of loading state", () => {
    const noCatchItem: InvoiceItem = { ...ITEM, tripCatchId: null };
    renderColumns([noCatchItem], undefined, true);
    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.queryByText("…")).not.toBeInTheDocument();
  });

  it("shows the other-invoice count using 'other' wording, never a bare count", () => {
    const usage = new Map([["catch-1", usageEntry({ otherInvoiceCount: 2 })]]);
    renderColumns([ITEM], usage);
    expect(screen.getByText("2 other invoices")).toBeInTheDocument();
    expect(screen.queryByText("2 invoices")).not.toBeInTheDocument();
  });

  it("uses singular phrasing for exactly one other invoice", () => {
    const usage = new Map([["catch-1", usageEntry({ otherInvoiceCount: 1 })]]);
    renderColumns([ITEM], usage);
    expect(screen.getByText("1 other invoice")).toBeInTheDocument();
  });

  it("shows draft and consumed quantities when both are non-zero", () => {
    const usage = new Map([
      [
        "catch-1",
        usageEntry({ otherInvoiceCount: 2, otherDraftQuantity: "20.000", otherConsumedQuantity: "40.000" }),
      ],
    ]);
    renderColumns([ITEM], usage);
    expect(screen.getByText("20.000 kg draft · 40.000 kg consumed")).toBeInTheDocument();
  });

  it("shows only the draft portion when consumed is zero", () => {
    const usage = new Map([
      ["catch-1", usageEntry({ otherInvoiceCount: 1, otherDraftQuantity: "20.000" })],
    ]);
    renderColumns([ITEM], usage);
    expect(screen.getByText("20.000 kg draft")).toBeInTheDocument();
    expect(screen.queryByText(/consumed/)).not.toBeInTheDocument();
  });

  it("omits the detail line entirely when both quantities are zero", () => {
    const usage = new Map([["catch-1", usageEntry({ otherInvoiceCount: 1 })]]);
    renderColumns([ITEM], usage);
    expect(screen.queryByText(/draft/)).not.toBeInTheDocument();
    expect(screen.queryByText(/consumed/)).not.toBeInTheDocument();
  });

  it("never labels usage as Reserved or Committed Stock", () => {
    const usage = new Map([
      ["catch-1", usageEntry({ otherInvoiceCount: 1, otherDraftQuantity: "20.000" })],
    ]);
    renderColumns([ITEM], usage);
    expect(screen.queryByText(/reserved/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/committed/i)).not.toBeInTheDocument();
  });

  it("associates each item's own trip catch with its own usage entry independently", () => {
    const usage = new Map([
      ["catch-1", usageEntry({ otherInvoiceCount: 2 })],
      ["catch-2", usageEntry({ tripCatchId: "catch-2", otherInvoiceCount: 0 })],
    ]);
    renderColumns([ITEM, OTHER_ITEM], usage);
    expect(screen.getByText("2 other invoices")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders the count as plain, non-interactive text without invoice:view", () => {
    hasPermissionMock.mockReturnValue(false);
    const usage = new Map([["catch-1", usageEntry({ otherInvoiceCount: 2 })]]);
    renderColumns([ITEM], usage);
    expect(screen.getByText("2 other invoices")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /View other invoices/ })).not.toBeInTheDocument();
  });

  it("opens a dialog listing the referencing invoices, excluding the current invoice, when clicked with invoice:view", async () => {
    getTripCatchConflictsMock.mockResolvedValue({
      tripCatchId: "catch-1",
      requiredQuantity: null,
      availableQuantity: "100.000",
      shortfallQuantity: null,
      conflictingInvoices: [
        {
          invoiceId: "other-invoice-1",
          invoiceNumber: "INV/2026-27/00025",
          status: "issued",
          invoiceDate: "2026-07-22",
          companyName: "ABC Traders",
          quantity: "40.000",
        },
      ],
    });
    const usage = new Map([
      ["catch-1", usageEntry({ otherInvoiceCount: 1, otherConsumedQuantity: "40.000" })],
    ]);
    const user = userEvent.setup();
    renderColumns([ITEM], usage);

    await user.click(screen.getByRole("button", { name: /View other invoices/ }));

    expect(await screen.findByText("Invoices referencing this catch")).toBeInTheDocument();
    await waitFor(() =>
      expect(getTripCatchConflictsMock).toHaveBeenCalledWith("catch-1", {
        excludeInvoiceId: "invoice-current",
        requiredQuantity: undefined,
      })
    );
    const link = await screen.findByRole("link", { name: "View" });
    expect(link).toHaveAttribute("href", "/invoices/other-invoice-1");
  });
});
