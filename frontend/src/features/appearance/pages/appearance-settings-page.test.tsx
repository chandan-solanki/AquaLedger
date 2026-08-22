import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { useThemeMock } = vi.hoisted(() => ({ useThemeMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  usePathname: () => "/profile/appearance",
}));

vi.mock("next-themes", () => ({
  useTheme: useThemeMock,
}));

import { AppearanceSettingsPage } from "@/features/appearance/pages/appearance-settings-page";

function mockTheme(theme: string | undefined, extra: Record<string, unknown> = {}) {
  useThemeMock.mockReturnValue({ theme, resolvedTheme: theme, setTheme: setThemeMock, ...extra });
}

const setThemeMock = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  mockTheme("system");
});

describe("AppearanceSettingsPage", () => {
  it("renders all three theme options with their explanations", () => {
    render(<AppearanceSettingsPage />);

    expect(screen.getByText("Light")).toBeInTheDocument();
    expect(screen.getByText("Always use the light appearance.")).toBeInTheDocument();
    expect(screen.getByText("Dark")).toBeInTheDocument();
    expect(screen.getByText("Always use the dark appearance.")).toBeInTheDocument();
    expect(screen.getByText("System")).toBeInTheDocument();
    expect(screen.getByText("Follow your device or operating system preference.")).toBeInTheDocument();
  });

  it("marks the option matching the current theme as selected", () => {
    mockTheme("dark");
    render(<AppearanceSettingsPage />);

    expect(screen.getByRole("radio", { name: /dark/i })).toBeChecked();
    expect(screen.getByRole("radio", { name: /light/i })).not.toBeChecked();
    expect(screen.getByRole("radio", { name: /system/i })).not.toBeChecked();
  });

  it("selecting Light calls the existing theme authority with 'light'", async () => {
    const user = userEvent.setup();
    mockTheme("dark");
    render(<AppearanceSettingsPage />);

    await user.click(screen.getByRole("radio", { name: /light/i }));

    expect(setThemeMock).toHaveBeenCalledWith("light");
    expect(setThemeMock).toHaveBeenCalledTimes(1);
  });

  it("selecting Dark calls the existing theme authority with 'dark'", async () => {
    const user = userEvent.setup();
    mockTheme("light");
    render(<AppearanceSettingsPage />);

    await user.click(screen.getByRole("radio", { name: /dark/i }));

    expect(setThemeMock).toHaveBeenCalledWith("dark");
  });

  it("selecting System calls the existing theme authority with 'system'", async () => {
    const user = userEvent.setup();
    mockTheme("light");
    render(<AppearanceSettingsPage />);

    await user.click(screen.getByRole("radio", { name: /system/i }));

    expect(setThemeMock).toHaveBeenCalledWith("system");
  });

  it("keeps System selected even when the OS resolves it to dark - selected preference is not the resolved theme", () => {
    mockTheme("system", { resolvedTheme: "dark" });
    render(<AppearanceSettingsPage />);

    expect(screen.getByRole("radio", { name: /system/i })).toBeChecked();
    expect(screen.getByRole("radio", { name: /dark/i })).not.toBeChecked();
  });

  it("reflects the theme hook's value directly rather than tracking its own selection state", () => {
    mockTheme("light");
    const { rerender } = render(<AppearanceSettingsPage />);
    expect(screen.getByRole("radio", { name: /light/i })).toBeChecked();

    // Nothing was clicked - only the hook's return value changed. If this
    // page kept a second, duplicated "selected" state instead of reading
    // useTheme() directly, Light would incorrectly stay checked here.
    mockTheme("dark");
    rerender(<AppearanceSettingsPage />);

    expect(screen.getByRole("radio", { name: /dark/i })).toBeChecked();
    expect(screen.getByRole("radio", { name: /light/i })).not.toBeChecked();
  });
});
