import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { FishStockContributingCatchesTable } from "@/features/fish-stock/components/fish-stock-contributing-catches-table";
import type { FishStockContributingCatch } from "@/features/fish-stock/types/fish-stock";
import type { TripCatchInvoiceUsage } from "@/features/invoices/types/trip-catch-invoice-usage";

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

const AVAILABLE_CATCH: FishStockContributingCatch = {
  tripCatchId: "catch-1",
  tripId: "trip-1",
  tripNumber: "TRIP-2026-0042",
  landingDate: "2026-07-22",
  quantityCaught: "180.000",
  soldQuantity: "60.000",
  availableQuantity: "120.000",
  wasteQuantity: "0.000",
};

const DEPLETED_CATCH: FishStockContributingCatch = {
  ...AVAILABLE_CATCH,
  tripCatchId: "catch-2",
  tripNumber: "TRIP-2026-0043",
  availableQuantity: "0.000",
  soldQuantity: "180.000",
};

function renderTable(props: Partial<React.ComponentProps<typeof FishStockContributingCatchesTable>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <FishStockContributingCatchesTable
        catches={[AVAILABLE_CATCH]}
        isLoading={false}
        unitLabel="Kg"
        {...props}
      />
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  hasPermissionMock.mockReturnValue(true);
  getTripCatchConflictsMock.mockResolvedValue({
    tripCatchId: "catch-1",
    requiredQuantity: null,
    availableQuantity: "120.000",
    shortfallQuantity: null,
    conflictingInvoices: [],
  });
});

describe("FishStockContributingCatchesTable", () => {
  it("links a catch with available stock to a pre-filled invoice draft", () => {
    renderTable();

    const link = screen.getByRole("link", { name: "Create Invoice" });
    expect(link).toHaveAttribute("href", "/invoices/new?tripCatchId=catch-1");
  });

  it("shows no Create Invoice action for a catch with zero available stock", () => {
    renderTable({ catches: [DEPLETED_CATCH] });

    expect(screen.queryByRole("link", { name: "Create Invoice" })).not.toBeInTheDocument();
  });

  it("gives each catch its own independent action, never a shared or mixed-up one", () => {
    renderTable({ catches: [AVAILABLE_CATCH, DEPLETED_CATCH] });

    const links = screen.getAllByRole("link", { name: "Create Invoice" });
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveAttribute("href", "/invoices/new?tripCatchId=catch-1");
  });

  it("hides the Create Invoice action entirely without invoice:create permission", () => {
    hasPermissionMock.mockReturnValue(false);
    renderTable();

    expect(screen.queryByRole("link", { name: "Create Invoice" })).not.toBeInTheDocument();
  });

  it("shows an empty state with no rows when there are no contributing catches", () => {
    renderTable({ catches: [] });

    expect(screen.getByText("No contributing catches")).toBeInTheDocument();
  });
});

describe("FishStockContributingCatchesTable Invoice Usage indicator (Sprint 15 Session 7)", () => {
  it("shows a dash when a catch has no usage entry", () => {
    renderTable({ usageByTripCatchId: new Map() });

    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("shows a dash when the usage summary is unavailable (e.g. the fetch failed)", () => {
    renderTable({ usageByTripCatchId: undefined, isUsageLoading: false });

    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("shows a loading placeholder while usage is being fetched", () => {
    renderTable({ usageByTripCatchId: undefined, isUsageLoading: true });

    expect(screen.getByText("…")).toBeInTheDocument();
    expect(screen.queryByText("—")).not.toBeInTheDocument();
  });

  it("shows the invoice count for a catch with usage", () => {
    const usage = new Map<string, TripCatchInvoiceUsage>([
      ["catch-1", { tripCatchId: "catch-1", invoiceCount: 2, draftQuantity: "0", consumedQuantity: "0" }],
    ]);
    renderTable({ usageByTripCatchId: usage });

    expect(screen.getByText("2 invoices")).toBeInTheDocument();
  });

  it("uses singular phrasing for exactly one invoice", () => {
    const usage = new Map<string, TripCatchInvoiceUsage>([
      ["catch-1", { tripCatchId: "catch-1", invoiceCount: 1, draftQuantity: "0", consumedQuantity: "0" }],
    ]);
    renderTable({ usageByTripCatchId: usage });

    expect(screen.getByText("1 invoice")).toBeInTheDocument();
  });

  it("shows draft and consumed quantities when both are non-zero", () => {
    const usage = new Map<string, TripCatchInvoiceUsage>([
      [
        "catch-1",
        { tripCatchId: "catch-1", invoiceCount: 2, draftQuantity: "30.000", consumedQuantity: "60.000" },
      ],
    ]);
    renderTable({ usageByTripCatchId: usage });

    expect(screen.getByText("30.000 Kg draft · 60.000 Kg consumed")).toBeInTheDocument();
  });

  it("omits the detail line entirely when both quantities are zero", () => {
    const usage = new Map<string, TripCatchInvoiceUsage>([
      ["catch-1", { tripCatchId: "catch-1", invoiceCount: 0, draftQuantity: "0", consumedQuantity: "0" }],
    ]);
    renderTable({ usageByTripCatchId: usage });

    expect(screen.queryByText(/draft/)).not.toBeInTheDocument();
    expect(screen.queryByText(/consumed/)).not.toBeInTheDocument();
  });

  it("never labels usage as Reserved or Committed Stock", () => {
    const usage = new Map<string, TripCatchInvoiceUsage>([
      [
        "catch-1",
        { tripCatchId: "catch-1", invoiceCount: 1, draftQuantity: "30.000", consumedQuantity: "0" },
      ],
    ]);
    renderTable({ usageByTripCatchId: usage });

    expect(screen.queryByText(/reserved/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/committed/i)).not.toBeInTheDocument();
  });

  it("associates each catch with its own usage entry independently", () => {
    const usage = new Map<string, TripCatchInvoiceUsage>([
      ["catch-1", { tripCatchId: "catch-1", invoiceCount: 2, draftQuantity: "0", consumedQuantity: "0" }],
      ["catch-2", { tripCatchId: "catch-2", invoiceCount: 0, draftQuantity: "0", consumedQuantity: "0" }],
    ]);
    renderTable({ catches: [AVAILABLE_CATCH, DEPLETED_CATCH], usageByTripCatchId: usage });

    expect(screen.getByText("2 invoices")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders the count as plain, non-interactive text without invoice:view", () => {
    hasPermissionMock.mockReturnValue(false);
    const usage = new Map<string, TripCatchInvoiceUsage>([
      ["catch-1", { tripCatchId: "catch-1", invoiceCount: 2, draftQuantity: "0", consumedQuantity: "0" }],
    ]);
    renderTable({ usageByTripCatchId: usage });

    expect(screen.getByText("2 invoices")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /View invoices/ })).not.toBeInTheDocument();
  });

  it("opens a dialog listing the referencing invoices when clicked with invoice:view", async () => {
    getTripCatchConflictsMock.mockResolvedValue({
      tripCatchId: "catch-1",
      requiredQuantity: null,
      availableQuantity: "120.000",
      shortfallQuantity: null,
      conflictingInvoices: [
        {
          invoiceId: "invoice-1",
          invoiceNumber: "INV/2026-27/00025",
          status: "issued",
          invoiceDate: "2026-07-22",
          companyName: "ABC Traders",
          quantity: "60.000",
        },
      ],
    });
    const usage = new Map<string, TripCatchInvoiceUsage>([
      ["catch-1", { tripCatchId: "catch-1", invoiceCount: 1, draftQuantity: "0", consumedQuantity: "60.000" }],
    ]);
    const user = userEvent.setup();
    renderTable({ usageByTripCatchId: usage });

    await user.click(screen.getByRole("button", { name: /View invoices/ }));

    expect(await screen.findByText("Invoices referencing this catch")).toBeInTheDocument();
    await waitFor(() => expect(getTripCatchConflictsMock).toHaveBeenCalledWith("catch-1", { excludeInvoiceId: undefined, requiredQuantity: undefined }));
    const link = await screen.findByRole("link", { name: "View" });
    expect(link).toHaveAttribute("href", "/invoices/invoice-1");
  });
});
