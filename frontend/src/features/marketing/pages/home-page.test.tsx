import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HomePage } from "@/features/marketing/pages/home-page";

describe("HomePage", () => {
  it("renders the AquaLedger headline and description", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { level: 1, name: "AquaLedger" })).toBeInTheDocument();
    expect(screen.getByText("Fishery Management & ERP")).toBeInTheDocument();
  });

  it("links to /login for signing in", () => {
    render(<HomePage />);

    const signInLinks = screen.getAllByRole("link", { name: "Sign in" });
    expect(signInLinks.length).toBeGreaterThan(0);
    for (const link of signInLinks) {
      expect(link).toHaveAttribute("href", "/login");
    }
  });

  it("links to /privacy for the privacy policy", () => {
    render(<HomePage />);

    const privacyLinks = screen.getAllByRole("link", { name: /privacy policy/i });
    expect(privacyLinks.length).toBeGreaterThan(0);
    for (const link of privacyLinks) {
      expect(link).toHaveAttribute("href", "/privacy");
    }
  });

  it("lists the core capabilities without claiming unbuilt features", () => {
    render(<HomePage />);

    expect(screen.getByText("Companies")).toBeInTheDocument();
    expect(screen.getByText("Invoices")).toBeInTheDocument();
    expect(screen.getByText("Payments")).toBeInTheDocument();
    expect(screen.queryByText(/OCR/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/AI Assistant/i)).not.toBeInTheDocument();
  });
});
