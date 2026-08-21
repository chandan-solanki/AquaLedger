import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InvoiceIssuePreflightDialog } from "@/features/invoices/components/invoice-issue-preflight-dialog";
import type { Fish } from "@/features/fish";
import type { InvoiceIssuePreflightConflict } from "@/features/invoices/types/invoice-issue-preflight";
import type { InvoiceItem } from "@/features/invoices/types/invoice-item";

const FISH_BY_ID = new Map<string, Fish>([
  ["fish-1", { id: "fish-1", name: "Pomfret", unit: "kg" } as Fish],
  ["fish-2", { id: "fish-2", name: "Tuna", unit: "kg" } as Fish],
]);

function makeItem(overrides: Partial<InvoiceItem> = {}): InvoiceItem {
  return {
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
    ...overrides,
  };
}

function makeConflict(overrides: Partial<InvoiceIssuePreflightConflict> = {}): InvoiceIssuePreflightConflict {
  return {
    tripCatchId: "catch-1",
    requestedQuantity: "30.000",
    availableQuantity: "20.000",
    isSufficient: false,
    shortfallQuantity: "10.000",
    otherDraftQuantity: "0.000",
    ...overrides,
  };
}

function renderDialog(props: Partial<React.ComponentProps<typeof InvoiceIssuePreflightDialog>> = {}) {
  const onOpenChange = vi.fn();
  const onContinueAnyway = vi.fn();
  render(
    <InvoiceIssuePreflightDialog
      open
      onOpenChange={onOpenChange}
      conflicts={[makeConflict()]}
      items={[makeItem()]}
      fishById={FISH_BY_ID}
      onContinueAnyway={onContinueAnyway}
      {...props}
    />
  );
  return { onOpenChange, onContinueAnyway };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("InvoiceIssuePreflightDialog", () => {
  it("shows the informational heading, never an alarming error tone", () => {
    renderDialog();

    expect(screen.getByText("Check stock before issuing")).toBeInTheDocument();
    expect(
      screen.getByText("Some invoice items may no longer have sufficient available stock.")
    ).toBeInTheDocument();
  });

  it("renders the fish name and requested/available/shortfall quantities for one conflict", () => {
    renderDialog();

    expect(screen.getByText("Pomfret")).toBeInTheDocument();
    expect(screen.getByText("30.000 kg")).toBeInTheDocument();
    expect(screen.getByText("20.000 kg")).toBeInTheDocument();
    expect(screen.getByText("10.000 kg")).toBeInTheDocument();
  });

  it("renders one row per conflict for multiple conflicts, each with its own fish", () => {
    renderDialog({
      conflicts: [
        makeConflict({ tripCatchId: "catch-1" }),
        makeConflict({ tripCatchId: "catch-2", requestedQuantity: "15.000", availableQuantity: "5.000", shortfallQuantity: "10.000" }),
      ],
      items: [makeItem({ tripCatchId: "catch-1" }), makeItem({ id: "item-2", tripCatchId: "catch-2", fishId: "fish-2" })],
    });

    expect(screen.getByText("Pomfret")).toBeInTheDocument();
    expect(screen.getByText("Tuna")).toBeInTheDocument();
    expect(screen.getAllByText(/10\.000 kg/).length).toBeGreaterThanOrEqual(1);
  });

  it("falls back to 'Unknown fish' when no matching item is found for a conflict", () => {
    renderDialog({ items: [] });

    expect(screen.getByText("Unknown fish")).toBeInTheDocument();
  });

  it("shows the other-draft-quantity note only when it is non-zero", () => {
    renderDialog({ conflicts: [makeConflict({ otherDraftQuantity: "5.000" })] });

    expect(screen.getByText(/Also referenced by other draft invoices: 5\.000 kg/)).toBeInTheDocument();
  });

  it("omits the other-draft-quantity note when it is zero", () => {
    renderDialog({ conflicts: [makeConflict({ otherDraftQuantity: "0.000" })] });

    expect(screen.queryByText(/Also referenced by other draft invoices/)).not.toBeInTheDocument();
  });

  it("never uses the terms Reserved, Committed Stock, or Locked Stock", () => {
    renderDialog({ conflicts: [makeConflict({ otherDraftQuantity: "5.000" })] });

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).queryByText(/reserved/i)).not.toBeInTheDocument();
    expect(within(dialog).queryByText(/committed stock/i)).not.toBeInTheDocument();
    expect(within(dialog).queryByText(/locked stock/i)).not.toBeInTheDocument();
  });

  it("Cancel calls onOpenChange(false) without calling onContinueAnyway", async () => {
    const user = userEvent.setup();
    const { onOpenChange, onContinueAnyway } = renderDialog();

    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(onContinueAnyway).not.toHaveBeenCalled();
  });

  it("Continue to Issue calls onContinueAnyway", async () => {
    const user = userEvent.setup();
    const { onContinueAnyway } = renderDialog();

    await user.click(screen.getByRole("button", { name: "Continue to Issue" }));

    expect(onContinueAnyway).toHaveBeenCalledTimes(1);
  });
});
