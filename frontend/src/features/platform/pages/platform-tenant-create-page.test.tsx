import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PlatformTenantCreatePage } from "@/features/platform/pages/platform-tenant-create-page";

const { pushMock, createTenantMutateAsyncMock, toastSuccessMock, toastErrorMock, consoleLogSpy } = vi.hoisted(
  () => ({
    pushMock: vi.fn(),
    createTenantMutateAsyncMock: vi.fn(),
    toastSuccessMock: vi.fn(),
    toastErrorMock: vi.fn(),
    consoleLogSpy: vi.fn(),
  })
);

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  usePathname: () => "/platform/tenants/new",
}));

vi.mock("@/features/platform/hooks/use-create-tenant", () => ({
  useCreateTenant: () => ({ mutateAsync: createTenantMutateAsyncMock, isPending: false }),
}));

vi.mock("@/lib/toast", () => ({
  toastSuccess: toastSuccessMock,
  toastError: toastErrorMock,
  toastLoading: vi.fn(() => "toast-id"),
  dismissToast: vi.fn(),
}));

const VALID = {
  name: "Ocean Fresh Traders",
  slug: "ocean-fresh-traders",
  fullName: "Priya Nair",
  email: "owner@oceanfresh.example",
  username: "oceanfresh-owner",
  password: "TempPass@123",
};

async function fillAndSubmit(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/tenant name/i), VALID.name);
  await user.type(screen.getByLabelText(/^slug/i), VALID.slug);
  await user.type(screen.getByLabelText(/full name/i), VALID.fullName);
  await user.type(screen.getByLabelText(/^email/i), VALID.email);
  await user.type(screen.getByLabelText(/^username/i), VALID.username);
  await user.type(screen.getByLabelText(/^password/i), VALID.password);
  await user.type(screen.getByLabelText(/confirm password/i), VALID.password);
  await user.click(screen.getByRole("button", { name: /provision tenant/i }));
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(console, "log").mockImplementation(consoleLogSpy);
  vi.spyOn(console, "error").mockImplementation(() => {});
});

describe("PlatformTenantCreatePage", () => {
  it("submits the correct payload, shows a success toast, and navigates to the new tenant's detail page", async () => {
    createTenantMutateAsyncMock.mockResolvedValue({
      tenant: {
        id: "tenant-new-1",
        name: VALID.name,
        slug: VALID.slug,
        status: "active",
        plan: null,
        baseCurrency: "INR",
        fiscalYearStartMonth: 4,
        createdAt: "2026-08-22T00:00:00Z",
        updatedAt: "2026-08-22T00:00:00Z",
      },
      administrator: {
        id: "user-new-1",
        email: VALID.email,
        username: VALID.username,
        fullName: VALID.fullName,
      },
    });

    const user = userEvent.setup();
    render(<PlatformTenantCreatePage />);
    await fillAndSubmit(user);

    await waitFor(() =>
      expect(createTenantMutateAsyncMock).toHaveBeenCalledWith({
        name: VALID.name,
        slug: VALID.slug,
        administrator: {
          email: VALID.email,
          username: VALID.username,
          full_name: VALID.fullName,
          password: VALID.password,
        },
      })
    );
    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith("Ocean Fresh Traders was provisioned."));
    expect(pushMock).toHaveBeenCalledWith("/platform/tenants/tenant-new-1");
  });

  it("maps a duplicate slug conflict to the form's field error, without navigating", async () => {
    createTenantMutateAsyncMock.mockRejectedValue({
      category: "conflict",
      status: 409,
      code: "DUPLICATE_TENANT_SLUG",
      message: "A tenant with this slug already exists",
    });

    const user = userEvent.setup();
    render(<PlatformTenantCreatePage />);
    await fillAndSubmit(user);

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith("A tenant with this slug already exists"));
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("never logs the administrator password to the console on submission", async () => {
    createTenantMutateAsyncMock.mockResolvedValue({
      tenant: {
        id: "tenant-new-1",
        name: VALID.name,
        slug: VALID.slug,
        status: "active",
        plan: null,
        baseCurrency: "INR",
        fiscalYearStartMonth: 4,
        createdAt: "2026-08-22T00:00:00Z",
        updatedAt: "2026-08-22T00:00:00Z",
      },
      administrator: { id: "user-new-1", email: VALID.email, username: VALID.username, fullName: VALID.fullName },
    });

    const user = userEvent.setup();
    render(<PlatformTenantCreatePage />);
    await fillAndSubmit(user);

    await waitFor(() => expect(pushMock).toHaveBeenCalled());

    for (const call of consoleLogSpy.mock.calls) {
      for (const arg of call) {
        expect(JSON.stringify(arg)).not.toContain(VALID.password);
      }
    }
    expect(toastSuccessMock.mock.calls.flat().join(" ")).not.toContain(VALID.password);
  });

  it("never includes the password in the success or error toast text", async () => {
    createTenantMutateAsyncMock.mockRejectedValue({
      category: "conflict",
      status: 409,
      code: "DUPLICATE_USER_EMAIL",
      message: "A user with this email already exists",
    });

    const user = userEvent.setup();
    render(<PlatformTenantCreatePage />);
    await fillAndSubmit(user);

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalled());
    expect(toastErrorMock.mock.calls.flat().join(" ")).not.toContain(VALID.password);
  });
});
