import type { ReactNode } from "react";

import { PlatformGuard } from "@/features/platform/components/platform-guard";

export default function PlatformLayout({ children }: { children: ReactNode }) {
  return <PlatformGuard>{children}</PlatformGuard>;
}
