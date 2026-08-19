import { NextResponse } from "next/server";

import { authenticatedBackendRequest } from "@/lib/auth/authenticated-backend-request";
import { authErrorResponse } from "@/lib/auth/handle-backend-auth-error";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const data = await authenticatedBackendRequest(`/users/${id}`);
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}

export async function PUT(request: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const body = await request.json();
    const data = await authenticatedBackendRequest(`/users/${id}`, { method: "PUT", body });
    return NextResponse.json(data);
  } catch (error) {
    return authErrorResponse(error);
  }
}
