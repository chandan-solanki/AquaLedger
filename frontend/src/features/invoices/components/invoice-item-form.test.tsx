import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InvoiceItemForm } from "@/features/invoices/components/invoice-item-form";

const {
  listTripCatchesMock,
  getTripCatchMock,
  getTripMock,
  useFishOptionsMock,
  getTripCatchDraftDemandMock,
  getTripCatchConflictsMock,
} = vi.hoisted(() => ({
  listTripCatchesMock: vi.fn(),
  getTripCatchMock: vi.fn(),
  getTripMock: vi.fn(),
  useFishOptionsMock: vi.fn(),
  getTripCatchDraftDemandMock: vi.fn(),
  getTripCatchConflictsMock: vi.fn(),
}));

vi.mock("@/features/fish", () => ({
  FISH_UNIT_LABELS: { kg: "Kg", box: "Box", piece: "Piece", ton: "Ton" },
}));

vi.mock("@/features/trips", () => ({
  CATCH_GRADE_LABELS: { A: "Grade A", B: "Grade B", C: "Grade C" },
  tripCatchService: { listTripCatches: listTripCatchesMock, getTripCatch: getTripCatchMock },
  tripKeys: { detail: (id: string) => ["trips", "detail", id] },
  tripService: { getTrip: getTripMock },
  useFishOptions: useFishOptionsMock,
}));

vi.mock("@/features/invoices/services/invoice-service", () => ({
  invoiceService: {
    getTripCatchDraftDemand: getTripCatchDraftDemandMock,
    getTripCatchConflicts: getTripCatchConflictsMock,
  },
}));

const FISH = { id: "fish-1", name: "Pomfret", unit: "kg" as const };

const CATCH_TRIP_A = {
  id: "catch-a",
  tripId: "trip-a",
  fishId: "fish-1",
  grade: "A" as const,
  availableQuantity: "20.000",
};
const CATCH_TRIP_B = {
  id: "catch-b",
  tripId: "trip-b",
  fishId: "fish-1",
  grade: "B" as const,
  availableQuantity: "50.000",
};
const CATCH_OUT_OF_STOCK = {
  id: "catch-c",
  tripId: "trip-c",
  fishId: "fish-1",
  grade: "A" as const,
  availableQuantity: "0.000",
};

const TRIPS: Record<string, string> = {
  "trip-a": "TRIP-A",
  "trip-b": "TRIP-B",
  "trip-c": "TRIP-C",
};

function renderForm(props: Partial<React.ComponentProps<typeof InvoiceItemForm>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onSubmit = vi.fn().mockResolvedValue(undefined);
  const onCancel = vi.fn();
  render(
    <QueryClientProvider client={queryClient}>
      <InvoiceItemForm
        invoiceId="invoice-1"
        onSubmit={onSubmit}
        onCancel={onCancel}
        submitLabel="Add Item"
        {...props}
      />
    </QueryClientProvider>
  );
  return { onSubmit, onCancel };
}

async function openTripCatchSelector() {
  const user = userEvent.setup();
  await user.click(screen.getByRole("combobox", { name: "Trip Catch" }));
  return user;
}

beforeEach(() => {
  vi.clearAllMocks();
  useFishOptionsMock.mockReturnValue({
    options: [{ value: FISH.id, label: FISH.name }],
    fishById: new Map([[FISH.id, FISH]]),
    isLoading: false,
  });
  listTripCatchesMock.mockResolvedValue({
    data: [CATCH_TRIP_A, CATCH_TRIP_B, CATCH_OUT_OF_STOCK],
    meta: { total_records: 3 },
  });
  getTripCatchMock.mockImplementation((id: string) =>
    Promise.resolve([CATCH_TRIP_A, CATCH_TRIP_B, CATCH_OUT_OF_STOCK].find((tc) => tc.id === id))
  );
  getTripMock.mockImplementation((id: string) => Promise.resolve({ id, tripNumber: TRIPS[id] }));
  getTripCatchDraftDemandMock.mockImplementation((tripCatchId: string) =>
    Promise.resolve({ tripCatchId, otherDraftQuantity: "0" })
  );
  getTripCatchConflictsMock.mockImplementation((tripCatchId: string) =>
    Promise.resolve({
      tripCatchId,
      requiredQuantity: null,
      availableQuantity: "20.000",
      shortfallQuantity: null,
      conflictingInvoices: [],
    })
  );
});

describe("InvoiceItemForm stock-aware selection", () => {
  it("shows each catch's available quantity and unit in the Trip Catch selector", async () => {
    renderForm();
    await openTripCatchSelector();

    await waitFor(() => expect(listTripCatchesMock).toHaveBeenCalled());
    expect(await screen.findByText("Grade A · Available: 20.000 Kg")).toBeInTheDocument();
    expect(await screen.findByText("Grade B · Available: 50.000 Kg")).toBeInTheDocument();
  });

  it("shows an 'Out of stock' catch as disabled rather than a selectable positive quantity", async () => {
    renderForm();
    await openTripCatchSelector();

    const outOfStockText = await screen.findByText("Grade A · Out of stock");
    expect(outOfStockText).toBeInTheDocument();
    const item = outOfStockText.closest('[cmdk-item]');
    expect(item).toHaveAttribute("aria-disabled", "true");
  });

  it("keeps two catches of the same fish from different trips fully separate", async () => {
    renderForm();
    await openTripCatchSelector();

    expect(await screen.findByText("TRIP-A — Pomfret")).toBeInTheDocument();
    expect(await screen.findByText("TRIP-B — Pomfret")).toBeInTheDocument();
    expect(screen.getByText("Grade A · Available: 20.000 Kg")).toBeInTheDocument();
    expect(screen.getByText("Grade B · Available: 50.000 Kg")).toBeInTheDocument();
  });

  it("shows Available Stock and a live Remaining figure once a catch is selected, and accepts a quantity within the limit", async () => {
    const { onSubmit } = renderForm();
    const user = await openTripCatchSelector();

    const option = await screen.findByText("TRIP-A — Pomfret");
    await user.click(option);

    expect(await screen.findByText("Available Stock")).toBeInTheDocument();
    // Before any quantity is entered, both "Available Stock" and "Remaining" show the same figure.
    expect(screen.getAllByText("20.000 Kg")).toHaveLength(2);

    await user.type(screen.getByLabelText(/Quantity/), "15");
    expect(await screen.findByText("5.000 Kg")).toBeInTheDocument();

    await user.type(screen.getByLabelText(/Rate/), "10");
    await user.click(screen.getByRole("button", { name: "Add Item" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      trip_catch_id: "catch-a",
      fish_id: "fish-1",
      quantity: "15",
    });
  });

  it("blocks submission and shows a clear message when quantity exceeds what is available", async () => {
    const { onSubmit } = renderForm();
    const user = await openTripCatchSelector();

    const option = await screen.findByText("TRIP-A — Pomfret");
    await user.click(option);

    await user.type(screen.getByLabelText(/Quantity/), "25");
    await user.type(screen.getByLabelText(/Rate/), "10");
    await user.click(screen.getByRole("button", { name: "Add Item" }));

    expect(await screen.findByText("Only 20.000 Kg is currently available.")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

describe("InvoiceItemForm draft demand (Sprint 15 Session 5)", () => {
  async function selectCatchA() {
    const user = await openTripCatchSelector();
    const option = await screen.findByText("TRIP-A — Pomfret");
    await user.click(option);
    return user;
  }

  it("stays exactly as before Session 5 when there is no other draft demand", async () => {
    getTripCatchDraftDemandMock.mockResolvedValue({ tripCatchId: "catch-a", otherDraftQuantity: "0" });
    renderForm();
    await selectCatchA();

    await waitFor(() => expect(getTripCatchDraftDemandMock).toHaveBeenCalled());
    expect(screen.queryByText("Other Draft Invoices")).not.toBeInTheDocument();
    expect(screen.queryByText("Potentially Available")).not.toBeInTheDocument();
    expect(screen.queryByText(/Other draft invoices are using this catch/)).not.toBeInTheDocument();
  });

  it("shows other draft demand and the potentially-available figure once other drafts exist", async () => {
    getTripCatchDraftDemandMock.mockResolvedValue({ tripCatchId: "catch-a", otherDraftQuantity: "6.000" });
    renderForm();
    await selectCatchA();

    expect(await screen.findByText("Other Draft Invoices")).toBeInTheDocument();
    expect(screen.getByText("6.000 Kg")).toBeInTheDocument();
    expect(screen.getByText("Potentially Available")).toBeInTheDocument();
    // Available 20 - other drafts 6 = 14.
    expect(screen.getByText("14.000 Kg")).toBeInTheDocument();
    expect(
      screen.getByText(/Other draft invoices are using this catch\. Stock is not reserved/)
    ).toBeInTheDocument();
  });

  it("excludes the current invoice's own demand by passing invoiceId as excludeInvoiceId", async () => {
    renderForm({ invoiceId: "invoice-42" });
    await selectCatchA();

    await waitFor(() =>
      expect(getTripCatchDraftDemandMock).toHaveBeenCalledWith("catch-a", {
        excludeInvoiceId: "invoice-42",
      })
    );
  });

  it("warns, without blocking, when quantity exceeds potentially-available but not actual available", async () => {
    getTripCatchDraftDemandMock.mockResolvedValue({ tripCatchId: "catch-a", otherDraftQuantity: "6.000" });
    const { onSubmit } = renderForm();
    const user = await selectCatchA();
    await screen.findByText("Potentially Available");

    // Available 20, potentially available 14 (20 - 6) - 18 exceeds potentially-available but not available.
    await user.type(screen.getByLabelText(/Quantity/), "18");

    expect(
      await screen.findByText(/20\.000 Kg is currently available, but 6\.000 Kg is already requested/)
    ).toBeInTheDocument();

    await user.type(screen.getByLabelText(/Rate/), "10");
    await user.click(screen.getByRole("button", { name: "Add Item" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
  });

  it("shows no over-potentially-available warning when quantity stays within it", async () => {
    getTripCatchDraftDemandMock.mockResolvedValue({ tripCatchId: "catch-a", otherDraftQuantity: "6.000" });
    renderForm();
    const user = await selectCatchA();
    await screen.findByText("Potentially Available");

    await user.type(screen.getByLabelText(/Quantity/), "10");

    expect(screen.queryByText(/is already requested by other draft invoices/)).not.toBeInTheDocument();
  });

  it("does not fetch or show draft demand for an out-of-stock catch", async () => {
    // Edit mode, pre-populated with the zero-availability catch - Session 4 keeps this
    // selectable in Edit mode (a historical selection is never hidden), so this is the one way
    // a zero-stock catch can be the current selection.
    renderForm({
      defaultValues: {
        trip_catch_id: "catch-c",
        fish_id: "fish-1",
        description: "",
        quantity: "",
        unit: "kg",
        rate: "",
        discount_percent: "",
        tax_rate: "",
      },
    });

    await waitFor(() => expect(getTripCatchMock).toHaveBeenCalledWith("catch-c"));
    expect(await screen.findByText("Available Stock")).toBeInTheDocument();
    expect(getTripCatchDraftDemandMock).not.toHaveBeenCalled();
    expect(screen.queryByText("Other Draft Invoices")).not.toBeInTheDocument();
  });
});

describe("InvoiceItemForm other-invoice usage (Sprint 15 Session 9)", () => {
  async function selectCatchA() {
    const user = await openTripCatchSelector();
    const option = await screen.findByText("TRIP-A — Pomfret");
    await user.click(option);
    return user;
  }

  it("fetches nothing before a catch is selected", async () => {
    renderForm();

    await screen.findByRole("combobox", { name: "Trip Catch" });
    expect(getTripCatchConflictsMock).not.toHaveBeenCalled();
  });

  it("shows no warning when the selected catch has no other invoice usage", async () => {
    getTripCatchConflictsMock.mockResolvedValue({
      tripCatchId: "catch-a",
      requiredQuantity: null,
      availableQuantity: "20.000",
      shortfallQuantity: null,
      conflictingInvoices: [],
    });
    renderForm();
    await selectCatchA();

    await waitFor(() => expect(getTripCatchConflictsMock).toHaveBeenCalled());
    expect(screen.queryByText(/Referenced by/)).not.toBeInTheDocument();
  });

  it("shows a loading state while the lookup is in flight", async () => {
    let resolveConflicts!: (value: unknown) => void;
    getTripCatchConflictsMock.mockReturnValue(new Promise((resolve) => (resolveConflicts = resolve)));
    renderForm();
    await selectCatchA();

    expect(await screen.findByText("Checking other invoices…")).toBeInTheDocument();

    resolveConflicts({
      tripCatchId: "catch-a",
      requiredQuantity: null,
      availableQuantity: "20.000",
      shortfallQuantity: null,
      conflictingInvoices: [],
    });
    await waitFor(() => expect(screen.queryByText("Checking other invoices…")).not.toBeInTheDocument());
  });

  it("shows draft-only usage", async () => {
    getTripCatchConflictsMock.mockResolvedValue({
      tripCatchId: "catch-a",
      requiredQuantity: null,
      availableQuantity: "20.000",
      shortfallQuantity: null,
      conflictingInvoices: [
        {
          invoiceId: "other-1",
          invoiceNumber: null,
          status: "draft",
          invoiceDate: "2026-08-01",
          companyName: "ABC Traders",
          quantity: "20.000",
        },
      ],
    });
    renderForm();
    await selectCatchA();

    expect(await screen.findByText("Referenced by 1 other invoice")).toBeInTheDocument();
    expect(screen.getByText("20.000 Kg in draft invoices")).toBeInTheDocument();
  });

  it("shows consumed-only usage", async () => {
    getTripCatchConflictsMock.mockResolvedValue({
      tripCatchId: "catch-a",
      requiredQuantity: null,
      availableQuantity: "20.000",
      shortfallQuantity: null,
      conflictingInvoices: [
        {
          invoiceId: "other-1",
          invoiceNumber: "INV/2026-27/00030",
          status: "issued",
          invoiceDate: "2026-08-01",
          companyName: "ABC Traders",
          quantity: "30.000",
        },
      ],
    });
    renderForm();
    await selectCatchA();

    expect(await screen.findByText("Referenced by 1 other invoice")).toBeInTheDocument();
    expect(screen.getByText("30.000 Kg already consumed")).toBeInTheDocument();
  });

  it("shows mixed draft and consumed usage", async () => {
    getTripCatchConflictsMock.mockResolvedValue({
      tripCatchId: "catch-a",
      requiredQuantity: null,
      availableQuantity: "20.000",
      shortfallQuantity: null,
      conflictingInvoices: [
        {
          invoiceId: "other-draft",
          invoiceNumber: null,
          status: "draft",
          invoiceDate: "2026-08-01",
          companyName: "ABC Traders",
          quantity: "20.000",
        },
        {
          invoiceId: "other-issued",
          invoiceNumber: "INV/2026-27/00031",
          status: "issued",
          invoiceDate: "2026-08-01",
          companyName: "XYZ Seafood",
          quantity: "30.000",
        },
      ],
    });
    renderForm();
    await selectCatchA();

    expect(await screen.findByText("Referenced by 2 other invoices")).toBeInTheDocument();
    expect(screen.getByText("20.000 Kg draft · 30.000 Kg consumed")).toBeInTheDocument();
  });

  it("never labels usage as Reserved, Committed Stock, or Locked Stock", async () => {
    getTripCatchConflictsMock.mockResolvedValue({
      tripCatchId: "catch-a",
      requiredQuantity: null,
      availableQuantity: "20.000",
      shortfallQuantity: null,
      conflictingInvoices: [
        {
          invoiceId: "other-1",
          invoiceNumber: null,
          status: "draft",
          invoiceDate: "2026-08-01",
          companyName: "ABC Traders",
          quantity: "20.000",
        },
      ],
    });
    renderForm();
    await selectCatchA();

    await screen.findByText("Referenced by 1 other invoice");
    expect(screen.queryByText(/reserved/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/committed/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/locked/i)).not.toBeInTheDocument();
  });

  it("excludes the current invoice by passing invoiceId as excludeInvoiceId", async () => {
    renderForm({ invoiceId: "invoice-42" });
    await selectCatchA();

    await waitFor(() =>
      expect(getTripCatchConflictsMock).toHaveBeenCalledWith("catch-a", {
        excludeInvoiceId: "invoice-42",
        requiredQuantity: undefined,
      })
    );
  });

  it("shows the exact Session 9 §5 scenario: 2 other invoices / 20 Kg draft / 40 Kg consumed, never 3 / 90", async () => {
    getTripCatchConflictsMock.mockResolvedValue({
      tripCatchId: "catch-a",
      requiredQuantity: null,
      availableQuantity: "20.000",
      shortfallQuantity: null,
      conflictingInvoices: [
        {
          invoiceId: "other-b",
          invoiceNumber: null,
          status: "draft",
          invoiceDate: "2026-08-01",
          companyName: "B Traders",
          quantity: "20.000",
        },
        {
          invoiceId: "other-c",
          invoiceNumber: "INV/2026-27/00032",
          status: "issued",
          invoiceDate: "2026-08-01",
          companyName: "C Traders",
          quantity: "40.000",
        },
      ],
    });
    renderForm({ invoiceId: "invoice-a" });
    await selectCatchA();

    expect(await screen.findByText("Referenced by 2 other invoices")).toBeInTheDocument();
    expect(screen.getByText("20.000 Kg draft · 40.000 Kg consumed")).toBeInTheDocument();
    expect(screen.queryByText("Referenced by 3 other invoices")).not.toBeInTheDocument();
    expect(screen.queryByText(/90\.000/)).not.toBeInTheDocument();
  });

  it("does not block saving when the usage lookup fails", async () => {
    getTripCatchConflictsMock.mockRejectedValue(new Error("network error"));
    const { onSubmit } = renderForm();
    const user = await selectCatchA();

    await waitFor(() => expect(getTripCatchConflictsMock).toHaveBeenCalled());
    expect(screen.queryByText(/Referenced by/)).not.toBeInTheDocument();

    await user.type(screen.getByLabelText(/Quantity/), "10");
    await user.type(screen.getByLabelText(/Rate/), "10");
    await user.click(screen.getByRole("button", { name: "Add Item" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
  });

  it("resets the usage display when the selection changes to a catch with different usage", async () => {
    getTripCatchConflictsMock.mockImplementation((tripCatchId: string) => {
      if (tripCatchId === "catch-a") {
        return Promise.resolve({
          tripCatchId,
          requiredQuantity: null,
          availableQuantity: "20.000",
          shortfallQuantity: null,
          conflictingInvoices: [
            {
              invoiceId: "other-1",
              invoiceNumber: null,
              status: "draft",
              invoiceDate: "2026-08-01",
              companyName: "ABC Traders",
              quantity: "20.000",
            },
          ],
        });
      }
      return Promise.resolve({
        tripCatchId,
        requiredQuantity: null,
        availableQuantity: "50.000",
        shortfallQuantity: null,
        conflictingInvoices: [],
      });
    });
    const user = await (async () => {
      renderForm();
      return openTripCatchSelector();
    })();

    await user.click(await screen.findByText("TRIP-A — Pomfret"));
    expect(await screen.findByText("Referenced by 1 other invoice")).toBeInTheDocument();

    await user.click(screen.getByRole("combobox", { name: "Trip Catch" }));
    await user.click(await screen.findByText("TRIP-B — Pomfret"));

    await waitFor(() => expect(screen.queryByText(/Referenced by/)).not.toBeInTheDocument());
  });
});
