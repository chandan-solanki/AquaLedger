import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/profile/notifications",
}));

import { NotificationPreferencesPage } from "@/features/notifications/pages/notification-preferences-page";

describe("NotificationPreferencesPage", () => {
  it("renders an honest explanation instead of any preference toggle", () => {
    render(<NotificationPreferencesPage />);

    expect(screen.getByText("Notification Preferences")).toBeInTheDocument();
    expect(screen.getByText("Nothing to configure yet")).toBeInTheDocument();
    // No form control of any kind - there's nothing real to persist.
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("never claims notifications are actually sent", () => {
    render(<NotificationPreferencesPage />);

    const body = document.body.textContent ?? "";
    expect(body).not.toMatch(/you will receive/i);
    expect(body).not.toMatch(/you'll receive/i);
  });
});
