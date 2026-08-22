import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AvatarUploader } from "@/features/profile/components/avatar-uploader";

const { toastErrorMock } = vi.hoisted(() => ({ toastErrorMock: vi.fn() }));

vi.mock("@/lib/toast", () => ({
  toastError: toastErrorMock,
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AvatarUploader", () => {
  it("shows the initials fallback and an Upload action when there is no avatar", () => {
    render(
      <AvatarUploader avatarUrl={null} fullName="Jane Doe" onUpload={vi.fn()} onRemove={vi.fn()} />
    );

    expect(screen.getByText("JD")).toBeInTheDocument();
    // The trigger is a <label htmlFor> wrapping a styled span, not a real
    // <button> - `getByLabelText` follows that association to the input.
    expect(screen.getByLabelText(/upload photo/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /remove/i })).not.toBeInTheDocument();
  });

  it("offers Change/Remove actions when an avatar already exists", () => {
    render(
      <AvatarUploader
        avatarUrl="/api/profile/avatar"
        fullName="Jane Doe"
        onUpload={vi.fn()}
        onRemove={vi.fn()}
      />
    );

    expect(screen.getByLabelText(/change photo/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /remove/i })).toBeInTheDocument();
  });

  it("rejects a disallowed file type client-side without calling onUpload", () => {
    const onUpload = vi.fn();
    render(
      <AvatarUploader avatarUrl={null} fullName="Jane Doe" onUpload={onUpload} onRemove={vi.fn()} />
    );

    // `userEvent.upload` itself enforces the input's `accept` allowlist (as
    // a real browser's file picker would) and never fires a change event
    // for a mismatched type - `fireEvent` bypasses that so this test can
    // reach handleFileChange's own JS-level check, which is the real
    // defense-in-depth here (accept is only advisory for e.g. drag-and-drop).
    const file = new File(["not-an-image"], "avatar.gif", { type: "image/gif" });
    const input = document.getElementById("profile-avatar-input") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    expect(onUpload).not.toHaveBeenCalled();
    expect(toastErrorMock).toHaveBeenCalledWith("Avatar must be a PNG, JPEG or WebP image.");
  });

  it("rejects an oversized file client-side without calling onUpload", async () => {
    const user = userEvent.setup();
    const onUpload = vi.fn();
    render(
      <AvatarUploader avatarUrl={null} fullName="Jane Doe" onUpload={onUpload} onRemove={vi.fn()} />
    );

    const oversized = new File([new Uint8Array(2 * 1024 * 1024 + 1)], "avatar.png", {
      type: "image/png",
    });
    const input = document.getElementById("profile-avatar-input") as HTMLInputElement;
    await user.upload(input, oversized);

    expect(onUpload).not.toHaveBeenCalled();
    expect(toastErrorMock).toHaveBeenCalledWith("Avatar must be 2 MB or smaller.");
  });

  it("calls onUpload with a valid file", async () => {
    const user = userEvent.setup();
    const onUpload = vi.fn().mockResolvedValue(undefined);
    render(
      <AvatarUploader avatarUrl={null} fullName="Jane Doe" onUpload={onUpload} onRemove={vi.fn()} />
    );

    const file = new File(["ok"], "avatar.png", { type: "image/png" });
    const input = document.getElementById("profile-avatar-input") as HTMLInputElement;
    await user.upload(input, file);

    expect(onUpload).toHaveBeenCalledWith(file);
    expect(toastErrorMock).not.toHaveBeenCalled();
  });

  it("calls onRemove when Remove is clicked", async () => {
    const user = userEvent.setup();
    const onRemove = vi.fn().mockResolvedValue(undefined);
    render(
      <AvatarUploader
        avatarUrl="/api/profile/avatar"
        fullName="Jane Doe"
        onUpload={vi.fn()}
        onRemove={onRemove}
      />
    );

    await user.click(screen.getByRole("button", { name: /remove/i }));

    expect(onRemove).toHaveBeenCalled();
  });

  it("disables the upload/remove controls while busy", () => {
    render(
      <AvatarUploader
        avatarUrl="/api/profile/avatar"
        fullName="Jane Doe"
        onUpload={vi.fn()}
        onRemove={vi.fn()}
        isUploading
      />
    );

    expect(document.getElementById("profile-avatar-input")).toBeDisabled();
    expect(screen.getByRole("button", { name: /remove/i })).toBeDisabled();
  });

  it("disables everything when the disabled prop is set", () => {
    render(
      <AvatarUploader
        avatarUrl={null}
        fullName="Jane Doe"
        onUpload={vi.fn()}
        onRemove={vi.fn()}
        disabled
      />
    );

    expect(document.getElementById("profile-avatar-input")).toBeDisabled();
  });
});
