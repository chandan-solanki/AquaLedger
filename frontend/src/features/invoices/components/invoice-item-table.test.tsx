import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InvoiceItemTable } from "@/features/invoices/components/invoice-item-table";

const {
  hasPermissionMock,
  useFishOptionsMock,
  getTripCatchMock,
  listInvoiceItemsMock,
  useInvoiceTripCatchConflictsMock,
  getTripCatchConflictsMock,
} = vi.hoisted(() => ({
  hasPermissionMock: vi.fn(() => true),
  useFishOptionsMock: vi.fn(),
  getTripCatchMock: vi.fn(),
  listInvoiceItemsMock: vi.fn(),
  useInvoiceTripCatchConflictsMock: vi.fn(),
  getTripCatchConflictsMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/features/auth/hooks/use-permissions", () => ({
  usePermissions: () => ({ hasPermission: hasPermissionMock }),
}));

vi.mock("@/features/trips", () => ({
  tripCatchService: { getTripCatch: getTripCatchMock },
  useFishOptions: useFishOptionsMock,
}));

vi.mock("@/features/invoices/services/invoice-item-service", () => ({
  invoiceItemService: {
    listInvoiceItems: listInvoiceItemsMock,
    createInvoiceItem: vi.fn(),
    updateInvoiceItem: vi.fn(),
    deleteInvoiceItem: vi.fn(),
  },
}));

vi.mock("@/features/invoices/services/invoice-service", () => ({
  invoiceService: { getTripCatchConflicts: getTripCatchConflictsMock },
}));

vi.mock("@/features/invoices/hooks/use-invoice-trip-catch-conflicts", () => ({
  useInvoiceTripCatchConflicts: useInvoiceTripCatchConflictsMock,
}));

const FISH = { id: "fish-1", name: "Pomfret", unit: "kg" as const };

const ITEM_A = {
  id: "item-1",
  tenantId: "tenant-1",
  invoiceId: "invoice-1",
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

function renderTable(props: Partial<React.ComponentProps<typeof InvoiceItemTable>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <InvoiceItemTable invoiceId="invoice-1" invoiceStatus="draft" {...props} />
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  hasPermissionMock.mockReturnValue(true);
  useFishOptionsMock.mockReturnValue({
    options: [{ value: FISH.id, label: FISH.name }],
    fishById: new Map([[FISH.id, FISH]]),
    isLoading: false,
  });
  listInvoiceItemsMock.mockResolvedValue([ITEM_A]);
  useInvoiceTripCatchConflictsMock.mockReturnValue({ data: [], isLoading: false, isError: false });
  getTripCatchConflictsMock.mockResolvedValue({
    tripCatchId: "catch-1",
    requiredQuantity: null,
    availableQuantity: "100.000",
    shortfallQuantity: null,
    conflictingInvoices: [],
  });
});

describe("InvoiceItemTable (Sprint 15 Session 8 - Other Invoice Usage integration)", () => {
  it("renders the existing item list and columns unchanged", async () => {
    renderTable();

    expect(await screen.findByText("Pomfret")).toBeInTheDocument();
    expect(screen.getByText("Pomfret - Grade A")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Other Invoice Usage" })).toBeInTheDocument();
  });

  it("requests the page-level usage summary for this invoice, not per item", async () => {
    renderTable();

    await screen.findByText("Pomfret");
    // Called once per render (a normal hook, re-invoked like any other) but always with the
    // SAME single invoiceId argument, never once per row/item - that's the N+1 this session forbids.
    expect(useInvoiceTripCatchConflictsMock.mock.calls.every((call) => call[0] === "invoice-1")).toBe(
      true
    );
  });

  it("shows a dash for the Other Invoice Usage cell while the summary is loading", async () => {
    useInvoiceTripCatchConflictsMock.mockReturnValue({ data: undefined, isLoading: true, isError: false });
    renderTable();

    await screen.findByText("Pomfret");
    expect(screen.getByText("…")).toBeInTheDocument();
  });

  it("does not crash and still renders the item list when the usage summary fetch fails", async () => {
    useInvoiceTripCatchConflictsMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });

    renderTable();

    expect(await screen.findByText("Pomfret")).toBeInTheDocument();
    expect(screen.getByText("Pomfret - Grade A")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("shows the other-invoice usage once the summary resolves", async () => {
    useInvoiceTripCatchConflictsMock.mockReturnValue({
      data: [
        {
          tripCatchId: "catch-1",
          otherInvoiceCount: 2,
          otherDraftQuantity: "20.000",
          otherConsumedQuantity: "0.000",
        },
      ],
      isLoading: false,
      isError: false,
    });

    renderTable();

    expect(await screen.findByText("2 other invoices")).toBeInTheDocument();
  });

  it("shows an empty state when there are no items", async () => {
    listInvoiceItemsMock.mockResolvedValue([]);
    renderTable();

    expect(await screen.findByText("No items yet")).toBeInTheDocument();
  });

  it("hides Add Item when the invoice is not a draft", async () => {
    renderTable({ invoiceStatus: "issued" });

    await screen.findByText("Pomfret");
    expect(screen.queryByRole("button", { name: "Add Item" })).not.toBeInTheDocument();
  });
});
