import { NextResponse, type NextRequest } from "next/server";

import {
  authenticatedBackendBinaryRequest,
  authenticatedBackendFormRequest,
  authenticatedBackendRequest,
} from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

/** Streams the logo bytes for inline display - the backend deliberately
 * omits Content-Disposition: attachment for this endpoint (unlike
 * /documents/{id}/download), so this proxy doesn't fabricate one either. */
export async function GET(_request: NextRequest) {
  try {
    const backendResponse = await authenticatedBackendBinaryRequest("/company-profile/logo");
    const body = await backendResponse.arrayBuffer();
    return new NextResponse(body, {
      status: backendResponse.status,
      headers: {
        "Content-Type": backendResponse.headers.get("content-type") ?? "application/octet-stream",
        // Set explicitly here too, not just relied on from the backend -
        // this path is identical for every caller, so a browser/intermediate
        // cache needs its own unambiguous signal not to reuse the bytes
        // across sessions (Sprint 18 Session 1 performance audit).
        "Cache-Control": "private, no-store",
      },
    });
  } catch (error) {
    return authErrorResponse(error);
  }
}

/** Forwards the browser's multipart upload as-is - `authenticatedBackendFormRequest`
 * is the one BFF helper that doesn't JSON-encode its body, since a
 * `FormData` file upload isn't JSON. */
export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const data = await authenticatedBackendFormRequest("/company-profile/logo", formData);
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}

export async function DELETE(_request: NextRequest) {
  try {
    await authenticatedBackendRequest("/company-profile/logo", { method: "DELETE" });
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    return authErrorResponse(error);
  }
}
