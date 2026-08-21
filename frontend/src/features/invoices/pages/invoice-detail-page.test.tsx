import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InvoiceDetailPage } from "@/features/invoices/pages/invoice-detail-page";

const {
  hasPermissionMock,
  useFishOptionsMock,
  useInvoiceMock,
  useCompanyOptionsMock,
  useInvoiceItemsMock,
  useInvoiceIssuePreflightMock,
  issuePreflightMutateMock,
  useIssueInvoiceMock,
  issueInvoiceMutateMock,
  useDeleteInvoiceMock,
} = vi.hoisted(() => ({
  hasPermissionMock: vi.fn(() => true),
  useFishOptionsMock: vi.fn(),
  useInvoiceMock: vi.fn(),
  useCompanyOptionsMock: vi.fn(),
  useInvoiceItemsMock: vi.fn(),
  useInvoiceIssuePreflightMock: vi.fn(),
  issuePreflightMutateMock: vi.fn(),
  useIssueInvoiceMock: vi.fn(),
  issueInvoiceMutateMock: vi.fn(),
  useDeleteInvoiceMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "invoice-1" }),
  usePathname: () => "/invoices/invoice-1",
}));

vi.mock("@/features/auth/hooks/use-permissions", () => ({
  usePermissions: () => ({ hasPermission: hasPermissionMock }),
}));

vi.mock("@/features/trips", () => ({
  useFishOptions: useFishOptionsMock,
}));

vi.mock("@/features/invoices/components/invoice-item-table", () => ({
  InvoiceItemTable: () => null,
}));

vi.mock("@/features/invoices/hooks/use-invoice", () => ({
  useInvoice: useInvoiceMock,
}));

vi.mock("@/features/invoices/hooks/use-company-options", () => ({
  useCompanyOptions: useCompanyOptionsMock,
}));

vi.mock("@/features/invoices/hooks/use-invoice-items", () => ({
  useInvoiceItems: useInvoiceItemsMock,
}));

vi.mock("@/features/invoices/hooks/use-invoice-issue-preflight", () => ({
  useInvoiceIssuePreflight: useInvoiceIssuePreflightMock,
}));

vi.mock("@/features/invoices/hooks/use-issue-invoice", () => ({
  useIssueInvoice: useIssueInvoiceMock,
}));

vi.mock("@/features/invoices/hooks/use-delete-invoice", () => ({
  useDeleteInvoice: useDeleteInvoiceMock,
}));

const FISH = { id: "fish-1", name: "Pomfret", unit: "kg" as const };

const DRAFT_INVOICE = {
  id: "invoice-1",
  tenantId: "tenant-1",
  companyId: "company-1",
  invoiceNumber: null,
  invoiceDate: "2026-08-21",
  dueDate: null,
  status: "draft" as const,
  subtotal: "1000.00",
  discountAmount: "0.00",
  taxableAmount: "1000.00",
  taxAmount: "0.00",
  transportCharge: "0.00",
  otherCharge: "0.00",
  roundOff: "0.00",
  totalAmount: "1000.00",
  paidAmount: "0.00",
  balanceAmount: "1000.00",
  remarks: null,
  issuedAt: null,
  createdAt: "2026-08-21T00:00:00Z",
  updatedAt: "2026-08-21T00:00:00Z",
};

const ITEM = {
  id: "item-1",
  tenantId: "tenant-1",
  invoiceId: "invoice-1",
  lineNumber: 1,
  fishId: "fish-1",
  tripCatchId: "catch-1",
  description: null,
  quantity: "30.000",
  unit: "kg",
  rate: "100.0000",
  discountPercent: "0.00",
  discountAmount: "0.00",
  taxableAmount: "3000.00",
  taxRate: "0.00",
  taxAmount: "0.00",
  lineTotal: "3000.00",
  createdAt: "2026-08-21T00:00:00Z",
  updatedAt: "2026-08-21T00:00:00Z",
};

function mockCleanPreflight() {
  issuePreflightMutateMock.mockImplementation(
    (_id: string, { onSuccess }: { onSuccess: (result: unknown) => void }) => {
      onSuccess({ invoiceId: "invoice-1", canIssueNow: true, conflicts: [] });
    }
  );
}

function mockConflictingPreflight() {
  issuePreflightMutateMock.mockImplementation(
    (_id: string, { onSuccess }: { onSuccess: (result: unknown) => void }) => {
      onSuccess({
        invoiceId: "invoice-1",
        canIssueNow: false,
        conflicts: [
          {
            tripCatchId: "catch-1",
            requestedQuantity: "30.000",
            availableQuantity: "20.000",
            isSufficient: false,
            shortfallQuantity: "10.000",
            otherDraftQuantity: "0.000",
          },
        ],
      });
    }
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
  useInvoiceMock.mockReturnValue({
    data: DRAFT_INVOICE,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  });
  useCompanyOptionsMock.mockReturnValue({
    options: [{ value: "company-1", label: "ABC Traders" }],
    nameById: new Map([["company-1", "ABC Traders"]]),
    isLoading: false,
  });
  useInvoiceItemsMock.mockReturnValue({ data: [ITEM], isLoading: false, isError: false });
  useInvoiceIssuePreflightMock.mockReturnValue({
    mutate: issuePreflightMutateMock,
    isPending: false,
  });
  useIssueInvoiceMock.mockReturnValue({ mutate: issueInvoiceMutateMock, isPending: false });
  useDeleteInvoiceMock.mockReturnValue({ mutate: vi.fn(), isPending: false });
});

describe("InvoiceDetailPage issue preflight (Sprint 15 Session 10)", () => {
  it("triggers exactly one preflight request when Issue Invoice is clicked", async () => {
    mockCleanPreflight();
    const user = userEvent.setup();
    render(<InvoiceDetailPage />);

    await user.click(screen.getByRole("button", { name: "Issue Invoice" }));

    expect(issuePreflightMutateMock).toHaveBeenCalledTimes(1);
    expect(issuePreflightMutateMock.mock.calls[0][0]).toBe("invoice-1");
  });

  it("proceeds straight to the existing confirmation dialog on a clean preflight", async () => {
    mockCleanPreflight();
    const user = userEvent.setup();
    render(<InvoiceDetailPage />);

    await user.click(screen.getByRole("button", { name: "Issue Invoice" }));

    expect(await screen.findByText("Issue this invoice?")).toBeInTheDocument();
    expect(screen.queryByText("Check stock before issuing")).not.toBeInTheDocument();
  });

  it("opens the preflight warning dialog when conflicts are found", async () => {
    mockConflictingPreflight();
    const user = userEvent.setup();
    render(<InvoiceDetailPage />);

    await user.click(screen.getByRole("button", { name: "Issue Invoice" }));

    expect(await screen.findByText("Check stock before issuing")).toBeInTheDocument();
    expect(screen.queryByText("Issue this invoice?")).not.toBeInTheDocument();
  });

  it("renders the affected item's fish name and quantities in the warning dialog", async () => {
    mockConflictingPreflight();
    const user = userEvent.setup();
    render(<InvoiceDetailPage />);

    await user.click(screen.getByRole("button", { name: "Issue Invoice" }));

    const dialog = await screen.findByRole("dialog", { name: "Check stock before issuing" });
    expect(within(dialog).getByText("Pomfret")).toBeInTheDocument();
    expect(within(dialog).getByText("30.000 kg")).toBeInTheDocument();
    expect(within(dialog).getByText("20.000 kg")).toBeInTheDocument();
    expect(within(dialog).getByText("10.000 kg")).toBeInTheDocument();
  });

  it("cancelling the warning dialog never opens the confirmation dialog or issues anything", async () => {
    mockConflictingPreflight();
    const user = userEvent.setup();
    render(<InvoiceDetailPage />);
    await user.click(screen.getByRole("button", { name: "Issue Invoice" }));
    const dialog = await screen.findByRole("dialog", { name: "Check stock before issuing" });

    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));

    expect(screen.queryByText("Check stock before issuing")).not.toBeInTheDocument();
    expect(screen.queryByText("Issue this invoice?")).not.toBeInTheDocument();
    expect(issueInvoiceMutateMock).not.toHaveBeenCalled();
  });

  it("Continue to Issue proceeds to the existing confirmation dialog", async () => {
    mockConflictingPreflight();
    const user = userEvent.setup();
    render(<InvoiceDetailPage />);
    await user.click(screen.getByRole("button", { name: "Issue Invoice" }));
    const dialog = await screen.findByRole("dialog", { name: "Check stock before issuing" });

    await user.click(within(dialog).getByRole("button", { name: "Continue to Issue" }));

    expect(await screen.findByText("Issue this invoice?")).toBeInTheDocument();
    expect(screen.queryByText("Check stock before issuing")).not.toBeInTheDocument();
  });

  it("re-runs the preflight on every Issue Invoice click", async () => {
    mockCleanPreflight();
    const user = userEvent.setup();
    render(<InvoiceDetailPage />);

    await user.click(screen.getByRole("button", { name: "Issue Invoice" }));
    await screen.findByText("Issue this invoice?");
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    await user.click(screen.getByRole("button", { name: "Issue Invoice" }));

    expect(issuePreflightMutateMock).toHaveBeenCalledTimes(2);
  });

  it("shows a loading state on the Issue Invoice button while the preflight is in flight", () => {
    useInvoiceIssuePreflightMock.mockReturnValue({
      mutate: issuePreflightMutateMock,
      isPending: true,
    });
    render(<InvoiceDetailPage />);

    expect(screen.getByRole("button", { name: "Issue Invoice" })).toBeDisabled();
  });

  it("falls back to the existing confirmation dialog when the preflight request itself fails", async () => {
    issuePreflightMutateMock.mockImplementation(
      (_id: string, { onError }: { onError: () => void }) => {
        onError();
      }
    );
    const user = userEvent.setup();
    render(<InvoiceDetailPage />);

    await user.click(screen.getByRole("button", { name: "Issue Invoice" }));

    expect(await screen.findByText("Issue this invoice?")).toBeInTheDocument();
  });

  it("does not crash the page when the invoice has no items yet", async () => {
    useInvoiceItemsMock.mockReturnValue({ data: [], isLoading: false, isError: false });
    mockConflictingPreflight();
    const user = userEvent.setup();
    render(<InvoiceDetailPage />);

    await user.click(screen.getByRole("button", { name: "Issue Invoice" }));

    expect(await screen.findByText("Check stock before issuing")).toBeInTheDocument();
    expect(screen.getByText("Unknown fish")).toBeInTheDocument();
  });

  it("still calls the real issue mutation once the user confirms after a clean preflight", async () => {
    mockCleanPreflight();
    const user = userEvent.setup();
    render(<InvoiceDetailPage />);
    await user.click(screen.getByRole("button", { name: "Issue Invoice" }));
    const confirmDialog = await screen.findByRole("alertdialog", { name: "Issue this invoice?" });

    await user.click(within(confirmDialog).getByRole("button", { name: "Issue Invoice" }));

    await waitFor(() => expect(issueInvoiceMutateMock).toHaveBeenCalled());
    expect(issueInvoiceMutateMock.mock.calls[0][0]).toBe("invoice-1");
  });
});
