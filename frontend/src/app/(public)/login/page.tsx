import type { Metadata } from "next";

import { LoginPage } from "@/features/auth/pages/login-page";

export const metadata: Metadata = {
  title: "Log in — AquaLedger",
};

export default function Page() {
  return <LoginPage />;
}
