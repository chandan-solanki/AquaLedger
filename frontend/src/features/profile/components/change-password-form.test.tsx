import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChangePasswordForm } from "@/features/profile/components/change-password-form";

const { toastErrorMock } = vi.hoisted(() => ({ toastErrorMock: vi.fn() }));

vi.mock("@/lib/toast", () => ({
  toastError: toastErrorMock,
}));

beforeEach(() => {
  vi.clearAllMocks();
});

async function fillAndSubmit(
  user: ReturnType<typeof userEvent.setup>,
  values: { current?: string; next?: string; confirm?: string }
) {
  if (values.current !== undefined) {
    await user.type(screen.getByLabelText(/current password/i), values.current);
  }
  if (values.next !== undefined) {
    await user.type(screen.getByLabelText(/^new password/i), values.next);
  }
  if (values.confirm !== undefined) {
    await user.type(screen.getByLabelText(/confirm new password/i), values.confirm);
  }
  await user.click(screen.getByRole("button", { name: /change password/i }));
}

describe("ChangePasswordForm", () => {
  it("renders all three password fields, empty, as password inputs", () => {
    render(<ChangePasswordForm onSubmit={vi.fn()} />);

    const current = screen.getByLabelText(/current password/i) as HTMLInputElement;
    const next = screen.getByLabelText(/^new password/i) as HTMLInputElement;
    const confirm = screen.getByLabelText(/confirm new password/i) as HTMLInputElement;

    expect(current).toHaveAttribute("type", "password");
    expect(next).toHaveAttribute("type", "password");
    expect(confirm).toHaveAttribute("type", "password");
    expect(current).toHaveValue("");
    expect(next).toHaveValue("");
    expect(confirm).toHaveValue("");
  });

  it("requires the current password", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<ChangePasswordForm onSubmit={onSubmit} />);

    await fillAndSubmit(user, { next: "NewStrong@1", confirm: "NewStrong@1" });

    expect(await screen.findByText(/current password is required/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("requires the new password", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<ChangePasswordForm onSubmit={onSubmit} />);

    await fillAndSubmit(user, { current: "Admin@123", confirm: "Admin@123" });

    // Scoped to the field's own alert text - the Confirm field's static
    // description also contains "8 characters", so an unscoped match would
    // be ambiguous.
    expect(await screen.findByText("Password must be at least 8 characters long")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("requires the confirmation field", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<ChangePasswordForm onSubmit={onSubmit} />);

    await fillAndSubmit(user, { current: "Admin@123", next: "NewStrong@1" });

    expect(await screen.findByText(/please confirm your new password/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("rejects a mismatched confirmation without calling onSubmit", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<ChangePasswordForm onSubmit={onSubmit} />);

    await fillAndSubmit(user, { current: "Admin@123", next: "NewStrong@1", confirm: "Different@1" });

    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("calls onSubmit with exactly the three form fields and clears them on success", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ChangePasswordForm onSubmit={onSubmit} />);

    await fillAndSubmit(user, { current: "Admin@123", next: "NewStrong@1", confirm: "NewStrong@1" });

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({
        current_password: "Admin@123",
        new_password: "NewStrong@1",
        confirm_password: "NewStrong@1",
      })
    );

    await waitFor(() => expect(screen.getByLabelText(/current password/i)).toHaveValue(""));
    expect(screen.getByLabelText(/^new password/i)).toHaveValue("");
    expect(screen.getByLabelText(/confirm new password/i)).toHaveValue("");
  });

  it("maps a wrong-current-password (401) error onto the Current Password field, not a toast", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockRejectedValue({
      category: "unauthorized",
      status: 401,
      code: "INVALID_CREDENTIALS",
      message: "Current password is incorrect",
    });
    render(<ChangePasswordForm onSubmit={onSubmit} />);

    await fillAndSubmit(user, { current: "wrong", next: "NewStrong@1", confirm: "NewStrong@1" });

    expect(await screen.findByText(/current password is incorrect/i)).toBeInTheDocument();
    expect(toastErrorMock).not.toHaveBeenCalled();
    // The failed attempt's values are not silently wiped - only a
    // successful change clears the form.
    expect(screen.getByLabelText(/^new password/i)).toHaveValue("NewStrong@1");
  });

  it("maps a weak-new-password (422) field error onto the New Password field", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockRejectedValue({
      category: "validation",
      status: 422,
      code: "VALIDATION_ERROR",
      message: "Password does not meet policy requirements",
      fieldErrors: { new_password: ["Password must contain an uppercase letter"] },
    });
    render(<ChangePasswordForm onSubmit={onSubmit} />);

    await fillAndSubmit(user, { current: "Admin@123", next: "newstrong1!", confirm: "newstrong1!" });

    expect(await screen.findByText(/password must contain an uppercase letter/i)).toBeInTheDocument();
    expect(toastErrorMock).not.toHaveBeenCalled();
  });

  it("shows a toast for any other failure, without echoing password values", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockRejectedValue({
      category: "server",
      status: 500,
      code: "INTERNAL_ERROR",
      message: "An unexpected error occurred.",
    });
    render(<ChangePasswordForm onSubmit={onSubmit} />);

    await fillAndSubmit(user, { current: "Admin@123", next: "NewStrong@1", confirm: "NewStrong@1" });

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith("An unexpected error occurred."));
    expect(toastErrorMock).not.toHaveBeenCalledWith(expect.stringContaining("NewStrong@1"));
  });

  it("never renders a submitted password value inside any on-screen error or success text", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockRejectedValue({
      category: "unauthorized",
      status: 401,
      code: "INVALID_CREDENTIALS",
      message: "Current password is incorrect",
    });
    render(<ChangePasswordForm onSubmit={onSubmit} />);

    await fillAndSubmit(user, { current: "Sup3rSecret!", next: "NewStrong@1", confirm: "NewStrong@1" });
    await screen.findByText(/current password is incorrect/i);

    expect(screen.queryByText("Sup3rSecret!")).not.toBeInTheDocument();
    expect(screen.queryByText("NewStrong@1")).not.toBeInTheDocument();
  });

  it("disables the submit button while submitting to prevent duplicate submission", async () => {
    const user = userEvent.setup();
    let resolveSubmit: () => void = () => {};
    const onSubmit = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveSubmit = resolve;
        })
    );
    render(<ChangePasswordForm onSubmit={onSubmit} />);

    await fillAndSubmit(user, { current: "Admin@123", next: "NewStrong@1", confirm: "NewStrong@1" });

    await waitFor(() => expect(screen.getByRole("button", { name: /changing/i })).toBeDisabled());
    expect(onSubmit).toHaveBeenCalledTimes(1);

    resolveSubmit();
    await waitFor(() => expect(screen.getByRole("button", { name: /change password/i })).not.toBeDisabled());
  });

  it("disables all fields when the disabled prop is set", () => {
    render(<ChangePasswordForm onSubmit={vi.fn()} disabled />);

    expect(screen.getByLabelText(/current password/i)).toBeDisabled();
    expect(screen.getByLabelText(/^new password/i)).toBeDisabled();
    expect(screen.getByLabelText(/confirm new password/i)).toBeDisabled();
    expect(screen.getByRole("button", { name: /change password/i })).toBeDisabled();
  });
});
