import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { UserMenu } from "@/components/layout/user-menu";

const { useCurrentUserMock, useAuthMock, pushMock } = vi.hoisted(() => ({
  useCurrentUserMock: vi.fn(),
  useAuthMock: vi.fn(),
  pushMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/features/auth/hooks/use-current-user", () => ({
  useCurrentUser: useCurrentUserMock,
}));

vi.mock("@/features/auth/hooks/use-auth", () => ({
  useAuth: useAuthMock,
}));

const USER = {
  id: "user-1",
  tenantId: "tenant-1",
  email: "jane@fisherp.local",
  username: "jane",
  fullName: "Jane Doe",
  phone: null,
  status: "active" as const,
  isSuperuser: false,
  lastLoginAt: null,
  roles: [],
  permissions: [],
  mustChangePassword: false,
};

beforeEach(() => {
  vi.clearAllMocks();
  useCurrentUserMock.mockReturnValue(USER);
  useAuthMock.mockReturnValue({ logout: vi.fn() });
});

describe("UserMenu", () => {
  it("navigates to /profile when 'Profile' is selected", async () => {
    const user = userEvent.setup();
    render(<UserMenu />);

    await user.click(screen.getByRole("button", { name: /Jane Doe/i }));
    await user.click(screen.getByText("Profile"));

    expect(pushMock).toHaveBeenCalledWith("/profile");
  });

  it("navigates to /profile/notifications when 'Notification Preferences' is selected, and closes the menu", async () => {
    const user = userEvent.setup();
    render(<UserMenu />);

    await user.click(screen.getByRole("button", { name: /Jane Doe/i }));
    await user.click(screen.getByText("Notification Preferences"));

    expect(pushMock).toHaveBeenCalledWith("/profile/notifications");
    expect(screen.queryByText("Notification Preferences")).not.toBeInTheDocument();
  });

  it("navigates to /profile/appearance when 'Appearance' is selected, and closes the menu", async () => {
    const user = userEvent.setup();
    render(<UserMenu />);

    await user.click(screen.getByRole("button", { name: /Jane Doe/i }));
    await user.click(screen.getByText("Appearance"));

    expect(pushMock).toHaveBeenCalledWith("/profile/appearance");
    expect(screen.queryByText("Appearance")).not.toBeInTheDocument();
  });
});
