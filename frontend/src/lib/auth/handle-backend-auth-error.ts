import "server-only";

import { NextResponse } from "next/server";

import { BackendAuthError } from "@/lib/auth/backend-auth-client";
import { apiErrorToEnvelope } from "@/lib/http-error";

/** Shared by every auth route handler so each doesn't re-implement this mapping. */
export function authErrorResponse(error: unknown): NextResponse {
  if (error instanceof BackendAuthError) {
    return NextResponse.json(apiErrorToEnvelope(error.apiError), {
      status: error.apiError.status ?? 500,
    });
  }

  console.error("Unexpected auth error", error);
  return NextResponse.json(
    apiErrorToEnvelope({
      category: "server",
      status: 500,
      code: "INTERNAL_ERROR",
      message: "An unexpected error occurred.",
    }),
    { status: 500 }
  );
}
