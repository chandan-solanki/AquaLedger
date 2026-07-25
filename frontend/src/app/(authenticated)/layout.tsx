import type { ReactNode } from "react";

import { AppLayout } from "@/components/layout/app-layout";
import { AuthGuard } from "@/features/auth/components/auth-guard";

export default function AuthenticatedLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <AppLayout>{children}</AppLayout>
    </AuthGuard>
  );
}
