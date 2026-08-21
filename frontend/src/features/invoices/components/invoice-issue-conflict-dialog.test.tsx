import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InvoiceIssueConflictDialog } from "@/features/invoices/components/invoice-issue-conflict-dialog";

const { hasPermissionMock, getTripCatchMock, useFishOptionsMock, getTripCatchConflictsMock } = vi.hoisted(() => ({
  hasPermissionMock: vi.fn(() => true),
  getTripCatchMock: vi.fn(),
  useFishOptionsMock: vi.fn(),
  getTripCatchConflictsMock: vi.fn(),
}));

vi.mock("@/features/auth/hooks/use-permissions", () => ({
  usePermissions: () => ({ hasPermission: hasPermissionMock }),
}));

vi.mock("@/features/fish", () => ({
  FISH_UNIT_LABELS: { kg: "Kg", box: "Box", piece: "Piece", ton: "Ton" },
}));

vi.mock("@/features/trips", () => ({
  CATCH_GRADE_LABELS: { A: "Grade A", B: "Grade B", C: "Grade C" },
  tripCatchService: { getTripCatch: getTripCatchMock },
  useFishOptions: useFishOptionsMock,
}));

vi.mock("@/features/invoices/services/invoice-service", () => ({
  invoiceService: { getTripCatchConflicts: getTripCatchConflictsMock },
}));

const FISH = { id: "fish-1", name: "Pomfret", unit: "kg" as const };
const TRIP_CATCH = { id: "catch-1", fishId: "fish-1", grade: "A" as const, availableQuantity: "40.000" };

function renderDialog(props: Partial<React.ComponentProps<typeof InvoiceIssueConflictDialog>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onOpenChange = vi.fn();
  render(
    <QueryClientProvider client={queryClient}>
      <InvoiceIssueConflictDialog
        open
        onOpenChange={onOpenChange}
        currentInvoiceId="invoice-current"
        tripCatchId="catch-1"
        requiredQuantity="50.000"
        {...props}
      />
    </QueryClientProvider>
  );
  return { onOpenChange };
}

beforeEach(() => {
  vi.clearAllMocks();
  hasPermissionMock.mockReturnValue(true);
  useFishOptionsMock.mockReturnValue({
    options: [{ value: FISH.id, label: FISH.name }],
    fishById: new Map([[FISH.id, FISH]]),
    isLoading: false,
  });
  getTripCatchMock.mockResolvedValue(TRIP_CATCH);
  getTripCatchConflictsMock.mockResolvedValue({
    tripCatchId: "catch-1",
    requiredQuantity: "50.000",
    availableQuantity: "40.000",
    shortfallQuantity: "10.000",
    conflictingInvoices: [],
  });
});

describe("InvoiceIssueConflictDialog", () => {
  it("shows required, available, and shortfall quantities", async () => {
    renderDialog();

    expect(await screen.findByText("Pomfret — Grade A")).toBeInTheDocument();
    expect(screen.getByText("Required")).toBeInTheDocument();
    expect(screen.getByText("50.000 Kg")).toBeInTheDocument();
    expect(screen.getByText("Available")).toBeInTheDocument();
    expect(screen.getByText("40.000 Kg")).toBeInTheDocument();
    expect(screen.getByText("Shortfall")).toBeInTheDocument();
    expect(screen.getByText("10.000 Kg")).toBeInTheDocument();
  });

  it("renders the fallback message when no conflict could be identified", async () => {
    getTripCatchConflictsMock.mockResolvedValue({
      tripCatchId: "catch-1",
      requiredQuantity: "50.000",
      availableQuantity: "40.000",
      shortfallQuantity: "10.000",
      conflictingInvoices: [],
    });
    renderDialog();

    expect(
      await screen.findByText(/No other invoice could be identified as the cause/)
    ).toBeInTheDocument();
  });

  it("displays a conflicting draft invoice", async () => {
    getTripCatchConflictsMock.mockResolvedValue({
      tripCatchId: "catch-1",
      requiredQuantity: "50.000",
      availableQuantity: "40.000",
      shortfallQuantity: "10.000",
      conflictingInvoices: [
        {
          invoiceId: "other-invoice-1",
          invoiceNumber: null,
          status: "draft",
          invoiceDate: "2026-08-01",
          companyName: "ABC Traders",
          quantity: "30.000",
        },
      ],
    });
    renderDialog();

    expect(await screen.findByText("Draft Invoice")).toBeInTheDocument();
    expect(screen.getByText(/ABC Traders/)).toBeInTheDocument();
    expect(screen.getByText(/30\.000 Kg/)).toBeInTheDocument();
    expect(screen.getByText("Other draft invoices referencing this catch")).toBeInTheDocument();
  });

  it("labels the section generically when an issued invoice already consumed the stock", async () => {
    getTripCatchConflictsMock.mockResolvedValue({
      tripCatchId: "catch-1",
      requiredQuantity: "50.000",
      availableQuantity: "40.000",
      shortfallQuantity: "10.000",
      conflictingInvoices: [
        {
          invoiceId: "other-invoice-1",
          invoiceNumber: "INV/2026-27/00025",
          status: "issued",
          invoiceDate: "2026-08-01",
          companyName: "ABC Traders",
          quantity: "60.000",
        },
      ],
    });
    renderDialog();

    expect(await screen.findByText("INV/2026-27/00025")).toBeInTheDocument();
    expect(screen.getByText("Other invoices referencing this catch")).toBeInTheDocument();
  });

  it("shows multiple conflicts, most beyond three collapsed behind a toggle", async () => {
    const conflicts = Array.from({ length: 5 }, (_, i) => ({
      invoiceId: `other-invoice-${i}`,
      invoiceNumber: null,
      status: "draft" as const,
      invoiceDate: "2026-08-01",
      companyName: `Company ${i}`,
      quantity: "5.000",
    }));
    getTripCatchConflictsMock.mockResolvedValue({
      tripCatchId: "catch-1",
      requiredQuantity: "50.000",
      availableQuantity: "40.000",
      shortfallQuantity: "10.000",
      conflictingInvoices: conflicts,
    });
    const user = userEvent.setup();
    renderDialog();

    await screen.findByText(/Company 0/);
    expect(screen.queryByText(/Company 4/)).not.toBeInTheDocument();
    expect(screen.getByText("Show 2 more")).toBeInTheDocument();

    await user.click(screen.getByText("Show 2 more"));
    expect(screen.getByText(/Company 4/)).toBeInTheDocument();
  });

  it("never lists the current invoice as its own conflict", async () => {
    renderDialog({ currentInvoiceId: "invoice-current" });

    await waitFor(() =>
      expect(getTripCatchConflictsMock).toHaveBeenCalledWith("catch-1", {
        excludeInvoiceId: "invoice-current",
        requiredQuantity: "50.000",
      })
    );
  });

  it("shows a View link to a conflicting invoice when the user can view invoices", async () => {
    getTripCatchConflictsMock.mockResolvedValue({
      tripCatchId: "catch-1",
      requiredQuantity: "50.000",
      availableQuantity: "40.000",
      shortfallQuantity: "10.000",
      conflictingInvoices: [
        {
          invoiceId: "other-invoice-1",
          invoiceNumber: "INV/2026-27/00025",
          status: "issued",
          invoiceDate: "2026-08-01",
          companyName: "ABC Traders",
          quantity: "60.000",
        },
      ],
    });
    renderDialog();

    const link = await screen.findByRole("link", { name: "View" });
    expect(link).toHaveAttribute("href", "/invoices/other-invoice-1");
  });

  it("shows plain text instead of a link when the user lacks invoice:view", async () => {
    hasPermissionMock.mockReturnValue(false);
    getTripCatchConflictsMock.mockResolvedValue({
      tripCatchId: "catch-1",
      requiredQuantity: "50.000",
      availableQuantity: "40.000",
      shortfallQuantity: "10.000",
      conflictingInvoices: [
        {
          invoiceId: "other-invoice-1",
          invoiceNumber: "INV/2026-27/00025",
          status: "issued",
          invoiceDate: "2026-08-01",
          companyName: "ABC Traders",
          quantity: "60.000",
        },
      ],
    });
    renderDialog();

    await screen.findByText("INV/2026-27/00025");
    expect(screen.queryByRole("link", { name: "View" })).not.toBeInTheDocument();
  });

  it("closes when Close is clicked", async () => {
    const user = userEvent.setup();
    const { onOpenChange } = renderDialog();

    await screen.findByText("Pomfret — Grade A");
    // Radix's Dialog renders its own icon-only "Close" (X) button with the same accessible
    // name as the footer's literal Close button - the footer one is the first in DOM order.
    await user.click(screen.getAllByRole("button", { name: "Close" })[0]);

    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
