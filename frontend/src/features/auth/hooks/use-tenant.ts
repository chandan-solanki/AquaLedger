import { useAuth } from "@/features/auth/hooks/use-auth";
import type { Tenant } from "@/features/auth/types/auth";

export function useTenant(): Tenant | null {
  return useAuth().tenant;
}
