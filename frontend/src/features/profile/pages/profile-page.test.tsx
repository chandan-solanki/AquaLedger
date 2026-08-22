import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProfilePage } from "@/features/profile/pages/profile-page";

const {
  useAuthMock,
  updateProfileMock,
  uploadAvatarMock,
  deleteAvatarMock,
  changePasswordMock,
  toastSuccessMock,
  toastErrorMock,
} = vi.hoisted(() => ({
  useAuthMock: vi.fn(),
  updateProfileMock: vi.fn(),
  uploadAvatarMock: vi.fn(),
  deleteAvatarMock: vi.fn(),
  changePasswordMock: vi.fn(),
  toastSuccessMock: vi.fn(),
  toastErrorMock: vi.fn(),
}));

vi.mock("@/features/auth/hooks/use-auth", () => ({
  useAuth: useAuthMock,
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/profile",
}));

vi.mock("@/features/profile/hooks/use-update-profile", () => ({
  useUpdateProfile: () => ({ mutateAsync: updateProfileMock, isPending: false }),
}));

vi.mock("@/features/profile/hooks/use-upload-avatar", () => ({
  useUploadAvatar: () => ({ mutateAsync: uploadAvatarMock, isPending: false }),
}));

vi.mock("@/features/profile/hooks/use-delete-avatar", () => ({
  useDeleteAvatar: () => ({ mutateAsync: deleteAvatarMock, isPending: false }),
}));

vi.mock("@/features/profile/hooks/use-change-password", () => ({
  useChangePassword: () => ({ mutateAsync: changePasswordMock, isPending: false }),
}));

vi.mock("@/lib/toast", () => ({
  toastSuccess: toastSuccessMock,
  toastError: toastErrorMock,
}));

const USER = {
  id: "user-1",
  tenantId: "tenant-1",
  email: "jane@fisherp.local",
  username: "jane",
  fullName: "Jane Doe",
  phone: "9876543210",
  status: "active" as const,
  isSuperuser: false,
  lastLoginAt: "2026-08-20T10:15:00.000Z",
  roles: ["accountant"],
  permissions: ["invoice:view"],
  mustChangePassword: false,
  avatarUrl: null as string | null,
};

function mockAuth(overrides: Partial<ReturnType<typeof useAuthMock>> = {}) {
  useAuthMock.mockReturnValue({
    user: USER,
    isLoading: false,
    isAuthenticated: true,
    ...overrides,
  });
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ProfilePage", () => {
  it("renders the current user's name, initials, contact info and roles", () => {
    mockAuth();

    render(<ProfilePage />);

    expect(screen.getByRole("heading", { name: "Jane Doe" })).toBeInTheDocument();
    expect(screen.getByText("@jane")).toBeInTheDocument();
    expect(screen.getByText("jane@fisherp.local")).toBeInTheDocument();
    expect(screen.getByText("accountant")).toBeInTheDocument();
    expect(screen.getAllByText("JD").length).toBeGreaterThan(0);
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByLabelText(/phone/i)).toHaveValue("9876543210");
  });

  it("never renders an editable (or any) email field - email stays out of reach through this page", () => {
    mockAuth();

    render(<ProfilePage />);

    expect(screen.queryByLabelText(/email/i)).not.toBeInTheDocument();
  });

  it("falls back to 'No roles assigned' when the user has no roles", () => {
    mockAuth({ user: { ...USER, roles: [] } });

    render(<ProfilePage />);

    expect(screen.getByText("No roles assigned")).toBeInTheDocument();
  });

  it("shows 'Never' when the user has no last-login timestamp", () => {
    mockAuth({ user: { ...USER, lastLoginAt: null } });

    render(<ProfilePage />);

    expect(screen.getByText("Never")).toBeInTheDocument();
  });

  it("renders a loading skeleton instead of profile fields while the session loads", () => {
    mockAuth({ user: null, isLoading: true });

    render(<ProfilePage />);

    expect(screen.queryByRole("heading", { name: "Jane Doe" })).not.toBeInTheDocument();
  });

  it("offers Change/Remove instead of Upload once the user already has an avatar", () => {
    // Radix's AvatarImage never mounts an <img> in jsdom (it only swaps in
    // once the browser confirms the image loaded, which jsdom can't do for
    // a fake src) - "Change Photo" appearing instead of "Upload Photo" is
    // the observable proxy for "ProfilePage resolved a non-null avatarUrl
    // and passed it through" (the /api-prefixing itself mirrors
    // CompanyProfilePage's own identical, untested convention).
    mockAuth({ user: { ...USER, avatarUrl: "/profile/avatar" } });

    render(<ProfilePage />);

    expect(screen.getByLabelText(/change photo/i)).toBeInTheDocument();
  });

  it("saves the edited profile fields and shows a success toast", async () => {
    const user = userEvent.setup();
    updateProfileMock.mockResolvedValue(undefined);
    mockAuth();

    render(<ProfilePage />);
    await user.clear(screen.getByLabelText(/full name/i));
    await user.type(screen.getByLabelText(/full name/i), "Jane S. Doe");
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() =>
      expect(updateProfileMock).toHaveBeenCalledWith(
        expect.objectContaining({ full_name: "Jane S. Doe" })
      )
    );
    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith("Profile was updated."));
  });

  it("uploads a new avatar and shows a success toast", async () => {
    const user = userEvent.setup();
    uploadAvatarMock.mockResolvedValue(undefined);
    mockAuth();

    render(<ProfilePage />);
    const file = new File(["ok"], "avatar.png", { type: "image/png" });
    const input = document.getElementById("profile-avatar-input") as HTMLInputElement;
    await user.upload(input, file);

    await waitFor(() => expect(uploadAvatarMock).toHaveBeenCalledWith(file));
    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith("Photo uploaded."));
  });

  it("shows an error toast when the avatar upload fails, without crashing the page", async () => {
    const user = userEvent.setup();
    uploadAvatarMock.mockRejectedValue({
      category: "validation",
      status: 415,
      code: "INVALID_AVATAR_CONTENT_TYPE",
      message: "The uploaded file could not be decoded as a valid image",
    });
    mockAuth();

    render(<ProfilePage />);
    const file = new File(["ok"], "avatar.png", { type: "image/png" });
    const input = document.getElementById("profile-avatar-input") as HTMLInputElement;
    await user.upload(input, file);

    expect(await screen.findByRole("heading", { name: "Jane Doe" })).toBeInTheDocument();
    await waitFor(() =>
      expect(toastErrorMock).toHaveBeenCalledWith(
        "The uploaded file could not be decoded as a valid image"
      )
    );
  });

  it("removes the avatar and shows a success toast", async () => {
    const user = userEvent.setup();
    deleteAvatarMock.mockResolvedValue(undefined);
    mockAuth({ user: { ...USER, avatarUrl: "/profile/avatar" } });

    render(<ProfilePage />);
    await user.click(screen.getByRole("button", { name: /remove/i }));

    await waitFor(() => expect(deleteAvatarMock).toHaveBeenCalled());
    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith("Photo removed."));
  });

  it("renders an Account Security section with the Change Password form", () => {
    mockAuth();

    render(<ProfilePage />);

    expect(screen.getByText("Account Security")).toBeInTheDocument();
    expect(screen.getByLabelText(/current password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^new password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm new password/i)).toBeInTheDocument();
  });

  it("does not show the password-change-required notice for a user who doesn't need one", () => {
    mockAuth({ user: { ...USER, mustChangePassword: false } });

    render(<ProfilePage />);

    expect(screen.queryByText(/requires a password change/i)).not.toBeInTheDocument();
  });

  it("shows a password-change-required notice when the session says so", () => {
    mockAuth({ user: { ...USER, mustChangePassword: true } });

    render(<ProfilePage />);

    expect(screen.getByText(/requires a password change/i)).toBeInTheDocument();
  });

  it("changes the password and shows a success toast", async () => {
    const user = userEvent.setup();
    changePasswordMock.mockResolvedValue(undefined);
    mockAuth();

    render(<ProfilePage />);
    await user.type(screen.getByLabelText(/current password/i), "Admin@123");
    await user.type(screen.getByLabelText(/^new password/i), "NewStrong@1");
    await user.type(screen.getByLabelText(/confirm new password/i), "NewStrong@1");
    await user.click(screen.getByRole("button", { name: /change password/i }));

    await waitFor(() =>
      expect(changePasswordMock).toHaveBeenCalledWith({
        current_password: "Admin@123",
        new_password: "NewStrong@1",
      })
    );
    // Never the confirmation field - it exists only for client-side validation.
    expect(changePasswordMock).not.toHaveBeenCalledWith(
      expect.objectContaining({ confirm_password: expect.anything() })
    );
    await waitFor(() =>
      expect(toastSuccessMock).toHaveBeenCalledWith(
        "Password changed. You'll need to log in again on your other sessions."
      )
    );
  });
});
