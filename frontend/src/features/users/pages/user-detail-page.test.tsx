import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  useAuthMock,
  useUserMock,
  useUpdateUserStatusMock,
  resetPasswordMutateAsyncMock,
  toastSuccessMock,
  toastErrorMock,
} = vi.hoisted(() => ({
  useAuthMock: vi.fn(),
  useUserMock: vi.fn(),
  useUpdateUserStatusMock: vi.fn(),
  resetPasswordMutateAsyncMock: vi.fn(),
  toastSuccessMock: vi.fn(),
  toastErrorMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "target-user-1" }),
  usePathname: () => "/users/target-user-1",
}));

vi.mock("@/features/auth/hooks/use-auth", () => ({
  useAuth: useAuthMock,
}));

vi.mock("@/features/users/hooks/use-user", () => ({
  useUser: useUserMock,
}));

vi.mock("@/features/users/hooks/use-update-user-status", () => ({
  useUpdateUserStatus: useUpdateUserStatusMock,
}));

vi.mock("@/features/users/hooks/use-reset-user-password", () => ({
  useResetUserPassword: () => ({ mutateAsync: resetPasswordMutateAsyncMock, isPending: false }),
}));

vi.mock("@/lib/toast", () => ({
  toastSuccess: toastSuccessMock,
  toastError: toastErrorMock,
}));

import { UserDetailPage } from "@/features/users/pages/user-detail-page";

const CURRENT_USER = {
  id: "admin-1",
  tenantId: "tenant-1",
  email: "admin@fisherp.local",
  username: "admin",
  fullName: "Super Admin",
  phone: null,
  status: "active" as const,
  isSuperuser: false,
  isPlatformAdmin: false,
  lastLoginAt: null,
  roles: ["admin"],
  permissions: ["user:manage"],
  mustChangePassword: false,
  avatarUrl: null as string | null,
};

const TARGET_USER = {
  id: "target-user-1",
  tenantId: "tenant-1",
  email: "priya@fisherp.local",
  username: "priya",
  fullName: "Priya Nair",
  phone: null,
  status: "active" as const,
  isSuperuser: false,
  lastLoginAt: null,
  role: { id: "role-1", name: "accountant", description: null },
  createdAt: "2026-08-01T00:00:00Z",
  updatedAt: "2026-08-01T00:00:00Z",
};

function mockAuth(overrides: Partial<typeof CURRENT_USER> = {}) {
  const user = { ...CURRENT_USER, ...overrides };
  useAuthMock.mockReturnValue({ user, permissions: user.permissions });
}

function mockTargetUser(overrides: Partial<typeof TARGET_USER> = {}) {
  useUserMock.mockReturnValue({
    data: { ...TARGET_USER, ...overrides },
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  mockAuth();
  mockTargetUser();
  useUpdateUserStatusMock.mockReturnValue({ mutate: vi.fn(), isPending: false });
});

describe("UserDetailPage - Reset Password", () => {
  it("offers a Reset Password action for another user", () => {
    render(<UserDetailPage />);

    expect(screen.getByRole("button", { name: /reset password/i })).toBeEnabled();
  });

  it("disables Reset Password when viewing your own account", () => {
    mockTargetUser({ id: CURRENT_USER.id });
    render(<UserDetailPage />);

    expect(screen.getByRole("button", { name: /reset password/i })).toBeDisabled();
  });

  it("disables Reset Password on a super_admin target for a non-superuser actor", () => {
    mockAuth({ isSuperuser: false });
    mockTargetUser({ isSuperuser: true });
    render(<UserDetailPage />);

    expect(screen.getByRole("button", { name: /reset password/i })).toBeDisabled();
  });

  it("enables Reset Password on a super_admin target for a superuser actor", () => {
    mockAuth({ isSuperuser: true });
    mockTargetUser({ isSuperuser: true });
    render(<UserDetailPage />);

    expect(screen.getByRole("button", { name: /reset password/i })).toBeEnabled();
  });

  it("opens the Reset Password dialog and submits the new password, showing a success toast", async () => {
    const user = userEvent.setup();
    resetPasswordMutateAsyncMock.mockResolvedValue(undefined);
    render(<UserDetailPage />);

    await user.click(screen.getByRole("button", { name: /reset password/i }));
    expect(screen.getByText("Reset password for Priya Nair")).toBeInTheDocument();

    const dialog = screen.getByRole("dialog");
    await user.type(within(dialog).getByLabelText(/^new password/i), "NewStrong@1");
    await user.type(within(dialog).getByLabelText(/confirm new password/i), "NewStrong@1");
    await user.click(within(dialog).getByRole("button", { name: /^reset password$/i }));

    await waitFor(() =>
      expect(resetPasswordMutateAsyncMock).toHaveBeenCalledWith({
        id: "target-user-1",
        newPassword: "NewStrong@1",
      })
    );
    await waitFor(() =>
      expect(toastSuccessMock).toHaveBeenCalledWith("Priya Nair's password was reset.")
    );
  });
});
