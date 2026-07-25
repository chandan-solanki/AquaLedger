import { z } from "zod";

// Mirrors the backend's exact email check (app/modules/auth/schemas.py) —
// deliberately not zod's stricter .email(), so anything the backend accepts
// (e.g. the seeded admin@fisherp.local account) the form accepts too.
const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export const loginSchema = z.object({
  email: z
    .string()
    .min(1, "Email is required")
    .regex(EMAIL_PATTERN, "Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
  rememberMe: z.boolean(),
});

export type LoginFormValues = z.infer<typeof loginSchema>;
