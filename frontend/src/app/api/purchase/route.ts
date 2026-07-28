import { NextResponse, type NextRequest } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/**
 * Proxy to the backend's `GET/POST /purchase` (app/modules/purchase/
 * router.py) - mirrors `app/api/invoices/route.ts` exactly. Backs both the
 * Purchase Bills feature's own List/Create pages
 * (`@/features/purchase-bills`) and the Supplier Payment Allocation form's
 * Purchase Bill selector (`supplier-payment-allocation-form.tsx`, GET only).
 * PUT/DELETE/POST-.../post live on `[id]/route.ts` and its own sub-routes.
 */
export async function GET(request: NextRequest) {
  try {
    const data = await authenticatedBackendRequest(`/purchase${request.nextUrl.search}`);
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const data = await authenticatedBackendRequest("/purchase", { method: "POST", body });
    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    return authErrorResponse(error);
  }
}
