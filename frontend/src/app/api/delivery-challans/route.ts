import { NextResponse, type NextRequest } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/**
 * Proxy to the backend's `GET/POST /delivery-challans`
 * (app/modules/delivery_challans/router.py) - mirrors
 * `app/api/purchase-orders/route.ts`. PUT/DELETE and the dispatch/deliver/
 * cancel transitions live on `[id]/route.ts` and its own sub-routes.
 */
export async function GET(request: NextRequest) {
  try {
    const data = await authenticatedBackendRequest(`/delivery-challans${request.nextUrl.search}`);
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const data = await authenticatedBackendRequest("/delivery-challans", { method: "POST", body });
    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    return authErrorResponse(error);
  }
}
