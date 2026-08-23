import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TenantForm } from "@/features/platform/components/tenant-form";

const { toastErrorMock } = vi.hoisted(() => ({ toastErrorMock: vi.fn() }));

vi.mock("@/lib/toast", () => ({
  toastError: toastErrorMock,
}));

const VALID = {
  name: "Ocean Fresh Traders",
  slug: "ocean-fresh-traders",
  fullName: "Priya Nair",
  email: "owner@oceanfresh.example",
  username: "oceanfresh-owner",
  password: "TempPass@123",
};

async function fillValidForm(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/tenant name/i), VALID.name);
  await user.type(screen.getByLabelText(/^slug/i), VALID.slug);
  await user.type(screen.getByLabelText(/full name/i), VALID.fullName);
  await user.type(screen.getByLabelText(/^email/i), VALID.email);
  await user.type(screen.getByLabelText(/^username/i), VALID.username);
  await user.type(screen.getByLabelText(/^password/i), VALID.password);
  await user.type(screen.getByLabelText(/confirm password/i), VALID.password);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("TenantForm", () => {
  it("blocks submission and shows required-field errors when submitted empty", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<TenantForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: /provision tenant/i }));

    expect(await screen.findByText("Tenant name is required")).toBeInTheDocument();
    expect(screen.getByText("Slug is required")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("rejects an invalid email address", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<TenantForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    await fillValidForm(user);
    await user.clear(screen.getByLabelText(/^email/i));
    await user.type(screen.getByLabelText(/^email/i), "not-an-email");
    await user.click(screen.getByRole("button", { name: /provision tenant/i }));

    expect(await screen.findByText(/enter a valid email address/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("rejects a slug with uppercase letters or invalid characters", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<TenantForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    await fillValidForm(user);
    await user.clear(screen.getByLabelText(/^slug/i));
    await user.type(screen.getByLabelText(/^slug/i), "Not A Valid Slug!");
    await user.click(screen.getByRole("button", { name: /provision tenant/i }));

    expect(
      await screen.findByText(/lowercase letters, numbers and single hyphens only/i)
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("rejects a mismatched password confirmation", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<TenantForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    await fillValidForm(user);
    await user.clear(screen.getByLabelText(/confirm password/i));
    await user.type(screen.getByLabelText(/confirm password/i), "SomethingElse@123");
    await user.click(screen.getByRole("button", { name: /provision tenant/i }));

    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("rejects a weak password that fails the policy", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<TenantForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    await fillValidForm(user);
    await user.clear(screen.getByLabelText(/^password/i));
    await user.clear(screen.getByLabelText(/confirm password/i));
    await user.type(screen.getByLabelText(/^password/i), "weak");
    await user.type(screen.getByLabelText(/confirm password/i), "weak");
    await user.click(screen.getByRole("button", { name: /provision tenant/i }));

    expect(await screen.findByText(/password must be at least 8 characters/i)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits exactly the TenantCreateRequest shape - no confirm_password field", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<TenantForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: /provision tenant/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    const submitted = onSubmit.mock.calls[0][0];
    expect(submitted).toEqual({
      name: VALID.name,
      slug: VALID.slug,
      administrator: {
        full_name: VALID.fullName,
        email: VALID.email,
        username: VALID.username,
        password: VALID.password,
      },
      confirm_password: VALID.password,
    });
    expect(submitted).not.toHaveProperty("plan");
    expect(submitted).not.toHaveProperty("base_currency");
  });

  it("prevents duplicate submission while pending", async () => {
    let resolveSubmit: () => void = () => {};
    const onSubmit = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveSubmit = resolve;
        })
    );
    const user = userEvent.setup();
    render(<TenantForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    await fillValidForm(user);
    const submitButton = screen.getByRole("button", { name: /provision tenant/i });
    await user.click(submitButton);

    await waitFor(() => expect(submitButton).toBeDisabled());
    await user.click(submitButton);
    expect(onSubmit).toHaveBeenCalledTimes(1);

    resolveSubmit();
  });

  it("maps a duplicate-slug 422 field error onto the slug field, not a toast", async () => {
    const onSubmit = vi.fn().mockRejectedValue({
      category: "validation",
      status: 422,
      code: "VALIDATION_ERROR",
      message: "Validation failed",
      fieldErrors: { slug: ["A tenant with this slug already exists"] },
    });
    const user = userEvent.setup();
    render(<TenantForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: /provision tenant/i }));

    expect(await screen.findByText("A tenant with this slug already exists")).toBeInTheDocument();
    expect(toastErrorMock).not.toHaveBeenCalled();
  });

  it("maps a nested administrator.password policy error onto the password field", async () => {
    const onSubmit = vi.fn().mockRejectedValue({
      category: "validation",
      status: 422,
      code: "VALIDATION_ERROR",
      message: "Validation failed",
      fieldErrors: { "administrator.password": ["Password does not meet policy requirements"] },
    });
    const user = userEvent.setup();
    render(<TenantForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: /provision tenant/i }));

    expect(await screen.findByText("Password does not meet policy requirements")).toBeInTheDocument();
  });

  it("shows a toast for a non-field error (e.g. a 409 conflict) rather than a form field", async () => {
    const onSubmit = vi.fn().mockRejectedValue({
      category: "conflict",
      status: 409,
      code: "DUPLICATE_USER_EMAIL",
      message: "A user with this email already exists",
    });
    const user = userEvent.setup();
    render(<TenantForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: /provision tenant/i }));

    await waitFor(() =>
      expect(toastErrorMock).toHaveBeenCalledWith("A user with this email already exists")
    );
  });

  it("never renders the password value in the DOM outside the password input itself", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    const { container } = render(<TenantForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: /provision tenant/i }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));

    expect(container.textContent).not.toContain(VALID.password);
  });
});
