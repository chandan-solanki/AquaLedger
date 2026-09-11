import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PrivacyPage } from "@/features/marketing/pages/privacy-page";

describe("PrivacyPage", () => {
  it("renders the privacy policy heading", () => {
    render(<PrivacyPage />);

    expect(
      screen.getByRole("heading", { level: 1, name: "AquaLedger Privacy Policy" })
    ).toBeInTheDocument();
  });

  it("links back to the homepage", () => {
    render(<PrivacyPage />);

    const homeLinks = screen.getAllByRole("link", { name: /back to aqualedger|^home$/i });
    expect(homeLinks.length).toBeGreaterThan(0);
    expect(homeLinks[0]).toHaveAttribute("href", "/");
  });

  it("does not claim compliance certifications the project does not document", () => {
    render(<PrivacyPage />);

    expect(screen.queryByText(/GDPR compliant/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/ISO 27001 certified/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/SOC ?2 certified/i)).not.toBeInTheDocument();
  });

  it("covers backups, security, and retention sections", () => {
    render(<PrivacyPage />);

    expect(screen.getByRole("heading", { name: /backups/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /security/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /data retention/i })).toBeInTheDocument();
  });
});
