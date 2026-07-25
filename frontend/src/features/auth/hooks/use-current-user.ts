import { useAuth } from "@/features/auth/hooks/use-auth";
import type { User } from "@/features/auth/types/auth";

export function useCurrentUser(): User | null {
  return useAuth().user;
}
