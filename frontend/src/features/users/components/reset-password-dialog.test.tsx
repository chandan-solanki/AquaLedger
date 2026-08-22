import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ResetPasswordDialog } from "@/features/users/components/reset-password-dialog";

const { toastErrorMock } = vi.hoisted(() => ({ toastErrorMock: vi.fn() }));

vi.mock("@/lib/toast", () => ({
  toastError: toastErrorMock,
}));

beforeEach(() => {
  vi.clearAllMocks();
});

async function fillAndSubmit(
  user: ReturnType<typeof userEvent.setup>,
  values: { next?: string; confirm?: string }
) {
  if (values.next !== undefined) {
    await user.type(screen.getByLabelText(/^new password/i), values.next);
  }
  if (values.confirm !== undefined) {
    await user.type(screen.getByLabelText(/confirm new password/i), values.confirm);
  }
  await user.click(screen.getByRole("button", { name: /^reset password$/i }));
}

describe("ResetPasswordDialog", () => {
  it("renders both password fields, empty, when open", () => {
    render(
      <ResetPasswordDialog open onOpenChange={vi.fn()} userName="Priya Nair" onSubmit={vi.fn()} />
    );

    expect(screen.getByText("Reset password for Priya Nair")).toBeInTheDocument();
    expect(screen.getByLabelText(/^new password/i)).toHaveValue("");
    expect(screen.getByLabelText(/confirm new password/i)).toHaveValue("");
  });

  it("renders nothing when closed", () => {
    render(
      <ResetPasswordDialog
        open={false}
        onOpenChange={vi.fn()}
        userName="Priya Nair"
        onSubmit={vi.fn()}
      />
    );

    expect(screen.queryByText("Reset password for Priya Nair")).not.toBeInTheDocument();
  });

  it("rejects a mismatched confirmation without calling onSubmit", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(
      <ResetPasswordDialog open onOpenChange={vi.fn()} userName="Priya Nair" onSubmit={onSubmit} />
    );

    await fillAndSubmit(user, { next: "NewStrong@1", confirm: "Different@1" });

    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("rejects a password that fails the policy client-side", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(
      <ResetPasswordDialog open onOpenChange={vi.fn()} userName="Priya Nair" onSubmit={onSubmit} />
    );

    await fillAndSubmit(user, { next: "weak", confirm: "weak" });

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("calls onSubmit with the new password (never the confirmation) and clears the form on success", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <ResetPasswordDialog open onOpenChange={vi.fn()} userName="Priya Nair" onSubmit={onSubmit} />
    );

    await fillAndSubmit(user, { next: "NewStrong@1", confirm: "NewStrong@1" });

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ new_password: "NewStrong@1" })
      )
    );
    await waitFor(() => expect(screen.getByLabelText(/^new password/i)).toHaveValue(""));
  });

  it("maps a weak-password 422 field error from the backend onto New Password", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockRejectedValue({
      category: "validation",
      status: 422,
      code: "VALIDATION_ERROR",
      message: "Password does not meet policy requirements",
      fieldErrors: { new_password: ["Password must contain a number"] },
    });
    render(
      <ResetPasswordDialog open onOpenChange={vi.fn()} userName="Priya Nair" onSubmit={onSubmit} />
    );

    await fillAndSubmit(user, { next: "NewStrong@Aa", confirm: "NewStrong@Aa" });

    expect(await screen.findByText(/password must contain a number/i)).toBeInTheDocument();
    expect(toastErrorMock).not.toHaveBeenCalled();
  });

  it("shows a toast for a non-field business-rule error (e.g. cannot reset your own password)", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockRejectedValue({
      category: "unknown",
      status: 422,
      code: "CANNOT_RESET_OWN_PASSWORD",
      message: "Use Change Password in your own profile to change your own password",
    });
    render(
      <ResetPasswordDialog open onOpenChange={vi.fn()} userName="Priya Nair" onSubmit={onSubmit} />
    );

    await fillAndSubmit(user, { next: "NewStrong@1", confirm: "NewStrong@1" });

    await waitFor(() =>
      expect(toastErrorMock).toHaveBeenCalledWith(
        "Use Change Password in your own profile to change your own password"
      )
    );
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
    render(
      <ResetPasswordDialog open onOpenChange={vi.fn()} userName="Priya Nair" onSubmit={onSubmit} />
    );

    await fillAndSubmit(user, { next: "NewStrong@1", confirm: "NewStrong@1" });

    await waitFor(() => expect(screen.getByRole("button", { name: /resetting/i })).toBeDisabled());
    expect(onSubmit).toHaveBeenCalledTimes(1);

    resolveSubmit();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /^reset password$/i })).not.toBeDisabled()
    );
  });
});
