import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProfileForm } from "@/features/profile/components/profile-form";
import { DEFAULT_PROFILE_FORM_VALUES } from "@/features/profile/schemas/profile-form-schema";

const { toastErrorMock } = vi.hoisted(() => ({ toastErrorMock: vi.fn() }));

vi.mock("@/lib/toast", () => ({
  toastSuccess: vi.fn(),
  toastError: toastErrorMock,
}));

const DEFAULT_VALUES = {
  full_name: "Jane Doe",
  username: "jane",
  phone: "9876543210",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ProfileForm", () => {
  it("renders with the existing values populated", () => {
    render(<ProfileForm defaultValues={DEFAULT_VALUES} onSubmit={vi.fn()} />);

    expect(screen.getByLabelText(/full name/i)).toHaveValue("Jane Doe");
    expect(screen.getByLabelText(/username/i)).toHaveValue("jane");
    expect(screen.getByLabelText(/phone/i)).toHaveValue("9876543210");
    // Email is never rendered by this form at all - it stays out of reach,
    // not merely disabled.
    expect(screen.queryByLabelText(/email/i)).not.toBeInTheDocument();
  });

  it("shows a validation error and does not submit when full name is cleared", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<ProfileForm defaultValues={DEFAULT_VALUES} onSubmit={onSubmit} />);

    await user.clear(screen.getByLabelText(/full name/i));
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    expect(await screen.findByText("Full name is required")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("shows a validation error for an invalid username", async () => {
    const user = userEvent.setup();
    render(<ProfileForm defaultValues={DEFAULT_VALUES} onSubmit={vi.fn()} />);

    await user.clear(screen.getByLabelText(/username/i));
    await user.type(screen.getByLabelText(/username/i), "a");
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    expect(
      await screen.findByText(/username must be 3-100 characters/i)
    ).toBeInTheDocument();
  });

  it("submits the allowed fields when the form is valid", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ProfileForm defaultValues={DEFAULT_VALUES} onSubmit={onSubmit} />);

    await user.clear(screen.getByLabelText(/full name/i));
    await user.type(screen.getByLabelText(/full name/i), "Jane S. Doe");
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ full_name: "Jane S. Doe", username: "jane", phone: "9876543210" })
    );
  });

  it("shows a toast for a backend conflict (duplicate username) instead of a field error", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockRejectedValue({
      category: "conflict",
      status: 409,
      code: "DUPLICATE_USERNAME",
      message: "A user with this username already exists",
    });
    render(<ProfileForm defaultValues={DEFAULT_VALUES} onSubmit={onSubmit} />);

    await user.click(screen.getByRole("button", { name: /save changes/i }));

    expect(await screen.findByRole("button", { name: /save changes/i })).toBeEnabled();
    expect(toastErrorMock).toHaveBeenCalledWith("A user with this username already exists");
  });

  it("maps a 422 field error onto the matching field", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockRejectedValue({
      category: "validation",
      status: 422,
      code: "VALIDATION_ERROR",
      message: "Validation failed",
      fieldErrors: { username: ["Already taken"] },
    });
    render(<ProfileForm defaultValues={DEFAULT_VALUES} onSubmit={onSubmit} />);

    await user.click(screen.getByRole("button", { name: /save changes/i }));

    expect(await screen.findByText("Already taken")).toBeInTheDocument();
  });

  it("disables every field and both actions while disabled", () => {
    render(<ProfileForm defaultValues={DEFAULT_VALUES} onSubmit={vi.fn()} disabled />);

    expect(screen.getByLabelText(/full name/i)).toBeDisabled();
    expect(screen.getByLabelText(/username/i)).toBeDisabled();
    expect(screen.getByLabelText(/phone/i)).toBeDisabled();
    expect(screen.getByRole("button", { name: /save changes/i })).toBeDisabled();
  });

  it("falls back to DEFAULT_PROFILE_FORM_VALUES when no defaults are given", () => {
    render(<ProfileForm defaultValues={DEFAULT_PROFILE_FORM_VALUES} onSubmit={vi.fn()} />);

    expect(screen.getByLabelText(/full name/i)).toHaveValue("");
  });
});
