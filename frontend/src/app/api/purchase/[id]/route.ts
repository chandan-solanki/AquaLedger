import { NextResponse } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/**
 * Proxy to the backend's `GET/PUT /purchase/{id}` - backs the Purchase
 * Bills feature's own Detail/Edit pages
 * (`purchaseBillService.getPurchaseBill`/`updatePurchaseBill`) and the
 * Supplier Payment Allocation table/form's per-bill resolution
 * (`supplier-payment-allocation-table.tsx`'s `useAllocationPurchaseBills`,
 * `supplier-payment-allocation-form.tsx`'s `PurchaseBillSelectorField`, GET
 * only), the same role `invoiceService.getInvoice` plays for
 * `PaymentAllocationTable`. No DELETE/`.../post` here - out of this pass's
 * scope.
 */
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const data = await authenticatedBackendRequest(`/purchase/${id}`);
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}

export async function PUT(request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const body = await request.json();
    const data = await authenticatedBackendRequest(`/purchase/${id}`, { method: "PUT", body });
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}
